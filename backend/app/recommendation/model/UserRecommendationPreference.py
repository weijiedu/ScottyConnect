# Domain shape for a user_recommendation_preferences document — stores a user's chosen recommendation strategy.

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UserRecommendationPreference(BaseModel):
    id: str | None = None
    user_id: str
    preferred_strategy: str = "hybrid"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
