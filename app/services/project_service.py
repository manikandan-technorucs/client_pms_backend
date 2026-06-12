"""Project service — isolated business logic for project CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services import attachment_service


def _load_options():
    return [
        selectinload(Project.tasks),
        selectinload(Project.bugs),
        selectinload(Project.attachments),
    ]


async def list_projects(session: AsyncSession) -> List[Project]:
    """Return all projects with their attachments."""
    result = await session.execute(
        select(Project).options(*_load_options()).order_by(Project.id)
    )
    return list(result.scalars().all())


async def get_project(session: AsyncSession, project_id: int) -> Optional[Project]:
    """Return a single project by ID."""
    result = await session.execute(
        select(Project)
        .options(*_load_options())
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
            session, project.attachments, keep_ids
        )
    if new_files:
        await attachment_service.save_files(
            session, new_files, project_id=project.id
        )

    await session.flush()
    await session.refresh(project, attribute_names=["attachments"])
    return project


async def delete_project(session: AsyncSession, project_id: int) -> bool:
    """Delete a project (cascades to tasks, bugs, attachments)."""
    project = await get_project(session, project_id)
    if project is None:
        return False
    await session.delete(project)
    return True
