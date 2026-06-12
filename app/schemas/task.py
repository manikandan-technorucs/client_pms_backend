"""Pydantic v2 schemas for Task."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskStatus
from app.schemas.attachment import AttachmentRead


class TaskBase(BaseModel):
    """Shared task fields."""

    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    assignees: Optional[List[str]] = []
    status: TaskStatus = TaskStatus.open


class TaskCreate(TaskBase):
    """Schema for creating a task."""

    project_id: int
    parent_id: Optional[int] = None


class TaskUpdate(BaseModel):
    """Schema for updating a task — all fields optional."""

    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    assignees: Optional[List[str]] = None
    status: Optional[TaskStatus] = None
    parent_id: Optional[int] = None


class TaskRead(TaskBase):
    """Schema for reading a task."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    parent_id: Optional[int] = None
    attachments: List[AttachmentRead] = []
    subtasks: List["TaskRead"] = []
