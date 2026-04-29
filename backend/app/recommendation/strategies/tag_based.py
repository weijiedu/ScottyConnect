"""
Tag-based recommendation strategy.

Flow:
  1. Fetch the user's tag_ids via UserProfileDAO.
  2. Find all events sharing at least one of those tags via EventTagDAO.
  3. Score each event by the number of overlapping tags (higher = better match).
  4. Return all matching event_ids sorted by descending score.
"""

from app.recommendation.dao.event_tag_dao import EventTagDAO
from app.recommendation.dao.user_profile_dao import UserProfileDAO
from app.recommendation.strategies.base import RecommendationStrategy


class TagBasedRecommendationStrategy(RecommendationStrategy):
    def __init__(
        self,
        user_profile_dao: UserProfileDAO,
        event_tag_dao: EventTagDAO,
    ) -> None:
        self._user_profile_dao = user_profile_dao
        self._event_tag_dao = event_tag_dao

    def recommend(self, user_id: str) -> list[str]:
        tag_ids = self._user_profile_dao.get_user_tags(user_id)
        if not tag_ids:
            return []

        scored: dict[str, int] = self._event_tag_dao.find_event_ids_by_tags(tag_ids)
        sorted_ids = sorted(scored, key=lambda eid: scored[eid], reverse=True)
        return sorted_ids
