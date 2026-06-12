"""Task service — isolated business logic for task CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import attachment_service


def _load_options():
    """Eager-load attachments and two levels of subtasks."""
    return [
        selectinload(Task.attachments),
        selectinload(Task.subtasks).selectinload(Task.attachments),
        selectinload(Task.subtasks).selectinload(Task.subtasks).selectinload(Task.attachments),
    ]


async def list_tasks(
    session: AsyncSession, project_id: int, parent_id: Optional[int] = None
) -> List[Task]:
    """Return tasks filtered by project and optional parent."""
    stmt = (
        select(Task)
        .options(*_load_options())
        .where(Task.project_id == project_id)
        .where(Task.parent_id == parent_id)
        .order_by(Task.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


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
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Task:
    """Create a task and optionally attach files."""
    task = Task(**data.model_dump())
    session.add(task)
    await session.flush()
    if new_files:
        await attachment_service.save_files(session, new_files, task_id=task.id)
    await session.refresh(task, attribute_names=["attachments", "subtasks"])
    return task


async def update_task(
    session: AsyncSession,
    task_id: int,
    data: TaskUpdate,
    keep_attachment_ids: List[int],
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Optional[Task]:
    """Update task fields and synchronize attachments."""
    task = await get_task(session, task_id)
    if task is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    await session.flush()
    await attachment_service.sync_attachments(
        session,
        keep_attachment_ids,
        task_id=task_id,
        new_files=new_files,
    )
    await session.refresh(task, attribute_names=["attachments", "subtasks"])
    return task


async def delete_task(session: AsyncSession, task_id: int) -> bool:
    """Delete a task (cascades to subtasks and attachments)."""
    task = await get_task(session, task_id)
    if task is None:
        return False
    await session.delete(task)
    return True
