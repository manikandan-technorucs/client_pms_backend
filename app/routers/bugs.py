from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bug import BugStatus
from app.schemas.bug import BugCreate, BugRead, BugUpdate
from app.services import bug_service

router = APIRouter(prefix="/bugs", tags=["Bugs"])


@router.get("/", response_model=List[BugRead])
async def list_bugs(
    project_id: int,
    session: AsyncSession = Depends(get_db),
):
    return await bug_service.list_all_bugs(session, project_id)


@router.post("/", response_model=BugRead, status_code=status.HTTP_201_CREATED)
async def create_bug(
    data: BugCreate,
    session: AsyncSession = Depends(get_db),
):
    return await bug_service.create_bug(session, data)


@router.get("/{bug_id}", response_model=BugRead)
async def get_bug(
    bug_id: int,
    session: AsyncSession = Depends(get_db),
):
    bug = await bug_service.get_bug(session, bug_id)
    if bug is None:
        raise HTTPException(status_code=404, detail="Bug not found")
    return bug


@router.put("/{bug_id}", response_model=BugRead)
async def update_bug(
    bug_id: int,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    reporter: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    assignees: Optional[str] = Form(None),  # JSON string
    task_id: Optional[int] = Form(None),
    parent_id: Optional[int] = Form(None),
    # Attachment sync
    keep_attachment_ids: str = Form("[]"),
    # New file uploads
    new_files: List[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_db),
):

    try:
        keep_ids: List[int] = json.loads(keep_attachment_ids)
    except (json.JSONDecodeError, ValueError):
        keep_ids = []

    update_data = BugUpdate(
        title=title,
        description=description,
        reporter=reporter,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        status=BugStatus(status) if status else None,
        assignees=json.loads(assignees) if assignees else None,
        task_id=task_id,
        parent_id=parent_id,
    )

    valid_files = [f for f in new_files if f.filename]

    bug = await bug_service.update_bug(
        session,
        bug_id,
        update_data,
        keep_ids,
        valid_files if valid_files else None,
    )
    if bug is None:
        raise HTTPException(status_code=404, detail="Bug not found")
    return bug


@router.delete("/{bug_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bug(
    bug_id: int,
    session: AsyncSession = Depends(get_db),
):
    deleted = await bug_service.delete_bug(session, bug_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bug not found")
