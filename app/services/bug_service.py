"""Bug service — isolated business logic for bug CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditAction
from app.models.bug import Bug
from app.schemas.bug import BugCreate, BugUpdate
from app.services import attachment_service
from app.services.audit_service import build_diff, build_snapshot, log_action


def _load_options():
    """Eager-load attachments and two levels of sub-bugs."""
    return [
        selectinload(Bug.attachments),
        selectinload(Bug.sub_bugs).selectinload(Bug.attachments),
        selectinload(Bug.sub_bugs).selectinload(Bug.sub_bugs).selectinload(Bug.attachments),
    ]


async def list_all_bugs(session: AsyncSession, project_id: int) -> List[Bug]:
    """Return all root bugs (parent_id=None) for a project with nested sub-bugs."""
    stmt = (
        select(Bug)
        .options(*_load_options())
        .where(Bug.project_id == project_id)
        .where(Bug.parent_id.is_(None))
        .order_by(Bug.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_bug(session: AsyncSession, bug_id: int) -> Optional[Bug]:
    """Return a single bug by ID."""
    result = await session.execute(
        select(Bug).options(*_load_options()).where(Bug.id == bug_id)
    )
    return result.scalar_one_or_none()


async def create_bug(
    session: AsyncSession,
    data: BugCreate,
    performed_by: str,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Bug:
    """Create a bug, set created_by, and write an audit log entry.

    Note: `reporter` remains a separate free-text field (Option A).
    `created_by` is always the authenticated user from the JWT.
    """
    bug = Bug(**data.model_dump(), created_by=performed_by, updated_by=performed_by)
    session.add(bug)
    await session.flush()
    if new_files:
        await attachment_service.save_files(session, new_files, bug_id=bug.id)
    await log_action(
        session,
        entity_type="bug",
        entity_id=bug.id,
        action=AuditAction.create,
        performed_by=performed_by,
        changes=build_snapshot(bug, exclude=("created_at", "updated_at")),
    )
    await session.refresh(bug, attribute_names=["attachments", "sub_bugs", "created_at", "updated_at"])
    return bug


async def update_bug(
    session: AsyncSession,
    bug_id: int,
    data: BugUpdate,
    keep_attachment_ids: List[int],
    performed_by: str,
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Optional[Bug]:
    """Update bug fields and synchronize attachments, log the diff."""
    bug = await get_bug(session, bug_id)
    if bug is None:
        return None

    old_snapshot = build_snapshot(bug, exclude=("created_at", "updated_at"))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bug, field, value)
    bug.updated_by = performed_by

    await session.flush()
    await attachment_service.sync_attachments(
        session,
        keep_attachment_ids,
        bug_id=bug_id,
        new_files=new_files,
    )

    diff = build_diff(old_snapshot, bug, exclude=("created_at", "updated_at"))
    if diff:
        await log_action(
            session,
            entity_type="bug",
            entity_id=bug_id,
            action=AuditAction.update,
            performed_by=performed_by,
            changes=diff,
        )

    await session.refresh(bug, attribute_names=["attachments", "sub_bugs", "updated_at"])
    return bug


async def delete_bug(session: AsyncSession, bug_id: int, performed_by: str) -> bool:
    """Delete a bug using an optimized DELETE statement.

    DB CASCADE handles sub-bugs and attachment rows. We only need to
    fetch attachment file paths for physical cleanup — no full ORM load.
    """
    # Lightweight existence check
    exists = await session.scalar(
        select(Bug.id).where(Bug.id == bug_id)
    )
    if exists is None:
        return False

    # Collect attachment file paths for physical cleanup
    from app.models.attachment import Attachment
    att_result = await session.execute(
        select(Attachment.file_path).where(Attachment.bug_id == bug_id)
    )
    file_paths = [row[0] for row in att_result.fetchall()]

    # Log deletion BEFORE the row disappears
    await log_action(
        session,
        entity_type="bug",
        entity_id=bug_id,
        action=AuditAction.delete,
        performed_by=performed_by,
        changes={"deleted_id": bug_id},
    )

    # Raw DELETE — CASCADE handles sub-bugs and their attachments in DB
    await session.execute(delete(Bug).where(Bug.id == bug_id))

    # Remove physical files concurrently (non-blocking)
    if file_paths:
        import asyncio
        await asyncio.gather(
            *(attachment_service._remove_file_async(p) for p in file_paths)
        )

    return True
