"""
Database access (singleton). Wraps PyMongo client and database handle.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

_instance: "Database | None" = None


class Database:
    """Thin holder for MongoClient and the selected database."""

    def __init__(self) -> None:
        uri = os.getenv("MONGO_URI")
        name = os.getenv("MONGO_DB")
        if not uri or not name:
            raise ValueError("MONGO_URI and MONGO_DB must be set in the environment")
        self.client = MongoClient(uri)
        self.db = self.client[name]


def get_database() -> Database:
    global _instance
    if _instance is None:
        _instance = Database()
    return _instance