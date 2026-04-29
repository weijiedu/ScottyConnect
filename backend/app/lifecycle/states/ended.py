# Concrete state: Ended — event is complete, tasks are frozen for the record.

from app.lifecycle.states.base import EventState


class EndedState(EventState):

    @property
    def name(self) -> str:
        return "ended"
    
    def validate_edit_event(self, is_owner: bool) -> None:
        raise ValueError("Only draft events can be edited")

    def validate_delete_event(self, is_owner: bool) -> None:
        raise ValueError("Only draft events can be deleted")

    def validate_view_tasks(self, is_owner: bool) -> None:
        pass
