"""SQLAlchemy ORM model for AuditLog — records every create/update/delete event."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditAction(str, enum.Enum):
    create = "create"
    update = "update"
    delete = "delete"


class AuditLog(Base):
    """Immutable audit trail entry.

    Intentionally has NO foreign-keys to entity tables so that rows survive
    after hard-deletes and the audit history is always intact.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Which entity was affected
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # What happened
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction),
        nullable=False,
    )

    # Who did it and when
    performed_by: Mapped[str] = mapped_column(String(50), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # JSON snapshot: for "update" → {field: {old: …, new: …}};
    # for "create" / "delete" → full field snapshot
    changes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        # Fast lookups by entity (most common query pattern)
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        # Fast lookups by actor
        Index("ix_audit_logs_performed_by", "performed_by"),
    )
