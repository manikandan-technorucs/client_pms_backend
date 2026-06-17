"""Audit log router — query history of entity mutations."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/", response_model=List[AuditLogRead])
async def list_audit_logs(
    entity_type: Optional[str] = Query(None, description="Filter by entity type: project, task, bug"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    performed_by: Optional[str] = Query(None, description="Filter by username"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> List[AuditLogRead]:
    """Return audit log entries, optionally filtered by entity type/id or actor.

    Requires authentication. Results are ordered newest-first.
    """
    stmt = select(AuditLog).order_by(AuditLog.performed_at.desc())

    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if performed_by is not None:
        stmt = stmt.where(AuditLog.performed_by == performed_by)

    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    return list(result.scalars().all())
