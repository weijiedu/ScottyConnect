# Data access for event-tag associations.

from app.recommendation.model.EventTag import EventTag
from app.utils.db import Database, get_database
from bson import ObjectId

EVENT_TAGS_COLLECTION = "event_tags"


class EventTagDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[EVENT_TAGS_COLLECTION]

    def find_event_ids_by_tags(self, tag_ids: list[str]) -> dict[str, int]:
        docs = self._col.find({"tag_id": {"$in": [ObjectId(tag_id) for tag_id in tag_ids]}})
        scores: dict[str, int] = {}
        for doc in docs:
            event_id = str(doc["event_id"])
            scores[event_id] = scores.get(event_id, 0) + 1
        return scores

    def add_event_tag(self, event_tag: EventTag) -> EventTag:
        event_oid = ObjectId(event_tag.event_id)
        tag_oid = ObjectId(event_tag.tag_id)
        if self._col.find_one({"event_id": event_oid, "tag_id": tag_oid}):
            return event_tag
        doc = event_tag.model_dump(exclude={"id"}, exclude_none=True)
        doc["event_id"] = event_oid
        doc["tag_id"] = tag_oid
        result = self._col.insert_one(doc)
        return event_tag.model_copy(update={"id": str(result.inserted_id)})

    def remove_event_tag(self, event_id: str, tag_id: str) -> bool:
        result = self._col.delete_one({"event_id": ObjectId(event_id), "tag_id": ObjectId(tag_id)})
        return result.deleted_count > 0

    def get_event_tags(self, event_id: str) -> list[str]:
        docs = self._col.find({"event_id": ObjectId(event_id)})
        return [str(doc["tag_id"]) for doc in docs]

    def remove_all_event_tags(self, event_id: str) -> int:
        result = self._col.delete_many({"event_id": ObjectId(event_id)})
        return result.deleted_count

    def get_all_event_ids(self) -> list[str]:
        return list(self._col.distinct("event_id"))

    @staticmethod
    def _to_event_tag(doc: dict) -> EventTag:
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        payload["event_id"] = str(payload["event_id"])
        payload["tag_id"] = str(payload["tag_id"])
        return EventTag.model_validate(payload)
