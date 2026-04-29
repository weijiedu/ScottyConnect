# Concrete state: Cancelled — event was abandoned, tasks are frozen for transparency.

from app.lifecycle.states.base import EventState


class CancelledState(EventState):

    @property
    def name(self) -> str:
        return "cancelled"

    def validate_edit_event(self, is_owner: bool) -> None:
        raise ValueError("Only draft events can be edited")

    def validate_delete_event(self, is_owner: bool) -> None:
        raise ValueError("Only draft events can be deleted")

    def validate_view_tasks(self, is_owner: bool) -> None:
        pass
