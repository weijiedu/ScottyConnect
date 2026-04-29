"""
DAO for logging, persists logs to MongoDB.
"""

from app.utils.db import Database, get_database
from app.logging.Model.Log import Log, LogLevel

LOGGING_COLLECTION = "logging"

class LoggerDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[LOGGING_COLLECTION]

    def insert(self, log: Log) -> Log:
        doc = log.model_dump(exclude={"id"}, exclude_none=True)
        result = self._col.insert_one(doc)
        return log.model_copy(update={"id": str(result.inserted_id)})