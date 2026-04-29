"""
Recommendation Service
"""

from bson import ObjectId
from bson.errors import InvalidId

from app.recommendation.dao.attendance_signal_dao import AttendanceSignalDAO
from app.recommendation.dao.event_signal_dao import EventSignalDAO
from app.recommendation.dao.event_tag_dao import EventTagDAO
from app.recommendation.dao.tag_dao import TagDAO
from app.recommendation.dao.user_preference_dao import UserPreferenceDAO
from app.recommendation.dao.user_profile_dao import UserProfileDAO
from app.recommendation.model.EventTag import EventTag
from app.recommendation.model.Tag import Tag
from app.recommendation.model.UserRecommendationPreference import UserRecommendationPreference
from app.recommendation.model.UserTag import UserTag
from app.recommendation.schemas import RecommendationResponse
from app.recommendation.strategy_factory import KNOWN_STRATEGIES, RecommendationStrategyFactory

RECOMMENDATION_SERVICE_EXTENSION_KEY = "recommendation_service"
DEFAULT_STRATEGY = "hybrid"


def get_recommendation_service() -> "RecommendationService":
    from flask import current_app

    return current_app.extensions[RECOMMENDATION_SERVICE_EXTENSION_KEY]


class RecommendationService:
    def __init__(
        self,
        user_profile_dao: UserProfileDAO | None = None,
        event_tag_dao: EventTagDAO | None = None,
        attendance_signal_dao: AttendanceSignalDAO | None = None,
        event_signal_dao: EventSignalDAO | None = None,
        user_preference_dao: UserPreferenceDAO | None = None,
        tag_dao: TagDAO | None = None,
    ) -> None:
        self._user_profile_dao = user_profile_dao or UserProfileDAO()
        self._event_tag_dao = event_tag_dao or EventTagDAO()
        attendance_signal_dao = attendance_signal_dao or AttendanceSignalDAO()
        self._event_signal_dao = event_signal_dao or EventSignalDAO()
        self._user_preference_dao = user_preference_dao or UserPreferenceDAO()
        self._tag_dao = tag_dao or TagDAO()
        self._factory = RecommendationStrategyFactory(
            self._user_profile_dao, self._event_tag_dao, attendance_signal_dao
        )

    def get_recommendation(
        self, user_id: str, strategy: str
    ) -> RecommendationResponse:
        try:
            strategy_obj = self._factory.create_strategy(strategy)
        except ValueError as e:
            return RecommendationResponse(
                message=str(e), strategy=strategy, events=[], code=400
            )

        ranked_ids = strategy_obj.recommend(user_id)
        ranked_events = self._event_signal_dao.get_published_events_by_ids(ranked_ids)

        all_published = self._event_signal_dao.get_all_published_events()
        ranked_ids_set = {event.id for event in ranked_events}
        unranked_tail = [event for event in all_published if event.id not in ranked_ids_set]

        combined = ranked_events + unranked_tail
        return RecommendationResponse(
            message="Success",
            strategy=strategy,
            events=combined,
            code=200,
        )

    def get_user_preference(self, user_id: str) -> UserRecommendationPreference | None:
        return self._user_preference_dao.get_preference(user_id)

    def set_user_preference(
        self, user_id: str, preferred_strategy: str
    ) -> UserRecommendationPreference | None:
        if preferred_strategy not in KNOWN_STRATEGIES:
            return None
        return self._user_preference_dao.upsert_preference(user_id, preferred_strategy)

    # ---- Tags ---------------------------------------------------------------

    def list_all_tags(self) -> list[Tag]:
        return self._tag_dao.find_all()

    def get_user_tag_ids(self, user_id: str) -> list[str] | None:
        try:
            ObjectId(user_id)
        except InvalidId:
            return None
        return self._user_profile_dao.get_user_tags(user_id)

    def set_user_tags(self, user_id: str, tag_ids: list[str]) -> list[str] | None:
        try:
            ObjectId(user_id)
        except InvalidId:
            return None

        # Validate each requested tag id and dedupe.
        valid_new: list[str] = []
        seen: set[str] = set()
        for tid in tag_ids:
            try:
                ObjectId(tid)
            except InvalidId:
                continue
            if tid not in seen and self._tag_dao.find_by_id(tid) is not None:
                valid_new.append(tid)
                seen.add(tid)

        # Remove all existing, then insert fresh.
        self._user_profile_dao.remove_all_tags(user_id)

        for tid in valid_new:
            self._user_profile_dao.add_tag(
                UserTag(user_id=user_id, tag_id=tid, source="user")
            )

        return self._user_profile_dao.get_user_tags(user_id)

    # ---- Event Tags ----------------------------------------------------------

    def get_event_tag_ids(self, event_id: str) -> list[str] | None:
        try:
            ObjectId(event_id)
        except InvalidId:
            return None
        return self._event_tag_dao.get_event_tags(event_id)

    def set_event_tags(self, event_id: str, tag_ids: list[str]) -> list[str] | None:
        try:
            ObjectId(event_id)
        except InvalidId:
            return None

        # Validate each requested tag id and dedupe.
        valid_new: list[str] = []
        seen: set[str] = set()
        for tid in tag_ids:
            try:
                ObjectId(tid)
            except InvalidId:
                continue
            if tid not in seen and self._tag_dao.find_by_id(tid) is not None:
                valid_new.append(tid)
                seen.add(tid)

        event_tag_dao = self._event_tag_dao
        event_tag_dao.remove_all_event_tags(event_id)

        for tid in valid_new:
            event_tag_dao.add_event_tag(EventTag(event_id=event_id, tag_id=tid))

        return event_tag_dao.get_event_tags(event_id)

    def delete_event_tags(self, event_id: str) -> int | None:
        try:
            ObjectId(event_id)
        except InvalidId:
            return None
        return self._event_tag_dao.remove_all_event_tags(event_id)
