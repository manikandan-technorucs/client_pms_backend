"""Task service — isolated business logic for task CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditAction
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import attachment_service
from app.services.audit_service import build_diff, build_snapshot, log_action


def _load_options():
    """Eager-load attachments and two levels of subtasks."""
    return [
        selectinload(Task.attachments),
        selectinload(Task.subtasks).selectinload(Task.attachments),
        selectinload(Task.subtasks).selectinload(Task.subtasks).selectinload(Task.attachments),
    ]


async def list_all_tasks(session: AsyncSession, project_id: int) -> List[Task]:
    """Return all root tasks (parent_id=None) for a project with nested subtasks."""
    stmt = (
        select(Task)
        .options(*_load_options())
        .where(Task.project_id == project_id)
        .where(Task.parent_id.is_(None))
        .order_by(Task.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_task(session: AsyncSession, task_id: int) -> Optional[Task]:
    """Return a single task by ID."""
    result = await session.execute(
        select(Task).options(*_load_options()).where(Task.id == task_id)
    )
    return result.scalar_one_or_none()


async def create_task(
    session: AsyncSession,
    data: TaskCreate,
    performed_by: str,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Task:
    """Create a task, set created_by, and write an audit log entry."""
    task = Task(**data.model_dump(), created_by=performed_by, updated_by=performed_by)
    session.add(task)
    await session.flush()
    if new_files:
        await attachment_service.save_files(session, new_files, task_id=task.id)
    await log_action(
        session,
        entity_type="task",
        entity_id=task.id,
        action=AuditAction.create,
        performed_by=performed_by,
        changes=build_snapshot(task, exclude=("created_at", "updated_at")),
    )
    await session.refresh(task, attribute_names=["attachments", "subtasks", "created_at", "updated_at"])
    return task


async def update_task(
    session: AsyncSession,
    task_id: int,
    data: TaskUpdate,
    keep_attachment_ids: List[int],
    performed_by: str,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Optional[Task]:
    """Update task fields and synchronize attachments, log the diff."""
    task = await get_task(session, task_id)
    if task is None:
        return None

    old_snapshot = build_snapshot(task, exclude=("created_at", "updated_at"))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    task.updated_by = performed_by

    await session.flush()
    await attachment_service.sync_attachments(
        session,
        keep_attachment_ids,
        task_id=task_id,
        new_files=new_files,
    )

    diff = build_diff(old_snapshot, task, exclude=("created_at", "updated_at"))
    if diff:
        await log_action(
            session,
            entity_type="task",
            entity_id=task_id,
            action=AuditAction.update,
            performed_by=performed_by,
            changes=diff,
        )

    await session.refresh(task, attribute_names=["attachments", "subtasks", "updated_at"])
    return task


async def delete_task(session: AsyncSession, task_id: int, performed_by: str) -> bool:
    """Delete a task using an optimized DELETE statement.

    DB CASCADE handles subtasks and attachment rows. We only need to
    fetch attachment file paths for physical cleanup — no full ORM load.
    """
    # Lightweight existence check
    exists = await session.scalar(
        select(Task.id).where(Task.id == task_id)
    )
    if exists is None:
        return False

    # Collect attachment file paths for physical cleanup
    from app.models.attachment import Attachment
    att_result = await session.execute(
        select(Attachment.file_path).where(Attachment.task_id == task_id)
    )
    file_paths = [row[0] for row in att_result.fetchall()]

    # Log deletion BEFORE the row disappears
    await log_action(
        session,
        entity_type="task",
        entity_id=task_id,
        action=AuditAction.delete,
        performed_by=performed_by,
        changes={"deleted_id": task_id},
    )

    # Raw DELETE — CASCADE handles subtasks and their attachments in DB
    await session.execute(delete(Task).where(Task.id == task_id))

    # Remove physical files concurrently (non-blocking)
    if file_paths:
        import asyncio
        await asyncio.gather(
            *(attachment_service._remove_file_async(p) for p in file_paths)
        )

    return True
