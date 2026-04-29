from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str | None = None
    event_id: str
    parent_id: str | None = None
    title: str
    description: str = ""
    status: str = "open"
    assigned_to: str | None = None
    contribution: str | None = None
    created_by: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
