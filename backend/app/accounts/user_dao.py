# Data access for User documents in MongoDB.

from datetime import datetime, timezone

from bson import ObjectId

from app.accounts.model.User import User
from app.utils.db import Database, get_database

USERS_COLLECTION = "users"


class UserDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[USERS_COLLECTION]

    def insert(self, user: User) -> User:
        if self.find_by_email(user.email) is not None:
            raise ValueError("Email already registered")
        if self.find_by_username(user.username) is not None:
            raise ValueError("Username already taken")
        doc = user.model_dump(exclude={"id"}, exclude_none=True)
        result = self._col.insert_one(doc)
        return user.model_copy(update={"id": str(result.inserted_id)})

    def find_by_email(self, email: str) -> User | None:
        doc = self._col.find_one({"email": email})
        return self._to_user(doc)

    def find_by_username(self, username: str) -> User | None:
        doc = self._col.find_one({"username": username})
        return self._to_user(doc)

    def find_by_id(self, user_id: str) -> User | None:
        """Finds a user by their internal ObjectID."""
        try:
            doc = self._col.find_one({"_id": ObjectId(user_id)})
            return self._to_user(doc)
        except Exception:
            return None

    def set_verified(self, email: str, verified: bool) -> bool:
        now = datetime.now(timezone.utc)
        res = self._col.update_one(
            {"email": email},
            {"$set": {"verified": verified, "updated_at": now}},
        )
        return res.modified_count > 0

    def update(self, user: User) -> bool:
        """Updates an existing user record in the database."""
        if not user.id:
            return False
        doc = user.model_dump(exclude={"id"}, exclude_none=True)
        res = self._col.update_one(
            {"_id": ObjectId(user.id)},
            {"$set": doc}
        )
        return res.modified_count > 0

    @staticmethod
    def _to_user(doc: dict | None) -> User | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return User.model_validate(payload)