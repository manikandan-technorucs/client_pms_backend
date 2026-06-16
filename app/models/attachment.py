"""SQLAlchemy ORM model for Attachment."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.bug import Bug
    from app.models.project import Project
    from app.models.task import Task


class Attachment(Base):

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,  # ← Speeds up attachment queries filtered by project
    )
    task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,  # ← Speeds up attachment queries filtered by task
    )
    bug_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bugs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,  # ← Speeds up attachment queries filtered by bug
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="attachments",
        foreign_keys=[project_id],
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task",
        back_populates="attachments",
        foreign_keys=[task_id],
    )
    bug: Mapped[Optional["Bug"]] = relationship(
        "Bug",
        back_populates="attachments",
        foreign_keys=[bug_id],
    )
