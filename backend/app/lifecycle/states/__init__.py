# State registry — maps stored status strings to runtime EventState objects.

from app.lifecycle.states.base import EventState
from app.lifecycle.states.draft import DraftState
from app.lifecycle.states.published import PublishedState
from app.lifecycle.states.ended import EndedState
from app.lifecycle.states.cancelled import CancelledState

_STATE_REGISTRY: dict[str, EventState] = {
    "draft": DraftState(),
    "published": PublishedState(),
    "ended": EndedState(),
    "cancelled": CancelledState(),
}


def resolve_state(status: str) -> EventState:
    """Return the EventState instance for a given status string, or raise."""
    state = _STATE_REGISTRY.get(status)
    if state is None:
        raise ValueError(f"Unknown event status: '{status}'")
    return state
