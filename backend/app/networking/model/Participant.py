"""
Participant Model
Defines the Colleagues in the Mediator pattern (Student and Alumni).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Protocol, Tuple, Optional

from pydantic import BaseModel


# Mediator interface to avoid circular dependencies.
class ICoffeeChatMediator(Protocol):
    def dispatch_invite(
        self,
        sender: 'Participant',
        receiver_id: str,
        scheduled_at: datetime,
        receiver_role: str,
    ) -> Tuple[bool, Optional[str]]:
        ...
    def finalize_invite_response(self, responder: 'Participant', invite_id: str, accept: bool) -> Tuple[bool, Optional[str]]:
        ...
    def validate_availability(self, user_id: str, scheduled_at: datetime) -> bool:
        ...
    def dispatch_cancellation(self, canceller: 'Participant', invite_id: str) -> bool:
        ...


# Abstract base class for all coffee chat participants.
class Participant(BaseModel, ABC):
    user_id: str
    username: str
    
    # Injected mediator (private attribute to avoid Pydantic validation issues)
    _mediator: ICoffeeChatMediator | None = None
    
    # Inject the mediator instance.
    def set_mediator(self, mediator: ICoffeeChatMediator):
        self._mediator = mediator

    # Return the participant's specific role.
    @abstractmethod
    def get_role(self) -> str:
        pass

    # Delegate invitation sending to the mediator.
    def initiate_chat(self, receiver_id: str, scheduled_at: datetime, receiver_role: str) -> Tuple[bool, Optional[str]]:
        if self._mediator:
            return self._mediator.dispatch_invite(self, receiver_id, scheduled_at, receiver_role)
        return False, "Mediator not configured"

    # Delegate invitation acceptance to the mediator.
    def accept_chat(self, invite_id: str) -> Tuple[bool, Optional[str]]:
        if self._mediator:
            return self._mediator.finalize_invite_response(self, invite_id, accept=True)
        return False, "Mediator not configured"

    # Delegate invitation declination to the mediator.
    def decline_chat(self, invite_id: str) -> Tuple[bool, Optional[str]]:
        if self._mediator:
            return self._mediator.finalize_invite_response(self, invite_id, accept=False)
        return False, "Mediator not configured"

    # Delegate invitation cancellation to the mediator.
    def cancel_chat(self, invite_id: str) -> bool:
        if self._mediator:
            return self._mediator.dispatch_cancellation(self, invite_id)
        return False

# Concrete Participant representing a Student.
class StudentAttendee(Participant):
    def get_role(self) -> str:
        return "STUDENT"


# Concrete Participant representing an Alumni.
class AlumniAttendee(Participant):
    def get_role(self) -> str:
        return "ALUMNI"


# Factory to create participants based on system roles.
class ParticipantFactory:
    
    _ROLE_MAP = {
        "STUDENT": StudentAttendee,
        "ALUMNI": AlumniAttendee
    }

    # Creates the appropriate Participant subclass for a given role.
    @staticmethod
    def create(user_id: str, username: str, role: str) -> Participant:
        cls = ParticipantFactory._ROLE_MAP.get(role)
        if cls is None:
            raise ValueError(f"Invalid role: {role}. Supported roles: {list(ParticipantFactory._ROLE_MAP.keys())}")
        return cls(user_id=user_id, username=username)
