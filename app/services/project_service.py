"""Project service — isolated business logic for project CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attachment import Attachment
from app.models.audit_log import AuditAction
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services import attachment_service
from app.services.audit_service import build_diff, build_snapshot, log_action


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
    performed_by: str,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Project:
    """Create a project, set created_by, and write an audit log entry."""
    project = Project(**data.model_dump(), created_by=performed_by, updated_by=performed_by)
    session.add(project)
    await session.flush()  # get project.id
    if new_files:
        await attachment_service.save_files(
            session, new_files, project_id=project.id
        )
    await log_action(
        session,
        entity_type="project",
        entity_id=project.id,
        action=AuditAction.create,
        performed_by=performed_by,
        changes=build_snapshot(project, exclude=("created_at", "updated_at")),
    )
    await session.refresh(project, attribute_names=["attachments", "created_at", "updated_at"])
    return project


async def update_project(
    session: AsyncSession,
    project_id: int,
    data: ProjectUpdate,
    performed_by: str,
    keep_ids: Optional[Sequence[int]] = None,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Optional[Project]:
    """Update scalar fields and attachments of a project, log the diff."""
    project = await get_project(session, project_id)
    if project is None:
        return None

    # Snapshot before changes
    old_snapshot = build_snapshot(project, exclude=("created_at", "updated_at"))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    project.updated_by = performed_by

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

    diff = build_diff(old_snapshot, project, exclude=("created_at", "updated_at"))
    if diff:
        await log_action(
            session,
            entity_type="project",
            entity_id=project_id,
            action=AuditAction.update,
            performed_by=performed_by,
            changes=diff,
        )

    await session.refresh(project, attribute_names=["attachments", "updated_at"])
    return project


async def delete_project(session: AsyncSession, project_id: int, performed_by: str) -> bool:
    """Delete a project using an optimized DELETE statement and log the event.

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

    # Log deletion BEFORE the row disappears
    await log_action(
        session,
        entity_type="project",
        entity_id=project_id,
        action=AuditAction.delete,
        performed_by=performed_by,
        changes={"deleted_id": project_id},
    )

    # Raw DELETE — CASCADE deletes tasks, bugs, and attachment rows
    await session.execute(delete(Project).where(Project.id == project_id))

    # Remove physical files concurrently (non-blocking)
    if file_paths:
        import asyncio
        await asyncio.gather(
            *(attachment_service._remove_file_async(p) for p in file_paths)
        )

    return True
