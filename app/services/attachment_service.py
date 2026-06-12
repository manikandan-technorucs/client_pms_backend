"""Attachment service — file I/O and DB sync engine."""
from __future__ import annotations

import os
import uuid
from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import Attachment

UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")


def _ensure_upload_dir() -> None:
    os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_files(
    session: AsyncSession,
    new_files: Sequence[UploadFile],
    *,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    bug_id: Optional[int] = None,
) -> List[Attachment]:
    """Save uploaded files to disk and persist Attachment rows."""
    _ensure_upload_dir()
    created: List[Attachment] = []
    for upload in new_files:
        if not upload.filename:
            continue
        unique_name = f"{uuid.uuid4().hex}_{upload.filename}"
        dest = os.path.join(UPLOAD_DIR, unique_name)
        content = await upload.read()
        with open(dest, "wb") as fh:
            fh.write(content)
        attachment = Attachment(
            file_name=upload.filename,
            file_path=dest,
            project_id=project_id,
            task_id=task_id,
            bug_id=bug_id,
        )
        session.add(attachment)
        created.append(attachment)
    return created


async def sync_attachments(
    session: AsyncSession,
    keep_ids: List[int],
    *,
    project_id: Optional[int] = None,
    task_id: Optional[int] = None,
    bug_id: Optional[int] = None,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> None:
    """
    Diff-sync attachments for an entity:
    1. Load current attachment IDs for the entity.
    2. Delete DB rows and purge physical files not in keep_ids.
    3. Save new uploaded files.
    """
    # Build query filter
    if task_id is not None:
        stmt = select(Attachment).where(Attachment.task_id == task_id)
    elif bug_id is not None:
        stmt = select(Attachment).where(Attachment.bug_id == bug_id)
    elif project_id is not None:
        stmt = select(Attachment).where(Attachment.project_id == project_id)
    else:
        return

    result = await session.execute(stmt)
    current: List[Attachment] = list(result.scalars().all())

    for attachment in current:
        if attachment.id not in keep_ids:
            # Purge physical file
            if os.path.exists(attachment.file_path):
                try:
                    os.remove(attachment.file_path)
                except OSError:
                    pass
            await session.delete(attachment)

    if new_files:
        await save_files(
            session,
            new_files,
            project_id=project_id,
            task_id=task_id,
            bug_id=bug_id,
        )
