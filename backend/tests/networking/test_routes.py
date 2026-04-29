import os
import unittest
from flask import Flask
from unittest.mock import patch

from app.networking.routes import networking
from app.networking.schemas import AppointmentResponse, BusySlotsResponse
from app.utils.jwt import JWT


class _StubNetworkingService:
    def request_invite(self, req, sender_id: str):
        return AppointmentResponse(message="Invitation sent successfully", code=201)

    def process_invite_response(self, req, responder_id: str):
        return AppointmentResponse(message="Invitation accepted successfully", code=200)

    def cancel_invite(self, invite_id: str, sender_id: str):
        return AppointmentResponse(message="Invitation cancelled successfully", code=200)

    def get_appointments(self, user_id: str):
        return [
            {
                "id": "invite-1",
                "sender_id": "sender-1",
                "sender_name": "sender",
                "receiver_id": "receiver-1",
                "receiver_name": "receiver",
                "scheduled_at": "2026-04-14T10:00:00",
                "status": "PENDING",
            }
        ]

    def get_busy_slots(self, user_id: str):
        return BusySlotsResponse(busy_slots=["Tue, Apr 14 @ 10:00 AM"], code=200)


class NetworkingRoutesTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["JWT_SECRET"] = "test-secret"
        app = Flask(__name__)
        app.register_blueprint(networking, url_prefix="/api/networking")
        self.client = app.test_client()
        token = JWT(secret_key="test-secret").generate_token("receiver-1")
        self.auth_headers = {"Authorization": f"Bearer {token}"}
        self._service_patch = patch(
            "app.networking.routes.get_networking_service",
            return_value=_StubNetworkingService(),
        )
        self._service_patch.start()

    def tearDown(self) -> None:
        self._service_patch.stop()

    def test_respond_endpoint_success(self):
        res = self.client.post(
            "/api/networking/respond",
            json={"invite_id": "invite-1", "accept": True},
            headers=self.auth_headers,
        )
        body = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(body["message"], "Invitation accepted successfully")

    def test_respond_endpoint_rejects_missing_auth(self):
        res = self.client.post(
            "/api/networking/respond",
            json={"invite_id": "invite-1", "accept": True},
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("message", res.get_json())

    def test_respond_endpoint_rejects_missing_json(self):
        res = self.client.post("/api/networking/respond", headers=self.auth_headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("message", res.get_json())

    def test_get_appointments_endpoint_shape(self):
        res = self.client.get("/api/networking/appointments/receiver-1", headers=self.auth_headers)
        body = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(body["appointments"], list)
        self.assertEqual(body["code"], 200)


if __name__ == "__main__":
    unittest.main()
