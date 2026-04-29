from bson import ObjectId
from bson.errors import InvalidId

from app.accounts.model.User import User
from app.attendance.model.AttendanceRecord import AttendanceRecord
from app.lifecycle.model.Event import Event
from app.utils.db import Database, get_database

ATTENDANCE_RECORDS_COLLECTION = "attendance_records"
EVENTS_COLLECTION = "events"
USERS_COLLECTION = "users"

class AttendanceDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[ATTENDANCE_RECORDS_COLLECTION]
    
    @property
    def _events_col(self):
        return self._database.db[EVENTS_COLLECTION]
    
    @property
    def _users_col(self):
        return self._database.db[USERS_COLLECTION]

    # Converts a MongoDB document to a User object.
    @staticmethod
    def _to_user(doc: dict | None) -> User | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return User.model_validate(payload)

    # Converts a MongoDB document to an Event object.
    @staticmethod
    def _to_event(doc: dict | None) -> Event | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return Event.model_validate(payload)
    
    # Converts a MongoDB document to an AttendanceRecord object.
    @staticmethod
    def _to_attendance_record(doc: dict | None) -> AttendanceRecord | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return AttendanceRecord.model_validate(payload)

    # Finds an event by id.
    def find_event_by_id(self, event_id: str) -> Event | None:
        try:
            doc = self._events_col.find_one({"_id": ObjectId(event_id)})
        except InvalidId:
            return None
        return self._to_event(doc)

    # Finds an attendance record by event and user id.
    def find_record_by_event_and_user(self, event_id: str, user_id: str) -> AttendanceRecord | None:
        doc = self._col.find_one({"event_id": event_id, "user_id": user_id})
        return self._to_attendance_record(doc)

    # Inserts a new attendance record into the database.
    def insert(self, attendance_record: AttendanceRecord) -> AttendanceRecord:
        doc = attendance_record.model_dump(exclude={"id"}, exclude_none=True)
        result = self._col.insert_one(doc)
        return attendance_record.model_copy(update={"id": str(result.inserted_id)})
    
    # Deletes an attendance record from the database.
    def delete(self, attendance_record_id: str) -> bool:
        try:
            result = self._col.delete_one({"_id": ObjectId(attendance_record_id)})
        except InvalidId:
            return False
        return result.deleted_count > 0
    
    # Updates an attendance record in the database.
    def update(self, attendance_record_id: str, updates: dict) -> bool:
        try:
            result = self._col.update_one({"_id": ObjectId(attendance_record_id)}, {"$set": updates})
        except InvalidId:
            return False
        return result.modified_count > 0
    
    # Gets all registered users for an event.
    def get_registered_users(self, event_id: str) -> list[User]:
        docs = self._col.find({"event_id": event_id})
        users: list[User] = []
        for doc in docs:
            user_id = doc.get("user_id")
            if not user_id:
                continue
            try:
                user_doc = self._users_col.find_one({"_id": ObjectId(user_id)})
            except InvalidId:
                continue
            user = self._to_user(user_doc)
            if user:
                users.append(user)
        return users
    
    # Gets all attended users for an event.
    def get_attended_users(self, event_id: str) -> list[User]:
        docs = self._col.find({"event_id": event_id, "attendance_time": {"$ne": None}})
        users: list[User] = []
        for doc in docs:
            user_id = doc.get("user_id")
            if not user_id:
                continue
            try:
                user_doc = self._users_col.find_one({"_id": ObjectId(user_id)})
            except InvalidId:
                continue
            user = self._to_user(user_doc)
            if user:
                users.append(user)
        return users

    # Gets all registered events for a user.
    def get_registered_events(self, user_id: str) -> list[Event]:
        docs = self._col.find({"user_id": user_id})
        events: list[Event] = []
        for doc in docs:
            event_id = doc.get("event_id")
            if not event_id:
                continue
            try:
                event_doc = self._events_col.find_one({"_id": ObjectId(event_id)})
            except InvalidId:
                continue
            event = self._to_event(event_doc)
            if event:
                events.append(event)
        return events
    
    # Gets all attended events for a user.
    def get_attended_events(self, user_id: str) -> list[Event]:
        docs = self._col.find({"user_id": user_id, "attendance_time": {"$ne": None}})
        events: list[Event] = []
        for doc in docs:
            event_id = doc.get("event_id")
            if not event_id:
                continue
            try:
                event_doc = self._events_col.find_one({"_id": ObjectId(event_id)})
            except InvalidId:
                continue
            event = self._to_event(event_doc)
            if event:
                events.append(event)
        return events
    
    def find_user_by_id(self, user_id: str) -> User | None:
        doc = self._users_col.find_one({"_id": ObjectId(user_id)})
        return self._to_user(doc)
    
    def find_user_by_email(self, email: str) -> User | None:
        doc = self._users_col.find_one({"email": email})
        return self._to_user(doc)