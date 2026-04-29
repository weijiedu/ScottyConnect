"""
Popularity-based recommendation strategy.

Ranks events by the number of users who actually attended (attendance_time set).
Reads attendance data through the recommendation-owned AttendanceSignalDAO so
the strategy has no dependency on the attendance service code.

Returns event_ids sorted by descending attendance count.
"""

from app.recommendation.dao.attendance_signal_dao import AttendanceSignalDAO
from app.recommendation.strategies.base import RecommendationStrategy


class PopularityBasedRecommendationStrategy(RecommendationStrategy):
    def __init__(self, attendance_signal_dao: AttendanceSignalDAO) -> None:
        self._attendance_signal_dao = attendance_signal_dao

    def recommend(self, user_id: str) -> list[str]:
        scores = self._attendance_signal_dao.count_attendance_by_event()
        sorted_ids = sorted(scores, key=lambda eid: scores[eid], reverse=True)
        return sorted_ids
