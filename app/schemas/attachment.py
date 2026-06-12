"""Pydantic v2 schemas for Attachment."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    """Schema for reading an attachment record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    file_path: str
    project_id: int | None = None
    task_id: int | None = None
    bug_id: int | None = None
