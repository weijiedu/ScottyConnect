"""
Hybrid recommendation strategy.

Blends tag-based and popularity signals. Each signal produces raw scores
(tag overlap count, attendance count), which are normalized to [0, 1] by
dividing by the max observed score, then combined with configurable weights.
"""

from app.recommendation.dao.attendance_signal_dao import AttendanceSignalDAO
from app.recommendation.dao.event_tag_dao import EventTagDAO
from app.recommendation.dao.user_profile_dao import UserProfileDAO
from app.recommendation.strategies.base import RecommendationStrategy

TAG_WEIGHT = 0.5
POPULARITY_WEIGHT = 0.5


class HybridRecommendationStrategy(RecommendationStrategy):
    def __init__(
        self,
        user_profile_dao: UserProfileDAO,
        event_tag_dao: EventTagDAO,
        attendance_signal_dao: AttendanceSignalDAO,
    ) -> None:
        self._user_profile_dao = user_profile_dao
        self._event_tag_dao = event_tag_dao
        self._attendance_signal_dao = attendance_signal_dao

    def recommend(self, user_id: str) -> list[str]:
        tag_ids = self._user_profile_dao.get_user_tags(user_id)
        tag_scores: dict[str, int] = (
            self._event_tag_dao.find_event_ids_by_tags(tag_ids) if tag_ids else {}
        )
        popularity_scores: dict[str, int] = (
            self._attendance_signal_dao.count_attendance_by_event()
        )

        tag_norm = self._normalize(tag_scores)
        popularity_norm = self._normalize(popularity_scores)

        candidate_ids = set(tag_norm) | set(popularity_norm)
        if not candidate_ids:
            return []

        combined: dict[str, float] = {
            event_id: TAG_WEIGHT * tag_norm.get(event_id, 0.0)
            + POPULARITY_WEIGHT * popularity_norm.get(event_id, 0.0)
            for event_id in candidate_ids
        }

        sorted_ids = sorted(combined, key=lambda eid: combined[eid], reverse=True)
        return sorted_ids

    @staticmethod
    def _normalize(scores: dict[str, int]) -> dict[str, float]:
        """Min-max style normalization against the max score; result in [0, 1]."""
        if not scores:
            return {}
        max_score = max(scores.values())
        if max_score <= 0:
            return {event_id: 0.0 for event_id in scores}
        return {event_id: score / max_score for event_id, score in scores.items()}
