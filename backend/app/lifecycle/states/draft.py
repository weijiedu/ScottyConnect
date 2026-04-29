# Concrete state: Draft — event is being planned privately by the owner.

from app.lifecycle.states.base import EventState


class DraftState(EventState):

    @property
    def name(self) -> str:
        return "draft"

    def allowed_transitions(self) -> list[str]:
        return ["published"]

    def validate_edit_event(self, is_owner: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can update this event")

    def validate_delete_event(self, is_owner: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can delete this event")

    def validate_create_task(self, is_owner: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can create tasks in 'draft' state")

    def validate_edit_task(self, is_owner: bool, is_claimed: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can edit tasks in 'draft' state")

    def validate_delete_task(self, is_owner: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can delete tasks in 'draft' state")

    def validate_view_tasks(self, is_owner: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can view tasks in 'draft' state")
