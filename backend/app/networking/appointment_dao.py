"""
Appointment DAO
Data access object for managing Appointment documents in MongoDB.
"""

from datetime import datetime, time, timezone
from typing import List, Optional
from bson import ObjectId

from app.networking.model.Appointment import Appointment, AppointmentStatus
from app.networking.utils import get_la_day_boundaries_in_utc, format_to_la_display
from app.utils.db import Database, get_database

EVENTS_COLLECTION = "events"
APPOINTMENTS_COLLECTION = "appointments"


class AppointmentDAO:
    # Handles persistence logic for coffee chat appointments.
    
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or get_database()

    # Returns the MongoDB collection for appointments.
    @property
    def _col(self):
        return self._database.db[APPOINTMENTS_COLLECTION]

    # Inserts a new appointment record.
    def insert(self, appointment: Appointment) -> Appointment:
        doc = appointment.model_dump(exclude={"id"}, exclude_none=True)
        # Ensure status is stored as string
        doc["status"] = appointment.status.value
        result = self._col.insert_one(doc)
        return appointment.model_copy(update={"id": str(result.inserted_id)})

    # Finds an appointment by its internal ObjectID.
    def find_by_id(self, appointment_id: str) -> Optional[Appointment]:
        try:
            doc = self._col.find_one({"_id": ObjectId(appointment_id)})
            return self._to_appointment(doc)
        except Exception:
            return None

    # Updates the status and timestamp of an existing appointment.
    def update_status(self, appointment_id: str, status: AppointmentStatus) -> bool:
        try:
            now = datetime.now(timezone.utc)
            res = self._col.update_one(
                {"_id": ObjectId(appointment_id)},
                {"$set": {"status": status.value, "updated_at": now}},
            )
            return res.modified_count > 0
        except Exception:
            return False

    # Atomically updates status only when current status matches expected.
    # This prevents race conditions by ensuring the status hasn't changed
    # between reading and writing in concurrent scenarios.
    def update_status_atomically(
        self,
        appointment_id: str,
        expected_status: AppointmentStatus,
        new_status: AppointmentStatus,
    ) -> bool:
        try:
            now = datetime.now(timezone.utc)
            res = self._col.update_one(
                {"_id": ObjectId(appointment_id), "status": expected_status.value},
                {"$set": {"status": new_status.value, "updated_at": now}},
            )
            return res.modified_count > 0
        except Exception:
            return False

    # Counts non-declined appointments for a user on a given calendar day.
    def count_by_user_and_date(self, user_id: str, date: datetime) -> int:
        # Determine the "day" boundary in LA time context
        start_of_day, end_of_day = get_la_day_boundaries_in_utc(date)
        
        query = {
            "sender_id": user_id,
            "created_at": {"$gte": start_of_day, "$lte": end_of_day},
            "status": {"$in": [AppointmentStatus.PENDING.value, AppointmentStatus.ACCEPTED.value]}
        }

        return self._col.count_documents(query)

    # Counts distinct receivers invited by sender for a receiver role on a given day.
    def count_distinct_receivers_by_sender_role_and_day(
        self,
        sender_id: str,
        receiver_role: str = "ALUMNI",
        date: datetime | None = None,
    ) -> int:
        date = date or datetime.now(timezone.utc)
        # Determine the "day" boundary in LA time context
        start_of_day, end_of_day = get_la_day_boundaries_in_utc(date)
        receiver_ids = self._col.distinct(
            "receiver_id",
            {
                "sender_id": sender_id,
                "receiver_role": receiver_role.upper(),
                "created_at": {"$gte": start_of_day, "$lte": end_of_day},
                "status": {"$in": [AppointmentStatus.PENDING.value, AppointmentStatus.ACCEPTED.value]},
            },

        )
        return len(receiver_ids)

    # Checks whether sender already invited specific receiver role target on a given day.
    def has_invited_receiver_by_sender_role_and_day(
        self,
        sender_id: str,
        receiver_id: str,
        receiver_role: str = "ALUMNI",
        date: datetime | None = None,
    ) -> bool:
        date = date or datetime.now(timezone.utc)
        # Determine the "day" boundary in LA time context
        start_of_day, end_of_day = get_la_day_boundaries_in_utc(date)
        return (
            self._col.count_documents(
                {
                    "sender_id": sender_id,
                    "receiver_id": receiver_id,
                    "receiver_role": receiver_role.upper(),
                    "created_at": {"$gte": start_of_day, "$lte": end_of_day},
                    "status": {"$in": [AppointmentStatus.PENDING.value, AppointmentStatus.ACCEPTED.value]},
                },

                limit=1,
            )
            > 0
        )
        
    # Checks if there is an active/upcoming interaction (Pending or Accepted) 
    # between two users in either direction that is scheduled for the future.
    def has_active_meeting_between_users(self, user_a: str, user_b: str, now: datetime) -> bool:
        query = {
            "$or": [
                {"sender_id": user_a, "receiver_id": user_b},
                {"sender_id": user_b, "receiver_id": user_a}
            ],
            "status": {"$in": [AppointmentStatus.PENDING.value, AppointmentStatus.ACCEPTED.value]},
            "scheduled_at": {"$gt": now}
        }
        return self._col.count_documents(query, limit=1) > 0

    # Returns all appointments where the user is either the sender or receiver.
    def find_all_by_user(self, user_id: str) -> List[Appointment]:
        cursor = self._col.find({
            "$or": [{"sender_id": user_id}, {"receiver_id": user_id}]
        }).sort("created_at", -1)

        return [self._to_appointment(doc) for doc in cursor if doc]

    # Returns a list of timeslot strings for all non-declined/non-cancelled meetings.
    def get_occupied_slots(self, user_id: str) -> List[str]:
        cursor = self._col.find({
            "$or": [{"sender_id": user_id}, {"receiver_id": user_id}],
            "status": AppointmentStatus.ACCEPTED.value
        }, {"scheduled_at": 1})

        slots: List[str] = []
        for doc in cursor:
            scheduled_at = doc.get("scheduled_at")
            if isinstance(scheduled_at, datetime):
                slots.append(format_to_la_display(scheduled_at))

        return slots

    # Helper to convert MongoDB document to Appointment Pydantic model.
    def _to_appointment(self, doc: dict | None) -> Optional[Appointment]:
        if doc is None:
            return None
        payload = dict(doc)
        oid = payload.pop("_id", None)
        if oid is not None:
            payload["id"] = str(oid)
        return Appointment.model_validate(payload)

