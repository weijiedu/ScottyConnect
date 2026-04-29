# Domain shape for a user_tags document — maps a user to a tag.

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UserTag(BaseModel):
    id: str | None = None
    user_id: str
    tag_id: str
    weight: float = 1.0
    source: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
