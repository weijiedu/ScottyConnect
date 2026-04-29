# Data access for user-tag associations — feeds get_user_tags.

from app.recommendation.model.UserTag import UserTag
from app.utils.db import Database, get_database
from bson import ObjectId

USER_TAGS_COLLECTION = "user_tags"


class UserProfileDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[USER_TAGS_COLLECTION]

    def get_user_tags(self, user_id: str) -> list[str]:
        docs = self._col.find({"user_id": ObjectId(user_id)})
        docs = [self._to_user_tag(doc) for doc in docs]
        return [doc.tag_id for doc in docs]

    def add_tag(self, user_tag: UserTag) -> UserTag:
        user_oid = ObjectId(user_tag.user_id)
        tag_oid = ObjectId(user_tag.tag_id)
        if self._col.find_one({"user_id": user_oid, "tag_id": tag_oid}):
            return user_tag
        doc = user_tag.model_dump(exclude={"id"}, exclude_none=True)
        doc["user_id"] = user_oid
        doc["tag_id"] = tag_oid
        result = self._col.insert_one(doc)
        return user_tag.model_copy(update={"id": str(result.inserted_id)})

    def remove_all_tags(self, user_id: str) -> int:
        result = self._col.delete_many({"user_id": ObjectId(user_id)})
        return result.deleted_count

    @staticmethod
    def _to_user_tag(doc: dict) -> UserTag:
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        payload["tag_id"] = str(payload["tag_id"])
        payload["user_id"] = str(payload["user_id"])
        return UserTag.model_validate(payload)
