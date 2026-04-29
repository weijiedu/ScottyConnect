from __future__ import annotations

from datetime import datetime
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from app.networking.appointment_dao import AppointmentDAO


# Role-aware policy for checking whether an invite can be sent.
class InvitePolicy(Protocol):

    def can_send_invite(
        self,
        sender_id: str,
        receiver_role: str,
        receiver_id: str,
        scheduled_at: datetime,
        dao: "AppointmentDAO",
        now: datetime,
    ) -> tuple[bool, str | None]:
        ...


# Student rule:
# - no cap when inviting students
# - max 3 distinct alumni invite targets per day
class StudentInvitePolicy:

    def can_send_invite(
        self,
        sender_id: str,
        receiver_role: str,
        receiver_id: str,
        scheduled_at: datetime,
        dao: "AppointmentDAO",
        now: datetime,
    ) -> tuple[bool, str | None]:
        if dao.has_active_meeting_between_users(sender_id, receiver_id, now):
            return False, "You already have an active interaction with this person"

        if receiver_role.upper() != "ALUMNI":
            return True, None

        if dao.has_invited_receiver_by_sender_role_and_day(
            sender_id=sender_id,
            receiver_id=receiver_id,
            receiver_role="ALUMNI",
            date=now,
        ):
            return True, None

        distinct_alumni = dao.count_distinct_receivers_by_sender_role_and_day(
            sender_id=sender_id,
            receiver_role="ALUMNI",
            date=now,
        )
        if distinct_alumni >= 3:
            return False, "Students may invite at most 3 distinct alumni per day"

        return True, None


# Alumni rule: no invite cap.
class AlumniInvitePolicy:

    def can_send_invite(
        self,
        sender_id: str,
        receiver_role: str,
        receiver_id: str,
        scheduled_at: datetime,
        dao: "AppointmentDAO",
        now: datetime,
    ) -> tuple[bool, str | None]:
        if dao.has_active_meeting_between_users(sender_id, receiver_id, now):
            return False, "You already have an active interaction with this person"
            
        return True, None
