# Concrete state: Published — event is live, participants can interact with tasks.

from app.lifecycle.states.base import EventState


class PublishedState(EventState):

    @property
    def name(self) -> str:
        return "published"

    def allowed_transitions(self) -> list[str]:
        return ["ended", "cancelled"]

    def validate_edit_event(self, is_owner: bool) -> None:
        raise ValueError("Only draft events can be edited")

    def validate_delete_event(self, is_owner: bool) -> None:
        raise ValueError("Only draft events can be deleted")

    def validate_create_task(self, is_owner: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can create tasks in 'draft' or 'published' state")

    def validate_edit_task(self, is_owner: bool, is_claimed: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can edit tasks in 'published' state")
        if is_claimed:
            raise ValueError("Cannot edit a task that has already been claimed")

    def validate_delete_task(self, is_owner: bool) -> None:
        if not is_owner:
            raise ValueError("Only the event owner can delete tasks in 'published' state")

    def validate_view_tasks(self, is_owner: bool) -> None:
        pass

    def validate_claim_task(self) -> None:
        pass

    def validate_contribute(self) -> None:
        pass
