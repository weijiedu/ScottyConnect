"""
Attendance Schemas
Pydantic models for attendance request validation and API responses.
"""

from app.accounts.schemas import PublicUser
from app.lifecycle.schemas import PublicEvent
from pydantic import BaseModel

# Register event response schema
class RegisterEventResponse(BaseModel):
    registered: bool
    message: str
    code: int

# Attend event response schema
class AttendEventResponse(BaseModel):
    attended: bool
    message: str
    code: int

# Attendance record response schema
class AttendanceRecordResponse(BaseModel):
    message: str
    code: int
    users: list[PublicUser]

# Registered events response schema
class ListEventsResponse(BaseModel):
    message: str
    code: int
    events: list[PublicEvent]