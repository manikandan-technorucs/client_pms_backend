from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/", response_model=List[TaskRead])
async def list_tasks(
    project_id: int,
    session: AsyncSession = Depends(get_db),
):
    return await task_service.list_all_tasks(session, project_id)


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return await task_service.create_task(session, data, performed_by=current_user)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
):
    task = await task_service.get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,

    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    assignees: Optional[str] = Form(None),  # JSON string e.g. '["Alice","Bob"]'
    parent_id: Optional[int] = Form(None),
    # Attachment sync: stringified JSON array of IDs to keep
    keep_attachment_ids: str = Form("[]"),
    # New file uploads
    new_files: List[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
):

    try:
        keep_ids: List[int] = json.loads(keep_attachment_ids)
    except (json.JSONDecodeError, ValueError):
        keep_ids = []

    update_data = TaskUpdate(
        name=name,
        description=description,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        status=TaskStatus(status) if status else None,
        assignees=json.loads(assignees) if assignees else None,
        parent_id=parent_id,
    )

    valid_files = [f for f in new_files if f.filename]

    task = await task_service.update_task(
        session,
        task_id,
        update_data,
        keep_ids,
        performed_by=current_user,
        new_files=valid_files if valid_files else None,
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
):

    deleted = await task_service.delete_task(session, task_id, performed_by=current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
