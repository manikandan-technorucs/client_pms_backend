"""Audit service — lightweight helper to write AuditLog rows."""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog


async def log_action(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    performed_by: str,
    changes: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Insert an AuditLog row for a create / update / delete event.

    Args:
        session:      The current async DB session (same transaction as the mutation).
        entity_type:  Lowercase entity name, e.g. "project", "task", "bug".
        entity_id:    PK of the affected row.
        action:       AuditAction.create | .update | .delete
        performed_by: Username from the JWT (current_user).
        changes:      For "update" → {field: {"old": ..., "new": ...}}.
                      For "create" / "delete" → full field snapshot dict.
    """
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        changes=changes,
    )
    session.add(entry)
    return entry


def build_snapshot(obj, exclude: tuple = ()) -> Dict[str, Any]:
    """Return a plain-dict snapshot of an ORM object's scalar columns."""
    result = {}
    for col in obj.__table__.columns:
        if col.name in exclude:
            continue
        val = getattr(obj, col.name, None)
        # Make datetimes JSON-serialisable
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def build_diff(old_snapshot: Dict[str, Any], new_obj, exclude: tuple = ()) -> Dict[str, Any]:
    """Return only the fields that changed between old_snapshot and new_obj."""
    diff = {}
    for col in new_obj.__table__.columns:
        if col.name in exclude:
            continue
        new_val = getattr(new_obj, col.name, None)
        if hasattr(new_val, "isoformat"):
            new_val = new_val.isoformat()
        old_val = old_snapshot.get(col.name)
        if old_val != new_val:
            diff[col.name] = {"old": old_val, "new": new_val}
    return diff
