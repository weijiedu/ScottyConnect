# backend/app/lifecycle/routes.py
"""
Routes for the lifecycle service.
"""
from flask import Blueprint, jsonify, g, request

from app.lifecycle.schemas import (
    CreateEventRequest,
    EventListResponse,
    EventResponse,
    SyncExpiredResponse,
    TransitionRequest,
    UpdateEventRequest,
)
from app.lifecycle.service import get_lifecycle_service
from app.utils.auth import require_auth, try_get_request_user_id
from app.utils.doc import doc
from app.utils.validate import validate

lifecycle = Blueprint("lifecycle", __name__)


@lifecycle.route("/events", methods=["POST"])
@require_auth
@validate(CreateEventRequest)
@doc(
    request=CreateEventRequest,
    response=EventResponse,
    description="Create a new event as draft or published",
    tags=["lifecycle"],
    success_status=201,
)
def create_event(req: CreateEventRequest):
    resp = get_lifecycle_service().create_event(req, g.user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code


@lifecycle.route("/events/mine", methods=["GET"])
@require_auth
@doc(
    response=EventListResponse,
    description="List events created by the authenticated user",
    tags=["lifecycle"],
    success_status=200,
)
def list_my_events():
    client_tz = request.args.get("client_tz")
    resp = get_lifecycle_service().list_mine(g.user_id, client_tz=client_tz)
    return jsonify(resp.model_dump(mode="json")), resp.code


@lifecycle.route("/events/published", methods=["GET"])
@doc(
    response=EventListResponse,
    description="List published events for the public feed",
    tags=["lifecycle"],
    success_status=200,
)
def list_published_events():
    client_tz = request.args.get("client_tz")
    resp = get_lifecycle_service().list_published(client_tz=client_tz)
    return jsonify(resp.model_dump(mode="json")), resp.code


@lifecycle.route("/events/sync-expired", methods=["POST"])
@doc(
    response=SyncExpiredResponse,
    description="Sync expired published events to ended (idempotent)",
    tags=["lifecycle"],
    success_status=200,
)
def sync_expired_events():
    client_tz = request.args.get("client_tz")
    ended_count, scanned_count = get_lifecycle_service().sync_all_expired_published_events(
        client_tz=client_tz
    )
    payload = SyncExpiredResponse(scanned=scanned_count, ended=ended_count)
    return jsonify(payload.model_dump(mode="json")), 200


@lifecycle.route("/events/<event_id>", methods=["GET"])
@doc(
    response=EventResponse,
    description="Get a single event by ID",
    tags=["lifecycle"],
    success_status=200,
)
def get_event(event_id: str):
    requester_id = try_get_request_user_id()
    client_tz = request.args.get("client_tz")
    resp = get_lifecycle_service().get_event(
        event_id, requester_id=requester_id, client_tz=client_tz
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@lifecycle.route("/events/<event_id>", methods=["PUT"])
@require_auth
@validate(UpdateEventRequest)
@doc(
    request=UpdateEventRequest,
    response=EventResponse,
    description="Update a draft event",
    tags=["lifecycle"],
    success_status=200,
)
def update_event(req: UpdateEventRequest, event_id: str):
    resp = get_lifecycle_service().update_event(event_id, req, g.user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code


@lifecycle.route("/events/<event_id>", methods=["DELETE"])
@require_auth
@doc(
    response=EventResponse,
    description="Delete a draft event",
    tags=["lifecycle"],
    success_status=200,
)
def delete_event(event_id: str):
    resp = get_lifecycle_service().delete_event(event_id, g.user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code


@lifecycle.route("/events/<event_id>/transition", methods=["POST"])
@require_auth
@validate(TransitionRequest)
@doc(
    request=TransitionRequest,
    response=EventResponse,
    description="Transition an event to a new lifecycle state",
    tags=["lifecycle"],
    success_status=200,
)
def transition_event(req: TransitionRequest, event_id: str):
    resp = get_lifecycle_service().transition(event_id, req.target_status, g.user_id)
    return jsonify(resp.model_dump(mode="json")), resp.code
