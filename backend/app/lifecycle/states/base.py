# Abstract base class for event lifecycle states (State Pattern).

from abc import ABC, abstractmethod


class EventState(ABC):
    """Each concrete state defines what transitions and task operations it permits."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the status string stored in the Event document (e.g. "draft")."""

    def allowed_transitions(self) -> list[str]:
        """Status strings this state can transition to. Empty by default (terminal)."""
        return []

    def handle_transition(self, target_status: str) -> str:
        """Validate and return *target_status*, or raise if the transition is illegal."""
        allowed = self.allowed_transitions()
        if target_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{self.name}' to '{target_status}'. "
                f"Allowed transitions: {allowed if allowed else 'none (terminal state)'}"
            )
        return target_status


    # Event-level permissions — default-deny
    # Concrete states override only the operations they explicitly allow.
    # If a state does not override a method, the operation is denied.

    def validate_edit_event(self, is_owner: bool) -> None:
        raise ValueError(f"Editing event is not allowed in '{self.name}' state")

    def validate_delete_event(self, is_owner: bool) -> None:
        raise ValueError(f"Deleting event is not allowed in '{self.name}' state")

    # Task-coordination permissions — default-deny
    # Concrete states override only the operations they explicitly allow.
    # If a state does not override a method, the operation is denied.

    def validate_create_task(self, is_owner: bool) -> None:
        raise ValueError(f"Creating tasks is not allowed in '{self.name}' state")

    def validate_edit_task(self, is_owner: bool, is_claimed: bool) -> None:
        raise ValueError(f"Editing tasks is not allowed in '{self.name}' state")

    def validate_delete_task(self, is_owner: bool) -> None:
        raise ValueError(f"Deleting tasks is not allowed in '{self.name}' state")

    def validate_view_tasks(self, is_owner: bool) -> None:
        raise ValueError(f"Viewing tasks is not allowed in '{self.name}' state")

    def validate_claim_task(self) -> None:
        raise ValueError(f"Claiming tasks is not allowed in '{self.name}' state")

    def validate_contribute(self) -> None:
        raise ValueError(f"Contributing is not allowed in '{self.name}' state")
