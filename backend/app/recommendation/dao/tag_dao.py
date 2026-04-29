# Data access for the tags collection.

from app.recommendation.model.Tag import Tag
from app.utils.db import Database, get_database
from bson import ObjectId

TAGS_COLLECTION = "tags"


class TagDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[TAGS_COLLECTION]

    def insert(self, tag: Tag) -> Tag:
        if self.find_by_slug(tag.slug) is not None:
            raise ValueError(f"Tag with slug '{tag.slug}' already exists")
        doc = tag.model_dump(exclude={"id"}, exclude_none=True)
        result = self._col.insert_one(doc)
        return tag.model_copy(update={"id": str(result.inserted_id)})

    def find_by_slug(self, slug: str) -> Tag | None:
        doc = self._col.find_one({"slug": slug})
        return self._to_tag(doc)

    def find_by_id(self, tag_id: str) -> Tag | None:
        doc = self._col.find_one({"_id": ObjectId(tag_id)})
        return self._to_tag(doc)

    def find_all(self) -> list[Tag]:
        return [self._to_tag(doc) for doc in self._col.find()]

    @staticmethod
    def _to_tag(doc: dict | None) -> Tag | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return Tag.model_validate(payload)
