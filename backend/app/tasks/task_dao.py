from datetime import datetime, timezone

from bson import ObjectId

from app.tasks.model.Task import Task
from app.utils.db import Database, get_database

TASKS_COLLECTION = "tasks"


class TaskDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[TASKS_COLLECTION]

    def insert(self, task: Task) -> Task:
        doc = task.model_dump(exclude={"id"}, exclude_none=True)
        result = self._col.insert_one(doc)
        return task.model_copy(update={"id": str(result.inserted_id)})

    def find_by_id(self, task_id: str) -> Task | None:
        doc = self._col.find_one({"_id": ObjectId(task_id)})
        return self._to_task(doc)

    def find_by_event(self, event_id: str) -> list[Task]:
        docs = self._col.find({"event_id": event_id})
        return [t for d in docs if (t := self._to_task(d)) is not None]

    def update(self, task_id: str, updates: dict) -> Task | None:
        updates["updated_at"] = datetime.now(timezone.utc)
        self._col.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": updates},
        )
        return self.find_by_id(task_id)

    def delete(self, task_id: str) -> bool:
        result = self._col.delete_one({"_id": ObjectId(task_id)})
        return result.deleted_count > 0

    def delete_subtree(self, parent_id: str) -> int:
        """Recursively delete all descendants of *parent_id*."""
        children = list(self._col.find({"parent_id": parent_id}))
        count = 0
        for child in children:
            child_id = str(child["_id"])
            count += self.delete_subtree(child_id)
            self._col.delete_one({"_id": child["_id"]})
            count += 1
        return count

    def bulk_update_status_for_event(
        self, event_id: str, new_status: str, *, skip_completed: bool = False
    ) -> int:
        # Set status of every task belonging to event_id
        query: dict = {"event_id": event_id}

        if skip_completed:
            query["status"] = {"$ne": "completed"}
        result = self._col.update_many(
            query,
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count

    @staticmethod
    def _to_task(doc: dict | None) -> Task | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)

        if oid is not None:
            payload["id"] = str(oid)
            
        return Task.model_validate(payload)
