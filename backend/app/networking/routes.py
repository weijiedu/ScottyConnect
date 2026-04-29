"""
Networking Routes
API endpoints for the 1-on-1 coffee chat and matchmaking feature.
"""

from flask import Blueprint, g, jsonify

from app.networking.schemas import (
    AppointmentListResponse,
    AppointmentResponse,
    BusySlotsResponse,
    CancelRequest,
    InviteRequest,
    RespondRequest,
)
from app.networking.service import get_networking_service
from app.utils.auth import require_auth
from app.utils.doc import doc
from app.utils.validate import validate

networking = Blueprint("networking", __name__)


# Endpoint to initiate a coffee chat request.
@networking.route("/invite", methods=["POST"])
@require_auth
@validate(InviteRequest)
@doc(
    request=InviteRequest,
    response=AppointmentResponse,
    description="Send a 1-on-1 coffee chat invitation",
    tags=["networking"],
    success_status=201,
)
def send_invite(req: InviteRequest):
    service = get_networking_service()
    resp = service.request_invite(req, sender_id=g.user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code


# Endpoint to accept or decline a pending invitation.
@networking.route("/respond", methods=["POST"])
@require_auth
@validate(RespondRequest)
@doc(
    request=RespondRequest,
    response=AppointmentResponse,
    description="Respond (Accept/Decline) to a coffee chat invitation",
    tags=["networking"],
    success_status=200,
)
def respond_invite(req: RespondRequest):
    service = get_networking_service()
    resp = service.process_invite_response(req, responder_id=g.user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code


# Endpoint to cancel a pending invitation sent by the user.
@networking.route("/cancel", methods=["POST"])
@require_auth
@validate(CancelRequest)
@doc(
    request=CancelRequest,
    response=AppointmentResponse,
    description="Cancel a sent coffee chat invitation",
    tags=["networking"],
    success_status=200,
)
def cancel_invite(req: CancelRequest):
    service = get_networking_service()
    resp = service.cancel_invite(req.invite_id, g.user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code


# Endpoint to retrieve the appointment history for a user.
@networking.route("/appointments/<user_id>", methods=["GET"])
@require_auth
@doc(
    response=AppointmentListResponse,
    description="Get all coffee chat appointments for a user",
    tags=["networking"],
    success_status=200,
)
def get_appointments(user_id: str):
    if user_id != g.user_id:
        return jsonify({"message": "Unauthorized to view appointments"}), 403
        
    service = get_networking_service()
    data = service.get_appointments(user_id)
    
    # Standardize response using schema
    resp = AppointmentListResponse(appointments=data, code=200)
    return jsonify(resp.model_dump(mode="json")), 200



# Endpoint to retrieve a user's busy slots for conflict prevention.
@networking.route("/busy-slots/<user_id>", methods=["GET"])
@require_auth
@doc(
    response=BusySlotsResponse,
    description="Get all occupied timeslots for a user",
    tags=["networking"],
    success_status=200,
)
def get_busy_slots(user_id: str):
    service = get_networking_service()
    resp = service.get_busy_slots(user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code
