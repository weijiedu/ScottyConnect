from flask import Blueprint, jsonify, request, g

from app.tasks.schemas import (
    CreateTaskRequest,
    UpdateTaskRequest,
    ContributeRequest,
    TaskResponse,
    TaskTreeResponse,
)
from app.tasks.service import get_tasks_service
from app.utils.doc import doc
from app.utils.validate import validate
from app.utils.auth import require_auth

tasks = Blueprint("tasks", __name__)


def _event_ctx() -> dict:
    # Extract optional event-context headers for events that live only in localStorage
    return {
        "fallback_owner_id": request.headers.get("X-Event-Owner-Id"),
        "fallback_status": request.headers.get("X-Event-Status"),
    }


@tasks.route("/events/<event_id>", methods=["POST"])
@require_auth
@validate(CreateTaskRequest)
@doc(
    request=CreateTaskRequest,
    response=TaskResponse,
    description="Create a new task (or sub-task) for an event",
    tags=["tasks"],
    success_status=201,
)
def create_task(req: CreateTaskRequest, event_id: str):
    resp = get_tasks_service().create_task(
        event_id, req.title, req.description, req.parent_id, g.user_id, **_event_ctx()
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@tasks.route("/events/<event_id>", methods=["GET"])
@require_auth
@doc(
    response=TaskTreeResponse,
    description="Get the full task tree for an event",
    tags=["tasks"],
    success_status=200,
)
def get_task_tree(event_id: str):
    resp = get_tasks_service().get_task_tree(event_id, g.user_id, **_event_ctx())
    return jsonify(resp.model_dump(mode="json")), resp.code


@tasks.route("/<task_id>", methods=["PUT"])
@require_auth
@validate(UpdateTaskRequest)
@doc(
    request=UpdateTaskRequest,
    response=TaskResponse,
    description="Update a task's title or description",
    tags=["tasks"],
    success_status=200,
)
def update_task(req: UpdateTaskRequest, task_id: str):
    resp = get_tasks_service().update_task(
        task_id, g.user_id, req.title, req.description, **_event_ctx()
    )
    return jsonify(resp.model_dump(mode="json")), resp.code


@tasks.route("/<task_id>", methods=["DELETE"])
@require_auth
@doc(
    response=TaskResponse,
    description="Delete a task and all its sub-tasks",
    tags=["tasks"],
    success_status=200,
)
def delete_task(task_id: str):
    resp = get_tasks_service().delete_task(task_id, g.user_id, **_event_ctx())
    return jsonify(resp.model_dump(mode="json")), resp.code


@tasks.route("/<task_id>/claim", methods=["POST"])
@require_auth
@doc(
    response=TaskResponse,
    description="Claim an open task",
    tags=["tasks"],
    success_status=200,
)
def claim_task(task_id: str):
    resp = get_tasks_service().claim_task(task_id, g.user_id, **_event_ctx())
    return jsonify(resp.model_dump(mode="json")), resp.code


@tasks.route("/<task_id>/claim", methods=["DELETE"])
@require_auth
@doc(
    response=TaskResponse,
    description="Unclaim a claimed task (by the claimant or event owner)",
    tags=["tasks"],
    success_status=200,
)
def unclaim_task(task_id: str):
    resp = get_tasks_service().unclaim_task(task_id, g.user_id, **_event_ctx())
    return jsonify(resp.model_dump(mode="json")), resp.code


@tasks.route("/<task_id>/contribute", methods=["POST"])
@require_auth
@validate(ContributeRequest)
@doc(
    request=ContributeRequest,
    response=TaskResponse,
    description="Submit a contribution for a claimed task",
    tags=["tasks"],
    success_status=200,
)
def contribute_task(req: ContributeRequest, task_id: str):
    resp = get_tasks_service().contribute(
        task_id, g.user_id, req.contribution, **_event_ctx()
    )
    return jsonify(resp.model_dump(mode="json")), resp.code
