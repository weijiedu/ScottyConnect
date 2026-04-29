"""
Routes for the feedback service.
"""

from flask import Blueprint, g, jsonify

from app.feedback.schemas import (
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStatusResponse,
    SubmitFeedbackRequest,
)
from app.feedback.service import get_feedback_service
from app.utils.auth import require_auth
from app.utils.doc import doc
from app.utils.validate import validate

feedback = Blueprint("feedback", __name__)


@feedback.route("/events/<event_id>/status", methods=["GET"])
@require_auth
@doc(
    response=FeedbackStatusResponse,
    description="Check whether feedback is open for an event and whether the current user is eligible",
    tags=["feedback"],
    success_status=200,
)
def get_feedback_status(event_id: str):
    response = get_feedback_service().get_feedback_status(event_id, g.user_id)
    return jsonify(response.model_dump(mode="json")), response.code


@feedback.route("/events/<event_id>", methods=["POST"])
@require_auth
@validate(SubmitFeedbackRequest)
@doc(
    request=SubmitFeedbackRequest,
    response=FeedbackResponse,
    description="Submit a rating and comment for an attended event",
    tags=["feedback"],
    success_status=201,
)
def submit_feedback(req: SubmitFeedbackRequest, event_id: str):
    response = get_feedback_service().submit_feedback(event_id, g.user_id, req)
    return jsonify(response.model_dump(mode="json")), response.code


@feedback.route("/events/<event_id>", methods=["GET"])
@require_auth
@doc(
    response=FeedbackListResponse,
    description="Retrieve all feedback for a given event",
    tags=["feedback"],
    success_status=200,
)
def get_feedbacks(event_id: str):
    response = get_feedback_service().get_feedbacks(event_id)
    return jsonify(response.model_dump(mode="json")), response.code


@feedback.route("/events/<event_id>/me", methods=["GET"])
@require_auth
@doc(
    response=FeedbackResponse,
    description="Retrieve the current user's own feedback for a specific event",
    tags=["feedback"],
    success_status=200,
)
def get_my_event_feedback(event_id: str):
    response = get_feedback_service().get_my_event_feedback(event_id, g.user_id)
    return jsonify(response.model_dump(mode="json")), response.code


@feedback.route("/me", methods=["GET"])
@require_auth
@doc(
    response=FeedbackListResponse,
    description="Retrieve the current user's full feedback history",
    tags=["feedback"],
    success_status=200,
)
def get_my_feedbacks():
    response = get_feedback_service().get_my_feedbacks(g.user_id)
    return jsonify(response.model_dump(mode="json")), response.code
