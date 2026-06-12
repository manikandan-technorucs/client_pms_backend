"""Pydantic v2 schemas for Project."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.project import ProjectStatus
from app.schemas.attachment import AttachmentRead


class ProjectBase(BaseModel):
    """Shared project fields."""

    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: ProjectStatus = ProjectStatus.open


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""


class ProjectUpdate(BaseModel):
    """Schema for updating a project — all fields optional."""

    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatus] = None


class ProjectRead(ProjectBase):
    """Schema for reading a project."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    attachments: List[AttachmentRead] = []
