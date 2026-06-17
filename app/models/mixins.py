"""Reusable SQLAlchemy mixin that adds audit timestamp + actor columns."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds created_at, updated_at, created_by, updated_by to any model.

    - created_at / updated_at are set automatically by the DB (server_default /
      onupdate), so they are always accurate even if the service layer forgets.
    - created_by / updated_by must be set explicitly in the service layer from
      the authenticated user's username.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
