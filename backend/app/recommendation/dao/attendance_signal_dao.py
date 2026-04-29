# Data access for attendance signals used by popularity-based recommendations.

from app.utils.db import Database, get_database

ATTENDANCE_RECORDS_COLLECTION = "attendance_records"


class AttendanceSignalDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[ATTENDANCE_RECORDS_COLLECTION]

    def count_attendance_by_event(self) -> dict[str, int]:
        pipeline = [
            {"$match": {"registration_time": {"$ne": None}}},
            {"$group": {"_id": "$event_id", "count": {"$sum": 1}}},
        ]
        return {doc["_id"]: doc["count"] for doc in self._col.aggregate(pipeline)}
