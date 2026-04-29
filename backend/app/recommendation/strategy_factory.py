"""
RecommendationStrategyFactory

Maps a strategy name string to a concrete RecommendationStrategy instance.
All strategies are constructed once with their required DAOs; the factory
simply looks up and returns the appropriate instance.
"""

from app.recommendation.dao.attendance_signal_dao import AttendanceSignalDAO
from app.recommendation.dao.event_tag_dao import EventTagDAO
from app.recommendation.dao.user_profile_dao import UserProfileDAO
from app.recommendation.strategies.base import RecommendationStrategy
from app.recommendation.strategies.hybrid import HybridRecommendationStrategy
from app.recommendation.strategies.popularity_based import PopularityBasedRecommendationStrategy
from app.recommendation.strategies.tag_based import TagBasedRecommendationStrategy

KNOWN_STRATEGIES = ("tag", "popularity", "hybrid")


class RecommendationStrategyFactory:
    def __init__(
        self,
        user_profile_dao: UserProfileDAO,
        event_tag_dao: EventTagDAO,
        attendance_signal_dao: AttendanceSignalDAO,
    ) -> None:
        self._registry: dict[str, RecommendationStrategy] = {
            "tag": TagBasedRecommendationStrategy(user_profile_dao, event_tag_dao),
            "popularity": PopularityBasedRecommendationStrategy(attendance_signal_dao),
            "hybrid": HybridRecommendationStrategy(
                user_profile_dao, event_tag_dao, attendance_signal_dao
            ),
        }

    def create_strategy(self, strategy: str) -> RecommendationStrategy:
        if strategy not in self._registry:
            raise ValueError(
                f"Unknown strategy '{strategy}'. Valid options: {', '.join(KNOWN_STRATEGIES)}"
            )
        return self._registry[strategy]
