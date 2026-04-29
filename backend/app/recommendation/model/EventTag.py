# Domain shape for an event_tags document — maps an event to a tag.

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class EventTag(BaseModel):
    id: str | None = None
    event_id: str
    tag_id: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
