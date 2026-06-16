"""Project service — isolated business logic for project CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attachment import Attachment
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services import attachment_service


def _list_options():
    """Load options for the list endpoint — attachments only (NO tasks/bugs).

    Loading tasks+bugs on every row in the list query is an N+1 disaster
    at scale. The list page only needs attachment counts, not task/bug data.
    """
    return [selectinload(Project.attachments)]


def _detail_options():
    """Load options for a single project detail — full related data."""
    return [
        selectinload(Project.attachments),
        selectinload(Project.tasks),
        selectinload(Project.bugs),
    ]


async def list_projects(session: AsyncSession) -> List[Project]:
    """Return all projects with only attachments loaded (optimized for list)."""
    result = await session.execute(
        select(Project).options(*_list_options()).order_by(Project.id)
    )
    return list(result.scalars().all())


async def get_project(session: AsyncSession, project_id: int) -> Optional[Project]:
    """Return a single project by ID with full related data."""
    result = await session.execute(
        select(Project)
        .options(*_detail_options())
        .where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def create_project(
    session: AsyncSession,
    data: ProjectCreate,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Project:
    """Create a project and optionally attach files."""
    project = Project(**data.model_dump())
    session.add(project)
    await session.flush()  # get project.id
    if new_files:
        await attachment_service.save_files(
            session, new_files, project_id=project.id
        )
    await session.refresh(project, attribute_names=["attachments"])
    return project


async def update_project(
    session: AsyncSession,
    project_id: int,
    data: ProjectUpdate,
    keep_ids: Optional[Sequence[int]] = None,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Optional[Project]:
    """Update scalar fields and attachments of a project."""
    project = await get_project(session, project_id)
    if project is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    # Sync attachments
    if keep_ids is not None:
        await attachment_service.sync_attachments(
            session, list(keep_ids), project_id=project.id
        )
    if new_files:
        await attachment_service.save_files(
            session, new_files, project_id=project.id
        )

    await session.flush()
    await session.refresh(project, attribute_names=["attachments"])
    return project


async def delete_project(session: AsyncSession, project_id: int) -> bool:
    """Delete a project using an optimized DELETE statement.

    Instead of loading the full ORM object (with all eager-loaded relations)
    just to call session.delete(), we:
    1. Check existence with a lightweight scalar query.
    2. Collect attachment file paths for physical cleanup.
    3. Issue a raw DELETE (DB CASCADE handles tasks/bugs/attachments rows).
    4. Remove physical files concurrently in background.
    """
    # Lightweight existence check — no joins
    exists = await session.scalar(
        select(Project.id).where(Project.id == project_id)
    )
    if exists is None:
        return False

    # Collect attachment file paths before deleting
    att_result = await session.execute(
        select(Attachment.file_path).where(Attachment.project_id == project_id)
    )
    file_paths = [row[0] for row in att_result.fetchall()]

    # Raw DELETE — CASCADE deletes tasks, bugs, and attachment rows
    await session.execute(delete(Project).where(Project.id == project_id))

    # Remove physical files concurrently (non-blocking)
    if file_paths:
        import asyncio
        import os
        await asyncio.gather(
            *(attachment_service._remove_file_async(p) for p in file_paths)
        )

    return True
