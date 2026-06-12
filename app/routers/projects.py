"""Projects router — CRUD endpoints."""
from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.database import get_db
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentRead
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import attachment_service, project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=List[ProjectRead])
async def list_projects(session: AsyncSession = Depends(get_db)):
    """List all projects."""
    return await project_service.list_projects(session)


import json
from typing import Optional

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    project_status: Optional[str] = Form(None, alias="status"),
    new_files: List[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    data = ProjectCreate(
        name=name,
        description=description,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        status=project_status if project_status else "Open",
    )
    valid_files = [f for f in new_files if f.filename]
    return await project_service.create_project(
        session, data, valid_files if valid_files else None
    )

@router.get("/stats")
async def get_project_stats(session: AsyncSession = Depends(get_db)):
    """Get global stats across all projects."""
    from sqlalchemy import select, func
    from app.models.task import Task
    from app.models.bug import Bug
    
    total_tasks = await session.scalar(select(func.count(Task.id)))
    total_bugs = await session.scalar(select(func.count(Bug.id)))
    
    return {"totalTasks": total_tasks or 0, "totalBugs": total_bugs or 0}

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a project by ID."""
    project = await project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    project_status: Optional[str] = Form(None, alias="status"),
    keep_attachment_ids: str = Form("[]"),
    new_files: List[UploadFile] = File(default=[]),
    session: AsyncSession = Depends(get_db),
):
    """Update a project's scalar fields and attachments."""
    try:
        keep_ids: List[int] = json.loads(keep_attachment_ids)
    except (json.JSONDecodeError, ValueError):
        keep_ids = []

    data = ProjectUpdate(
        name=name,
        description=description,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        status=project_status if project_status else None,
    )
    
    valid_files = [f for f in new_files if f.filename]
    project = await project_service.update_project(
        session, project_id, data, keep_ids, valid_files if valid_files else None
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a project (cascades to tasks, bugs, attachments)."""
    deleted = await project_service.delete_project(session, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")


# ── Project Attachment Endpoints ──────────────────────────────────────────────

@router.post(
    "/{project_id}/attachments",
    response_model=List[AttachmentRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_attachments(
    project_id: int,
    new_files: List[UploadFile] = File(...),
    session: AsyncSession = Depends(get_db),
):
    """Upload one or more files and attach them to a project."""
    project = await project_service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    valid_files = [f for f in new_files if f.filename]
    if not valid_files:
        raise HTTPException(status_code=400, detail="No valid files provided")

    created = await attachment_service.save_files(
        session, valid_files, project_id=project_id
    )
    await session.flush()
    return created


@router.delete(
    "/{project_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_attachment(
    project_id: int,
    attachment_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Remove a single attachment from a project."""
    result = await session.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.project_id == project_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if os.path.exists(attachment.file_path):
        try:
            os.remove(attachment.file_path)
        except OSError:
            pass
    await session.delete(attachment)
