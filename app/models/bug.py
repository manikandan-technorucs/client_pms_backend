"""SQLAlchemy ORM model for Bug (self-referential, optional task link)."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.project import Project
    from app.models.task import Task


class BugStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Bug(Base):
    """Bug entity — can be linked to a task or standalone under a project."""

    __tablename__ = "bugs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # ← Critical: speeds up GET /bugs/?project_id=X queries
    )
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,  # ← Speeds up bug-to-task join lookups
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bugs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,  # ← Speeds up sub-bug hierarchy lookups
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reporter: Mapped[str] = mapped_column(String(255), nullable=False)
    assignees: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    start_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    status: Mapped[BugStatus] = mapped_column(
        Enum(BugStatus),
        default=BugStatus.open,
        server_default=BugStatus.open.value,
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="bugs")
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="bugs")
    parent: Mapped[Optional["Bug"]] = relationship(
        "Bug", remote_side="Bug.id", back_populates="sub_bugs"
    )
    sub_bugs: Mapped[List["Bug"]] = relationship(
        "Bug",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        back_populates="bug",
        cascade="all, delete-orphan",
        foreign_keys="[Attachment.bug_id]",
        lazy="selectin",
    )
