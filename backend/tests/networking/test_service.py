import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import patch

from app.networking.model.Appointment import Appointment, AppointmentStatus
from app.networking.schemas import RespondRequest
from app.networking.service import NetworkingService


@dataclass
class _User:
    id: str
    username: str
    role: str


class _UserRepo:
    def __init__(self, users: dict[str, _User]) -> None:
        self._users = users

    def find_by_id(self, user_id: str):
        return self._users.get(user_id)


class _AccountService:
    def __init__(self, users: dict[str, _User]) -> None:
        self._users = _UserRepo(users)


class _FakeAppointmentDAO:
    def __init__(self, appointments: dict[str, Appointment] | None = None) -> None:
        self._appointments = appointments or {}

    def find_by_id(self, appointment_id: str):
        return self._appointments.get(appointment_id)

    def update_status_atomically(
        self,
        appointment_id: str,
        expected_status: AppointmentStatus,
        new_status: AppointmentStatus,
    ) -> bool:
        appt = self._appointments.get(appointment_id)
        if appt is None or appt.status != expected_status:
            return False
        self._appointments[appointment_id] = appt.model_copy(update={"status": new_status})
        return True


class NetworkingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.users = {
            "sender-1": _User(id="sender-1", username="sender", role="STUDENT"),
            "receiver-1": _User(id="receiver-1", username="receiver", role="ALUMNI"),
            "intruder-1": _User(id="intruder-1", username="intruder", role="ALUMNI"),
        }
        self.account_service = _AccountService(self.users)

    def _make_service(self, status: AppointmentStatus = AppointmentStatus.PENDING) -> NetworkingService:
        appt = Appointment(
            id="invite-1",
            sender_id="sender-1",
            receiver_id="receiver-1",
            scheduled_at=datetime(2025, 4, 14, 10, 0, tzinfo=timezone.utc),
            status=status,
        )
        dao = _FakeAppointmentDAO({"invite-1": appt})
        return NetworkingService(dao=dao)

    def test_respond_rejects_non_receiver(self):
        service = self._make_service(AppointmentStatus.PENDING)
        req = RespondRequest(invite_id="invite-1", accept=True)

        with patch("app.networking.service.get_account_service", return_value=self.account_service):
            resp = service.process_invite_response(req, responder_id="intruder-1")

        self.assertEqual(resp.code, 403)
        self.assertIn("receiver", resp.message.lower())

    def test_respond_rejects_non_pending(self):
        service = self._make_service(AppointmentStatus.CANCELLED)
        req = RespondRequest(invite_id="invite-1", accept=True)

        with patch("app.networking.service.get_account_service", return_value=self.account_service):
            resp = service.process_invite_response(req, responder_id="receiver-1")

        self.assertEqual(resp.code, 400)
        self.assertIn("cannot respond", resp.message.lower())

    def test_respond_accepts_pending_for_receiver(self):
        service = self._make_service(AppointmentStatus.PENDING)
        req = RespondRequest(invite_id="invite-1", accept=True)

        with patch("app.networking.service.get_account_service", return_value=self.account_service):
            resp = service.process_invite_response(req, responder_id="receiver-1")

        self.assertEqual(resp.code, 200)
        self.assertIn("accepted", resp.message.lower())

    def test_cancel_rejects_non_sender(self):
        service = self._make_service(AppointmentStatus.PENDING)

        resp = service.cancel_invite(appointment_id="invite-1", sender_id="receiver-1")

        self.assertEqual(resp.code, 403)
        self.assertIn("unauthorized", resp.message.lower())

    def test_cancel_succeeds_for_pending_sender(self):
        service = self._make_service(AppointmentStatus.PENDING)

        resp = service.cancel_invite(appointment_id="invite-1", sender_id="sender-1")

        self.assertEqual(resp.code, 200)
        self.assertIn("cancelled", resp.message.lower())


if __name__ == "__main__":
    unittest.main()
