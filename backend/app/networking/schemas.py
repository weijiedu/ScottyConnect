"""
Networking Schemas
Pydantic models for networking request validation and API responses.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# Schema for sending a coffee chat invitation.
class InviteRequest(BaseModel):
    receiver_id: str
    scheduled_at: datetime


# Schema for responding to a coffee chat invitation.
class RespondRequest(BaseModel):
    invite_id: str
    accept: bool


# Schema for cancelling a coffee chat invitation.
class CancelRequest(BaseModel):
    invite_id: str


# Standardized response for appointment-related operations.
class AppointmentResponse(BaseModel):
    message: str
    code: int
    invite_id: Optional[str] = None


# Standardized response for listing appointments.
class AppointmentListResponse(BaseModel):
    appointments: List[dict]
    code: int


# Response containing occupied timeslots for a user.
class BusySlotsResponse(BaseModel):
    busy_slots: List[str]
    code: int
