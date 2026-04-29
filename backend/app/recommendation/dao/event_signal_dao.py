# Data access for event metadata used by the recommendation service.

from bson import ObjectId
from bson.errors import InvalidId

from app.recommendation.schemas import RecommendedEvent
from app.utils.db import Database, get_database

EVENTS_COLLECTION = "events"
PUBLISHED_STATUS = "published"


class EventSignalDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[EVENTS_COLLECTION]

    def get_published_events_by_ids(self, event_ids: list[str]) -> list[RecommendedEvent]:
        if not event_ids:
            return []

        object_ids: list[ObjectId] = []
        for eid in event_ids:
            try:
                object_ids.append(ObjectId(eid))
            except InvalidId:
                continue

        if not object_ids:
            return []

        docs = self._col.find(
            {"_id": {"$in": object_ids}, "status": PUBLISHED_STATUS}
        )
        by_id: dict[str, RecommendedEvent] = {}
        for doc in docs:
            event = self._to_recommended_event(doc)
            by_id[event.id] = event
        return [by_id[eid] for eid in event_ids if eid in by_id]

    def get_all_published_events(self) -> list[RecommendedEvent]:
        docs = self._col.find({"status": PUBLISHED_STATUS}).sort("created_at", -1)
        return [self._to_recommended_event(doc) for doc in docs]

    @staticmethod
    def _to_recommended_event(doc: dict) -> RecommendedEvent:
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return RecommendedEvent.model_validate(payload)
