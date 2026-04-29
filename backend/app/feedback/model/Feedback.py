from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class Feedback(BaseModel):
    id: str | None = None
    event_id: str
    participant_id: str
    rating: int
    comment: str = ""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, rating: int) -> int:
        if rating < 1 or rating > 5:
            raise ValueError("rating must be between 1 and 5")
        return rating