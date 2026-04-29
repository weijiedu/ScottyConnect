import unittest
from datetime import datetime, timezone

from unittest.mock import patch

from app.bus.message import MessageType
from app.networking.mediator import NetworkingMediator
from app.networking.model.Appointment import Appointment, AppointmentStatus
from app.networking.model.Participant import AlumniAttendee, StudentAttendee


class _FakeDAO:
    def __init__(self) -> None:
        self.distinct_alumni_count = 0
        self.already_invited_alumni_ids: set[str] = set()
        self.occupied: dict[str, list[str]] = {}
        self.update_status_result = True
        self.inserted: list[Appointment] = []

    def count_distinct_receivers_by_sender_role_and_day(
        self,
        sender_id: str,
        receiver_role: str = "ALUMNI",
        date: datetime | None = None,
    ) -> int:
        return self.distinct_alumni_count

    def has_invited_receiver_by_sender_role_and_day(
        self,
        sender_id: str,
        receiver_id: str,
        receiver_role: str = "ALUMNI",
        date: datetime | None = None,
    ) -> bool:
        return receiver_id in self.already_invited_alumni_ids

    def has_pending_invite_between_users(self, sender_id: str, receiver_id: str) -> bool:
        return False

    def get_occupied_slots(self, user_id: str):
        return self.occupied.get(user_id, [])

    def insert(self, appointment: Appointment) -> Appointment:
        self.inserted.append(appointment)
        return appointment.model_copy(update={"id": "invite-1"})

    def update_status_atomically(
        self,
        appointment_id: str,
        expected_status: AppointmentStatus,
        new_status: AppointmentStatus,
    ) -> bool:
        return self.update_status_result


class NetworkingMediatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dao = _FakeDAO()
        self.mediator = NetworkingMediator(self.dao)
        
        self.patcher = patch('app.networking.mediator.MessageBus.publish')
        self.mock_publish = self.patcher.start()
        self.student = StudentAttendee(user_id="stu-1", username="stu")
        self.student.set_mediator(self.mediator)
        self.alumni = AlumniAttendee(user_id="alm-1", username="alm")
        self.alumni.set_mediator(self.mediator)

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_student_alumni_distinct_daily_cap_enforced(self):
        self.dao.distinct_alumni_count = 3
        ok = self.mediator.dispatch_invite(
            self.student,
            receiver_id="alm-4",
            scheduled_at=datetime(2025, 4, 14, 10, 0, tzinfo=timezone.utc),
            receiver_role="ALUMNI",
        )
        self.assertFalse(ok)
        self.assertEqual(self.mock_publish.call_count, 0)
        self.assertEqual(len(self.dao.inserted), 0)

    def test_availability_conflict_blocks_invite(self):
        slot = "Mon, Apr 14 @ 10:00 AM"
        self.dao.occupied["stu-1"] = [slot]
        ok = self.mediator.dispatch_invite(
            self.student,
            receiver_id="alm-2",
            scheduled_at=datetime(2025, 4, 14, 10, 0, tzinfo=timezone.utc),
            receiver_role="ALUMNI",
        )
        self.assertFalse(ok)
        self.assertEqual(self.mock_publish.call_count, 0)
        self.assertEqual(len(self.dao.inserted), 0)

    def test_publishes_requested_on_successful_invite(self):
        ok = self.mediator.dispatch_invite(
            self.student,
            receiver_id="alm-2",
            scheduled_at=datetime(2025, 4, 14, 10, 0, tzinfo=timezone.utc),
            receiver_role="ALUMNI",
        )
        self.assertTrue(ok)
        self.assertEqual(self.mock_publish.call_count, 1)
        msg = self.mock_publish.call_args[0][0]
        self.assertEqual(msg.type, MessageType.COFFEE_CHAT_REQUESTED)
        self.assertEqual(msg.data["sender_id"], "stu-1")

    def test_publishes_accepted_on_successful_accept(self):
        ok = self.mediator.finalize_invite_response(self.alumni, invite_id="invite-1", accept=True)
        self.assertTrue(ok)
        self.assertEqual(self.mock_publish.call_count, 1)
        msg = self.mock_publish.call_args[0][0]
        self.assertEqual(msg.type, MessageType.COFFEE_CHAT_ACCEPTED)
        self.assertEqual(msg.data["invite_id"], "invite-1")

    def test_publishes_declined_on_successful_decline(self):
        ok = self.mediator.finalize_invite_response(self.alumni, invite_id="invite-1", accept=False)
        self.assertTrue(ok)
        self.assertEqual(self.mock_publish.call_count, 1)
        msg = self.mock_publish.call_args[0][0]
        self.assertEqual(msg.type, MessageType.COFFEE_CHAT_DECLINED)

    def test_atomic_transition_conflict_path(self):
        self.dao.update_status_result = False
        ok = self.mediator.finalize_invite_response(self.alumni, invite_id="invite-1", accept=True)
        self.assertFalse(ok)
        self.assertEqual(self.mock_publish.call_count, 0)


if __name__ == "__main__":
    unittest.main()
