# Data access for per-user recommendation preferences.

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId

from app.recommendation.model.UserRecommendationPreference import UserRecommendationPreference
from app.utils.db import Database, get_database

PREFERENCES_COLLECTION = "user_recommendation_preferences"


class UserPreferenceDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[PREFERENCES_COLLECTION]

    def get_preference(self, user_id: str) -> UserRecommendationPreference | None:
        try:
            user_oid = ObjectId(user_id)
        except InvalidId:
            return None

        doc = self._col.find_one({"user_id": user_oid})
        if doc is None:
            return None
        return self._to_preference(doc)

    def upsert_preference(
        self, user_id: str, preferred_strategy: str
    ) -> UserRecommendationPreference | None:
        try:
            user_oid = ObjectId(user_id)
        except InvalidId:
            return None

        now = datetime.now(timezone.utc)
        self._col.update_one(
            {"user_id": user_oid},
            {
                "$set": {
                    "preferred_strategy": preferred_strategy,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "user_id": user_oid,
                    "created_at": now,
                },
            },
            upsert=True,
        )

        doc = self._col.find_one({"user_id": user_oid})
        return self._to_preference(doc) if doc is not None else None

    @staticmethod
    def _to_preference(doc: dict) -> UserRecommendationPreference:
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        payload["user_id"] = str(payload["user_id"])
        return UserRecommendationPreference.model_validate(payload)
