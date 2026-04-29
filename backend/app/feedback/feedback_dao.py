# Data access for Feedback documents in MongoDB.

from datetime import datetime, timezone

from app.feedback.model.Feedback import Feedback
from app.utils.db import Database, get_database

FEEDBACK_COLLECTION = "feedback"
FEEDBACK_SESSIONS_COLLECTION = "feedback_sessions"
ATTENDANCE_RECORDS_COLLECTION = "attendance_records"


class FeedbackDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[FEEDBACK_COLLECTION]

    @property
    def _sessions_col(self):
        return self._database.db[FEEDBACK_SESSIONS_COLLECTION]

    @property
    def _attendance_col(self):
        return self._database.db[ATTENDANCE_RECORDS_COLLECTION]

    # Converts a MongoDB document to a Feedback object.
    @staticmethod
    def _to_feedback(doc: dict | None) -> Feedback | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return Feedback.model_validate(payload)


    def insert(self, feedback: Feedback) -> Feedback:
        doc = feedback.model_dump(exclude={"id"}, exclude_none=True)
        result = self._col.insert_one(doc)
        return feedback.model_copy(update={"id": str(result.inserted_id)})

    # Finds all feedback
    def find_by_event(self, event_id: str) -> list[Feedback]:
        cursor = self._col.find({"event_id": event_id}).sort("created_at", -1)
        return [f for doc in cursor if (f := self._to_feedback(doc)) is not None]

    def find_by_user(self, user_id: str) -> list[Feedback]:
        cursor = self._col.find({"participant_id": user_id}).sort("created_at", -1)
        return [f for doc in cursor if (f := self._to_feedback(doc)) is not None]

    # by submit_feedback to detect duplicate submissions
    def find_by_event_and_participant(self, event_id: str, participant_id: str) -> Feedback | None:
        doc = self._col.find_one({"event_id": event_id, "participant_id": participant_id})
        return self._to_feedback(doc)

    # --- Feedback sessions---

    # Opens feedback window
    def enable_feedback(self, event_id: str, eligible_user_ids: list[str]) -> None:
        self._sessions_col.update_one(
            {"event_id": event_id},
            {"$set": {
                "event_id": event_id,
                "eligible_user_ids": eligible_user_ids,
                "enabled_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )

    def is_feedback_enabled(self, event_id: str) -> bool:
        doc = self._sessions_col.find_one({"event_id": event_id})
        return doc is not None

    def get_eligible_user_ids(self, event_id: str) -> list[str]:
        doc = self._sessions_col.find_one({"event_id": event_id})
        if doc is None:
            return []
        return doc.get("eligible_user_ids", [])

    def find_attendees_by_event(self, event_id: str) -> list[str]:
        cursor = self._attendance_col.find({"event_id": event_id})
        user_ids = []
        for doc in cursor:
            user_id = doc.get("user_id")
            if user_id:
                user_ids.append(user_id)
        return user_ids

