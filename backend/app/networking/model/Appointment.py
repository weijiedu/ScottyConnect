"""
Appointment Model
Defines the structure and lifecycle of a coffee chat appointment.
"""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator



# Possible statuses for a coffee chat invitation.
class AppointmentStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


# Domain model for a coffee chat appointment.
class Appointment(BaseModel):
    id: str | None = None
    sender_id: str
    receiver_id: str
    sender_role: str | None = None
    receiver_role: str | None = None
    scheduled_at: datetime
    status: AppointmentStatus = AppointmentStatus.PENDING
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    @field_validator("scheduled_at", mode="before")
    @classmethod
    def ensure_aware(cls, v):
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace(' ', 'T'))
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


    # Validates appointment status transitions.
    def can_transition(self, new_status: AppointmentStatus) -> bool:
        allowed = {
            AppointmentStatus.PENDING: {
                AppointmentStatus.ACCEPTED,
                AppointmentStatus.DECLINED,
                AppointmentStatus.CANCELLED,
            },
            AppointmentStatus.ACCEPTED: {
                AppointmentStatus.CANCELLED,
            },
            AppointmentStatus.DECLINED: set(),
            AppointmentStatus.CANCELLED: set(),
        }
        return new_status in allowed.get(self.status, set())

    # Returns a copied Appointment with a validated new status.
    def transition_to(self, new_status: AppointmentStatus) -> "Appointment":
        if not self.can_transition(new_status):
            raise ValueError(f"Invalid transition: {self.status} -> {new_status}")
        return self.model_copy(
            update={"status": new_status, "updated_at": datetime.now(timezone.utc)}
        )
