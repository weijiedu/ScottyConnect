"""
Routes for the attendance service.
"""

from flask import Blueprint, g, jsonify

from app.attendance.schemas import (
    AttendanceRecordResponse,
    RegisterEventResponse,
    AttendEventResponse,
    ListEventsResponse,
)

from app.utils.auth import require_auth
from app.utils.doc import doc
from app.attendance.service import get_attendance_service

attendance = Blueprint("attendance", __name__)

@attendance.route("/register/events/<event_id>/users", methods=["GET"])
@require_auth
@doc(
    response=AttendanceRecordResponse,
    description="Retrieve all registered users for an event",
    tags=["attendance"],
    success_status=200,
)
def get_registered_users(event_id: str):
    response = get_attendance_service().get_registered_users(event_id)
    return jsonify(response.model_dump()), response.code

@attendance.route("/register/events/<event_id>", methods=["GET"])
@require_auth
@doc(
    response=RegisterEventResponse,
    description="Check self registration status for an event",
    tags=["attendance"],
    success_status=200,
)
def get_registration_status(event_id: str):
    response = get_attendance_service().get_registration_status(event_id, g.user_id)
    return jsonify(response.model_dump()), response.code


@attendance.route("/attend/events/<event_id>/users", methods=["GET"])
@require_auth
@doc(
    response=AttendanceRecordResponse,
    description="Retrieve all attended users for an event",
    tags=["attendance"],
    success_status=200,
)
def get_attended_users(event_id: str):
    response = get_attendance_service().get_attended_users(event_id)
    return jsonify(response.model_dump()), response.code

@attendance.route("/attend/events/<event_id>", methods=["GET"])
@require_auth
@doc(
    response=AttendEventResponse,
    description="Check self attendance status for an event",
    tags=["attendance"],
    success_status=200,
)
def get_attendance_status(event_id: str):
    response = get_attendance_service().get_attendance_status(event_id, g.user_id)
    return jsonify(response.model_dump()), response.code

@attendance.route("/register/events/<event_id>", methods=["POST"])
@require_auth
@doc(
    response=RegisterEventResponse,
    description="Register for an event",
    tags=["attendance"],
    success_status=201,
)
def register_event(event_id: str):
    response = get_attendance_service().register_event(event_id, g.user_id)
    return jsonify(response.model_dump()), response.code

@attendance.route("/register/events/<event_id>", methods=["DELETE"])
@require_auth
@doc(
    response=RegisterEventResponse,
    description="Unregister from an event",
    tags=["attendance"],
    success_status=200,
)
def unregister_event(event_id: str):
    response = get_attendance_service().unregister_event(event_id, g.user_id)
    return jsonify(response.model_dump()), response.code

@attendance.route("/attend/events/<event_id>/users/<user_id>", methods=["POST"])
@require_auth
@doc(
    response=AttendEventResponse,
    description="Organizer mark a user as attended",
    tags=["attendance"],
    success_status=200,
)
def attend_event(event_id: str, user_id: str):
    response = get_attendance_service().attend_event(event_id, user_id, g.user_id)
    return jsonify(response.model_dump()), response.code

@attendance.route("/attend/events/<event_id>/users/<user_id>", methods=["DELETE"])
@require_auth
@doc(
    response=AttendEventResponse,
    description="Organizer mark a user as not attended",
    tags=["attendance"],
    success_status=200,
)
def unattend_event(event_id: str, user_id: str):
    response = get_attendance_service().unattend_event(event_id, user_id, g.user_id)
    return jsonify(response.model_dump()), response.code


@attendance.route("/register", methods=["GET"])
@require_auth
@doc(
    response=ListEventsResponse,
    description="Retrieve all registered events for the user",
    tags=["attendance"],
    success_status=200,
)
def get_registered_events():
    response = get_attendance_service().get_registered_events(g.user_id)
    return jsonify(response.model_dump()), response.code

@attendance.route("/attend", methods=["GET"])
@require_auth
@doc(
    response=ListEventsResponse,
    description="Retrieve all attended events for the user",
    tags=["attendance"],
    success_status=200,
)
def get_attended_events():
    response = get_attendance_service().get_attended_events(g.user_id)
    return jsonify(response.model_dump()), response.code