"""Bug service — isolated business logic for bug CRUD."""
from __future__ import annotations

from typing import List, Optional, Sequence

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bug import Bug
from app.schemas.bug import BugCreate, BugUpdate
from app.services import attachment_service


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
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Bug:
    """Create a bug and optionally attach files."""
    bug = Bug(**data.model_dump())
    session.add(bug)
    await session.flush()
    if new_files:
        await attachment_service.save_files(session, new_files, bug_id=bug.id)
    await session.refresh(bug, attribute_names=["attachments", "sub_bugs"])
    return bug


async def update_bug(
    session: AsyncSession,
    bug_id: int,
    data: BugUpdate,
    keep_attachment_ids: List[int],
    new_files: Optional[Sequence[UploadFile]] = None,
) -> Optional[Bug]:
    """Update bug fields and synchronize attachments."""
    bug = await get_bug(session, bug_id)
    if bug is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bug, field, value)
    await session.flush()
    await attachment_service.sync_attachments(
        session,
        keep_attachment_ids,
        bug_id=bug_id,
        new_files=new_files,
    )
    await session.refresh(bug, attribute_names=["attachments", "sub_bugs"])
    return bug


async def delete_bug(session: AsyncSession, bug_id: int) -> bool:
    """Delete a bug (cascades to sub-bugs and attachments)."""
    bug = await get_bug(session, bug_id)
    if bug is None:
        return False
    await session.delete(bug)
    return True
