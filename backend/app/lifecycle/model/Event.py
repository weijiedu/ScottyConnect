# Domain shape for an event document (persistence via LifecycleDAO).

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Event(BaseModel):
    id: str | None = None
    title: str
    description: str
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    capacity: int | None = None
    owner_id: str
    status: str = "draft"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
