"""
Notification DAO

Data access object for managing Notification documents in MongoDB.
"""

from app.notification.model.Email import Email, EmailType
from app.utils.db import Database, get_database
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

EMAILS_COLLECTION = "emails"
ATTENDANCE_RECORDS_COLLECTION = "attendance_records"
USERS_COLLECTION = "users"
EVENTS_COLLECTION = "events"
APPOINTMENTS_COLLECTION = "appointments"

class EmailDAO:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    @property
    def _col(self):
        return self._database.db[EMAILS_COLLECTION]

    @property
    def _attendance_col(self):
        return self._database.db[ATTENDANCE_RECORDS_COLLECTION]

    @property
    def _users_col(self):
        return self._database.db[USERS_COLLECTION]
    
    @property
    def _events_col(self):
        return self._database.db[EVENTS_COLLECTION]

    @property
    def _appointments_col(self):
        return self._database.db[APPOINTMENTS_COLLECTION]

    def insert(self, email: Email) -> Email:
        # Keep datetimes as native BSON datetimes so range queries work.
        doc = email.model_dump(mode="python", exclude={"id"}, exclude_none=True)
        result = self._col.insert_one(doc)
        return email.model_copy(update={"id": str(result.inserted_id)})

    def update_sent_successfully(self, email_id: str) -> bool:
        result = self._col.update_one({"_id": ObjectId(email_id)}, {"$set": {"sent_successfully": True}})
        return result.modified_count > 0

    def find_by_recipient_email(self, recipient_email: str) -> list[Email]:
        emails = self._col.find({"recipient_email": recipient_email}).sort("created_at", -1)
        return [e for doc in emails if (e := self._to_email(doc)) is not None]

    def find_confirmation_email(self, recipient_email: str, event_id: str) -> Email | None:
        # Find the most recent confirmation email or cancellation email for a given recipient and event
        email = self._col.find_one(
            {
                "recipient_email": recipient_email,
                "event_id": event_id,
                "email_type": {
                    "$in": [
                        EmailType.EVENT_REGISTRATION_CONFIRMATION.value,
                        EmailType.EVENT_REGISTRATION_CANCELLED.value,
                    ]
                },
            },
            sort=[("created_at", -1)]
        )
        return self._to_email(email)

    def find_registered_user_emails(self, event_id: str) -> list[str]:
        records = self._attendance_col.find({"event_id": event_id})
        recipient_emails: list[str] = []
        seen_emails: set[str] = set()
        for record in records:
            user_id = record.get("user_id")
            if not user_id:
                continue
            try:
                user_doc = self._users_col.find_one({"_id": ObjectId(user_id)})
            except InvalidId:
                continue
            if not user_doc:
                continue
            email = user_doc.get("email")
            if isinstance(email, str) and email not in seen_emails:
                seen_emails.add(email)
                recipient_emails.append(email)
        return recipient_emails

    def find_user_name_by_id(self, user_id: str) -> str | None:
        user_doc = self._users_col.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            return None
        username = user_doc.get("username")
        return username  

    def find_user_email_by_id(self, user_id: str) -> str | None:
        try:
            user_doc = self._users_col.find_one({"_id": ObjectId(user_id)})
        except InvalidId:
            return None
        if not user_doc:
            return None
        email = user_doc.get("email")
        return email if isinstance(email, str) else None

    def find_event_owner_email(self, event_id: str) -> str | None:
        event_doc = self.find_event_doc_by_id(event_id)
        if not event_doc:
            return None
        owner_id = event_doc.get("owner_id")
        if not isinstance(owner_id, str):
            return None
        return self.find_user_email_by_id(owner_id)

    def find_event_info(self, event_id: str) -> dict | None:
        event_doc = self.find_event_doc_by_id(event_id)
        if not event_doc:
            return None
        return {
            "id": event_id,
            "title": event_doc.get("title", ""),
            "description": event_doc.get("description", ""),
            "date": event_doc.get("date", ""),
            "start_time": event_doc.get("start_time", ""),
            "end_time": event_doc.get("end_time", ""),
            "location": event_doc.get("location", ""),
        }
    
    def find_unsent_emails(self) -> list[Email]:
        # Backward compatible: previously, some rows stored send_time as strings.
        # Load unsent emails first, then compare in Python after model parsing.
        now = datetime.now(timezone.utc)
        emails = self._col.find({"sent_successfully": False}).sort("created_at", -1)
        ready_to_send: list[Email] = []
        for doc in emails:
            email = self._to_email(doc)
            if email is None:
                continue
            send_time = self._normalize_utc(email.send_time)
            if send_time is None or send_time <= now:
                ready_to_send.append(email)
        return ready_to_send
    
    def delete(self, email_id: str) -> bool:
        result = self._col.delete_one({"_id": ObjectId(email_id)})
        return result.deleted_count > 0
    
    def delete_reminder(self, event_id: str, recipient_email: str) -> bool:
        result = self._col.delete_one({"event_id": event_id, "recipient_email": recipient_email, "email_type": EmailType.EVENT_REMINDER.value})
        return result.deleted_count > 0
    
    def delete_all_reminders_by_event_id(self, event_id: str) -> bool:
        result = self._col.delete_many({"event_id": event_id, "email_type": EmailType.EVENT_REMINDER.value})
        return result.deleted_count > 0

    def find_event_doc_by_id(self, event_id: str) -> dict | None:
        try:
            event_doc = self._events_col.find_one({"_id": ObjectId(event_id)})
        except InvalidId:
            return None
        return event_doc

    def find_coffee_chat_info(self, invite_id: str) -> dict | None:
        appointment_doc = self._appointments_col.find_one({"_id": ObjectId(invite_id)})
        if not appointment_doc:
            return None
        return {
            "id": invite_id,
            "sender_id": appointment_doc.get("sender_id"),
            "receiver_id": appointment_doc.get("receiver_id"),
            "scheduled_at": appointment_doc.get("scheduled_at"),
            "status": appointment_doc.get("status"),
            "created_at": appointment_doc.get("created_at"),
            "updated_at": appointment_doc.get("updated_at"),
        }

    @staticmethod
    def _to_email(doc: dict | None) -> Email | None:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return Email.model_validate(payload)

    @staticmethod
    def _normalize_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)