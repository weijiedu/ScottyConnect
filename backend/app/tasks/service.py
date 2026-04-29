from __future__ import annotations

from dataclasses import dataclass

from bson.errors import InvalidId

from app.lifecycle.lifecycle_dao import LifecycleDAO
from app.lifecycle.states import resolve_state
from app.tasks.composite import TaskComponent, build_task_tree
from app.tasks.model.Task import Task
from app.tasks.schemas import TaskNode, TaskResponse, TaskTreeResponse
from app.tasks.task_dao import TaskDAO
from app.bus.message import Message, MessageType
from app.bus.message_bus import Service
from app.accounts.user_dao import UserDAO as UserAccountDAO

TASKS_SERVICE_EXTENSION_KEY = "tasks_service"


def get_tasks_service() -> "TasksService":
    from flask import current_app

    return current_app.extensions[TASKS_SERVICE_EXTENSION_KEY]


# Lightweight event info used for permission checks.
@dataclass
class EventContext:
    owner_id: str
    status: str


class TasksService(Service):
    def __init__(
        self,
        task_dao: TaskDAO | None = None,
        lifecycle_dao: LifecycleDAO | None = None,
        user_dao: UserAccountDAO | None = None,
    ) -> None:
        super().__init__()
        self.key = TASKS_SERVICE_EXTENSION_KEY
        self._dao = task_dao or TaskDAO()
        self._lifecycle_dao = lifecycle_dao or LifecycleDAO()
        self.subscribeToMessages([MessageType.LIFECYCLE_MESSAGE])
        self._user_dao = user_dao or UserAccountDAO()


    # Message bus handler
    def processMessage(self, message: Message) -> None:
        data = message.get_data()
        new_status = data.get("new_status")
        event_id = data.get("event_id")
        if not event_id or not new_status:
            return
        if new_status == "ended":
            self._dao.bulk_update_status_for_event(
                event_id, "closed", skip_completed=True
            )
        elif new_status == "cancelled":
            self._dao.bulk_update_status_for_event(event_id, "unavailable")

    # Helpers
    def _resolve_event(
        self,
        event_id: str,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> tuple[EventContext | None, TaskResponse | None]:
        # Try MongoDB first
        # fall back to client-supplied context for localStorage-only events whose IDs are not valid ObjectIds.
        try:
            event = self._lifecycle_dao.find_by_id(event_id)

            if event is not None:
                return EventContext(owner_id=event.owner_id, status=event.status), None
        except (InvalidId, Exception):
            pass

        if fallback_owner_id and fallback_status:
            return EventContext(owner_id=fallback_owner_id, status=fallback_status), None

        return None, TaskResponse(message="Event not found", code=404)

    @staticmethod
    def _find_component(roots: list[TaskComponent], task_id: str) -> TaskComponent | None:
        # traverse the composite tree to locate the node with task_id
        for root in roots:
            if root.task.id == task_id:
                return root

            if root.is_composite():
                found = TasksService._find_component(root.children, task_id)

                if found:
                    return found

        return None

    def _get_username(self, user_id: str) -> str | None:

        user = self._user_dao.find_by_id(user_id)
        if user:
            return user.username
        else:
            return None

    def _node_from_dict(self, d: dict) -> TaskNode:
        assigned_to = d.get("assigned_to")
        
        if assigned_to:
            assigned_to_username = self._get_username(assigned_to)
        else:
            assigned_to_username = None

        return TaskNode(
            id = d.get("id"),
            event_id = d["event_id"],
            parent_id = d.get("parent_id"),
            title = d["title"],
            description = d.get("description", ""),
            status = d["status"],
            assigned_to = assigned_to,
            assigned_to_username = assigned_to_username,
            contribution = d.get("contribution"),
            created_by = d["created_by"],
            progress = d.get("progress", 0),
            children = [self._node_from_dict(c) for c in d.get("children", [])],
            created_at = str(d.get("created_at", "")),
            updated_at = str(d.get("updated_at", "")),
        )


    # Public API
    def create_task(
        self,
        event_id: str,
        title: str,
        description: str,
        parent_id: str | None,
        user_id: str,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> TaskResponse:
        ctx, err = self._resolve_event(event_id, fallback_owner_id, fallback_status)
        if err:
            return err

        is_owner = ctx.owner_id == user_id
        state = resolve_state(ctx.status)

        try:
            state.validate_create_task(is_owner)
        except ValueError as e:
            return TaskResponse(message=str(e), code=403)

        if parent_id:
            parent = self._dao.find_by_id(parent_id)
            if parent is None or parent.event_id != event_id:
                return TaskResponse(message="Parent task not found in this event", code=404)

        task = Task(
            event_id=event_id,
            parent_id=parent_id,
            title=title,
            description=description,
            created_by=user_id,
        )
        saved = self._dao.insert(task)

        tree = build_task_tree([saved])
        
        if tree:
            node = self._node_from_dict(tree[0].to_dict())
        else:
            node = None

        return TaskResponse(message="Task created", task=node, code=201)

    def get_task_tree(
        self,
        event_id: str,
        user_id: str,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> TaskTreeResponse:
        ctx, err = self._resolve_event(event_id, fallback_owner_id, fallback_status)
        if err:
            return TaskTreeResponse(message=err.message, tasks=[], code=err.code)

        is_owner = ctx.owner_id == user_id
        state = resolve_state(ctx.status)
        try:
            state.validate_view_tasks(is_owner)
        except ValueError as e:
            return TaskTreeResponse(message=str(e), tasks=[], code=403)

        tasks = self._dao.find_by_event(event_id)
        roots = build_task_tree(tasks)
        nodes = [self._node_from_dict(r.to_dict()) for r in roots]
        # Use composite count_tasks() to compute the total across all root subtrees.
        total = sum(r.count_tasks() for r in roots)

        return TaskTreeResponse(message="Success", tasks=nodes, total_tasks=total, code=200)

    def update_task(
        self,
        task_id: str,
        user_id: str,
        title: str | None = None,
        description: str | None = None,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> TaskResponse:
        task = self._dao.find_by_id(task_id)

        if task is None:
            return TaskResponse(message="Task not found", code=404)

        ctx, err = self._resolve_event(task.event_id, fallback_owner_id, fallback_status)

        if err:
            return err

        is_owner = ctx.owner_id == user_id
        is_claimed = task.assigned_to is not None
        state = resolve_state(ctx.status)

        try:
            state.validate_edit_task(is_owner, is_claimed)
        except ValueError as e:
            return TaskResponse(message=str(e), code=403)

        updates: dict = {}

        if title is not None:
            updates["title"] = title

        if description is not None:
            updates["description"] = description

        if not updates:
            return TaskResponse(message="No fields to update", code=400)

        updated = self._dao.update(task_id, updates)
        tree = build_task_tree([updated])

        if tree:
            node = self._node_from_dict(tree[0].to_dict())
        else:
            node = None

        return TaskResponse(message="Task updated", task=node, code=200)

    def delete_task(
        self,
        task_id: str,
        user_id: str,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> TaskResponse:
        task = self._dao.find_by_id(task_id)

        if task is None:
            return TaskResponse(message="Task not found", code=404)

        ctx, err = self._resolve_event(task.event_id, fallback_owner_id, fallback_status)
        if err:
            return err

        is_owner = ctx.owner_id == user_id
        state = resolve_state(ctx.status)

        try:
            state.validate_delete_task(is_owner)
        except ValueError as e:
            return TaskResponse(message=str(e), code=403)

        # Use composite collect_ids() to find all descendant IDs in one traversal, then bulk-delete them
        all_tasks = self._dao.find_by_event(task.event_id)
        roots = build_task_tree(all_tasks)
        target = self._find_component(roots, task_id)

        if target:
            for tid in target.collect_ids():
                self._dao.delete(tid)
        else:
            self._dao.delete(task_id)

        return TaskResponse(message="Task deleted", code=200)

    def claim_task(
        self,
        task_id: str,
        user_id: str,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> TaskResponse:

        task = self._dao.find_by_id(task_id)

        if task is None:
            return TaskResponse(message="Task not found", code=404)

        ctx, err = self._resolve_event(task.event_id, fallback_owner_id, fallback_status)

        if err:
            return err

        state = resolve_state(ctx.status)

        try:
            state.validate_claim_task()
        except ValueError as e:
            return TaskResponse(message=str(e), code=403)

        if task.assigned_to is not None:
            return TaskResponse(message="Task is already claimed", code=409)

        # Use composite is_composite() to decide claimability, only leaf nodes can be claimed.
        all_tasks = self._dao.find_by_event(task.event_id)
        roots = build_task_tree(all_tasks)
        target = self._find_component(roots, task_id)

        if target and target.is_composite():
            return TaskResponse(message="Cannot claim a parent task — claim its sub-tasks instead", code=400)

        updated = self._dao.update(task_id, {"assigned_to": user_id, "status": "claimed"})
        tree = build_task_tree([updated])

        if tree:
            node = self._node_from_dict(tree[0].to_dict())
        else:
            node = None

        return TaskResponse(message="Task claimed", task=node, code=200)

    def contribute(
        self,
        task_id: str,
        user_id: str,
        contribution: str,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> TaskResponse:
        task = self._dao.find_by_id(task_id)

        if task is None:
            return TaskResponse(message="Task not found", code=404)

        ctx, err = self._resolve_event(task.event_id, fallback_owner_id, fallback_status)

        if err:
            return err

        state = resolve_state(ctx.status)

        try:
            state.validate_contribute()
        except ValueError as e:
            return TaskResponse(message=str(e), code=403)

        if task.assigned_to != user_id:
            return TaskResponse(message="Only the assigned user can contribute", code=403)

        if task.status != "claimed":
            return TaskResponse(message="Task must be claimed before contributing", code=400)

        updated = self._dao.update(
            task_id, {"status": "completed", "contribution": contribution}
        )

        tree = build_task_tree([updated])
        node = self._node_from_dict(tree[0].to_dict()) if tree else None

        return TaskResponse(message="Contribution submitted", task=node, code=200)

    def unclaim_task(
        self,
        task_id: str,
        user_id: str,
        fallback_owner_id: str | None = None,
        fallback_status: str | None = None,
    ) -> TaskResponse:
        task = self._dao.find_by_id(task_id)

        if task is None:
            return TaskResponse(message="Task not found", code=404)

        ctx, err = self._resolve_event(task.event_id, fallback_owner_id, fallback_status)

        if err:
            return err

        is_owner = ctx.owner_id == user_id

        if task.assigned_to != user_id and not is_owner:
            return TaskResponse(message="Only the claimant or event owner can unclaim this task", code=403)

        if task.status != "claimed":
            return TaskResponse(message="Task is not claimed", code=400)

        updated = self._dao.update(task_id, {"assigned_to": None, "status": "open"})
        tree = build_task_tree([updated])

        if tree:
            node = self._node_from_dict(tree[0].to_dict())
        else:
            node = None

        return TaskResponse(message="Task unclaimed", task=node, code=200)
