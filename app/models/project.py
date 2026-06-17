"""SQLAlchemy ORM model for Project."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.bug import Bug
    from app.models.task import Task
 
class ProjectStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Project(Base, TimestampMixin):

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus),
        default=ProjectStatus.open,
        server_default=ProjectStatus.open.value,
        nullable=False,
    )

    # Relationships
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )
    bugs: Mapped[List["Bug"]] = relationship(
        "Bug",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="[Attachment.project_id]",
        lazy="select",
    )
