"""Pydantic v2 schemas for Bug."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.bug import BugStatus
from app.schemas.attachment import AttachmentRead


class BugBase(BaseModel):
    """Shared bug fields."""

    title: str
    description: Optional[str] = None
    reporter: str
    assignees: Optional[List[str]] = []
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: BugStatus = BugStatus.open


class BugCreate(BugBase):
    """Schema for creating a bug."""

    project_id: int
    task_id: Optional[int] = None
    parent_id: Optional[int] = None


class BugUpdate(BaseModel):
    """Schema for updating a bug — all fields optional."""

    title: Optional[str] = None
    description: Optional[str] = None
    reporter: Optional[str] = None
    assignees: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[BugStatus] = None
    task_id: Optional[int] = None
    parent_id: Optional[int] = None


class BugRead(BugBase):
    """Schema for reading a bug."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    task_id: Optional[int] = None
    parent_id: Optional[int] = None
    attachments: List[AttachmentRead] = []
    sub_bugs: List["BugRead"] = []
