"""Task service — isolated business logic for task CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

import csv
import io

from fastapi import UploadFile, HTTPException
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


async def import_tasks_from_csv(
    session: AsyncSession,
    project_id: int,
    file: UploadFile,
    performed_by: str,
) -> int:
    """Parse CSV and create tasks/subtasks. Returns number of created items."""
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM if present
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. Must be UTF-8 CSV.")
    
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")
    
    start_idx = 0
    if len(rows[0]) > 0 and rows[0][0].strip().lower() == "task":
        start_idx = 1
        
    current_parent_task = None
    tasks_created = 0
    
    for row_idx, row in enumerate(rows[start_idx:], start=start_idx + 1):
        if not row or not any(cell.strip() for cell in row):
            continue  # ignore empty rows
            
        task_name = row[0].strip() if len(row) > 0 else ""
        subtask_name = row[1].strip() if len(row) > 1 else ""
        
        if not task_name and not subtask_name:
            continue
            
        if task_name:
            # Create a parent task
            data = TaskCreate(
                project_id=project_id,
                name=task_name,
                status="open"
            )
            current_parent_task = Task(**data.model_dump(), created_by=performed_by, updated_by=performed_by)
            session.add(current_parent_task)
            await session.flush()  # to get the ID for subtasks
            tasks_created += 1
            
            # If the same row also has a subtask name
            if subtask_name:
                sub_data = TaskCreate(
                    project_id=project_id,
                    parent_id=current_parent_task.id,
                    name=subtask_name,
                    status="open"
                )
                sub_task = Task(**sub_data.model_dump(), created_by=performed_by, updated_by=performed_by)
                session.add(sub_task)
                tasks_created += 1
        else:
            # We have a subtask, but no task name on this row
            if not current_parent_task:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Row {row_idx}: Found a SubTask '{subtask_name}' but no parent Task was defined above it."
                )
            sub_data = TaskCreate(
                project_id=project_id,
                parent_id=current_parent_task.id,
                name=subtask_name,
                status="open"
            )
            sub_task = Task(**sub_data.model_dump(), created_by=performed_by, updated_by=performed_by)
            session.add(sub_task)
            tasks_created += 1

    if tasks_created == 0:
        raise HTTPException(status_code=400, detail="No valid tasks found in the CSV file.")
        
    return tasks_created
