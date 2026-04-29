"""
Routes for the recommendation service.
"""

from flask import Blueprint, jsonify, request

from app.recommendation.schemas import (
    EventTagsBody,
    EventTagsResponse,
    RecommendationResponse,
    TagItem,
    TagListResponse,
    UserPreferenceBody,
    UserPreferenceResponse,
    UserTagsBody,
    UserTagsResponse,
)
from app.recommendation.service import DEFAULT_STRATEGY, get_recommendation_service
from app.utils.doc import doc

recommendation = Blueprint("recommendation", __name__)


# Decorator order convention: @route -> @doc
@recommendation.route("/<user_id>", methods=["GET"])
@doc(
    response=RecommendationResponse,
    description="Get recommended published events for a user, ranked by strategy with remaining published events appended",
    tags=["recommendation"],
    success_status=200,
)
def get_recommendation(user_id: str):
    strategy = request.args.get("strategy", "").strip()
    if not strategy:
        return jsonify({"message": "'strategy' query parameter is required"}), 400

    resp = get_recommendation_service().get_recommendation(user_id, strategy)
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/preferences/<user_id>", methods=["GET"])
@doc(
    response=UserPreferenceResponse,
    description="Get a user's saved recommendation strategy preference (returns the default if none is stored)",
    tags=["recommendation"],
    success_status=200,
)
def get_preference(user_id: str):
    pref = get_recommendation_service().get_user_preference(user_id)
    preferred = pref.preferred_strategy if pref is not None else DEFAULT_STRATEGY
    resp = UserPreferenceResponse(
        message="Success",
        user_id=user_id,
        preferred_strategy=preferred,
        code=200,
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/preferences/<user_id>", methods=["POST"])
@doc(
    request=UserPreferenceBody,
    response=UserPreferenceResponse,
    description="Save a user's preferred recommendation strategy",
    tags=["recommendation"],
    success_status=200,
)
def set_preference(user_id: str):
    body = request.get_json(silent=True) or {}
    strategy = (body.get("preferred_strategy") or "").strip()
    if not strategy:
        return jsonify({"message": "'preferred_strategy' is required"}), 400

    pref = get_recommendation_service().set_user_preference(user_id, strategy)
    if pref is None:
        return jsonify({"message": "Invalid strategy or user_id"}), 400

    resp = UserPreferenceResponse(
        message="Success",
        user_id=pref.user_id,
        preferred_strategy=pref.preferred_strategy,
        code=200,
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/tags", methods=["GET"])
@doc(
    response=TagListResponse,
    description="List every selectable tag.",
    tags=["recommendation"],
    success_status=200,
)
def list_tags():
    tags = get_recommendation_service().list_all_tags()
    items = [
        TagItem(id=t.id or "", slug=t.slug, display_name=t.display_name)
        for t in tags
        if t.id is not None
    ]
    resp = TagListResponse(message="Success", tags=items, code=200)
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/user-tags/<user_id>", methods=["GET"])
@doc(
    response=UserTagsResponse,
    description="Get the tags a user has marked themselves as interested in.",
    tags=["recommendation"],
    success_status=200,
)
def get_user_tags(user_id: str):
    tag_ids = get_recommendation_service().get_user_tag_ids(user_id)
    if tag_ids is None:
        return jsonify({"message": "Invalid user_id"}), 400
    resp = UserTagsResponse(
        message="Success", user_id=user_id, tag_ids=tag_ids, code=200
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/user-tags/<user_id>", methods=["POST"])
@doc(
    request=UserTagsBody,
    response=UserTagsResponse,
    description="Replace a user's interested-tag set with the supplied list.",
    tags=["recommendation"],
    success_status=200,
)
def set_user_tags(user_id: str):
    body = request.get_json(silent=True) or {}
    raw_tag_ids = body.get("tag_ids")
    if not isinstance(raw_tag_ids, list):
        return jsonify({"message": "'tag_ids' must be a list of strings"}), 400

    tag_ids_in: list[str] = [str(t) for t in raw_tag_ids]
    saved = get_recommendation_service().set_user_tags(user_id, tag_ids_in)
    if saved is None:
        return jsonify({"message": "Invalid user_id"}), 400

    resp = UserTagsResponse(
        message="Success", user_id=user_id, tag_ids=saved, code=200
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/event-tags/<event_id>", methods=["GET"])
@doc(
    response=EventTagsResponse,
    description="Get the tags associated with an event.",
    tags=["recommendation"],
    success_status=200,
)
def get_event_tags(event_id: str):
    tag_ids = get_recommendation_service().get_event_tag_ids(event_id)
    if tag_ids is None:
        return jsonify({"message": "Invalid event_id"}), 400
    resp = EventTagsResponse(
        message="Success", event_id=event_id, tag_ids=tag_ids, code=200
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/event-tags/<event_id>", methods=["POST"])
@doc(
    request=EventTagsBody,
    response=EventTagsResponse,
    description="Replace an event's tag set with the supplied list.",
    tags=["recommendation"],
    success_status=200,
)
def set_event_tags(event_id: str):
    body = request.get_json(silent=True) or {}
    raw_tag_ids = body.get("tag_ids")
    if not isinstance(raw_tag_ids, list):
        return jsonify({"message": "'tag_ids' must be a list of strings"}), 400

    tag_ids_in: list[str] = [str(t) for t in raw_tag_ids]
    saved = get_recommendation_service().set_event_tags(event_id, tag_ids_in)
    if saved is None:
        return jsonify({"message": "Invalid event_id"}), 400

    resp = EventTagsResponse(
        message="Success", event_id=event_id, tag_ids=saved, code=200
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@recommendation.route("/event-tags/<event_id>", methods=["DELETE"])
@doc(
    response=EventTagsResponse,
    description="Delete all tags for an event.",
    tags=["recommendation"],
    success_status=200,
)
def delete_event_tags(event_id: str):
    count = get_recommendation_service().delete_event_tags(event_id)
    if count is None:
        return jsonify({"message": "Invalid event_id"}), 400

    resp = EventTagsResponse(
        message="Success", event_id=event_id, tag_ids=[], code=200
    )
    return jsonify(resp.model_dump(mode="json")), resp.code
