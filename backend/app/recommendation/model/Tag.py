# Domain shape for a tag document (persistence via TagRepository).

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Tag(BaseModel):
    id: str | None = None
    slug: str
    display_name: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
