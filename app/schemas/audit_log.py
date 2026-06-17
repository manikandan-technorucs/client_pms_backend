"""Pydantic v2 schemas for AuditLog."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditAction


class AuditLogRead(BaseModel):
    """Schema for reading an audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: AuditAction
    performed_by: str
    performed_at: datetime
    changes: Optional[Dict[str, Any]] = None
