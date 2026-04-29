"""
Attendance Record Model
Records the registration and attendance of a user at an event.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AttendanceRecord(BaseModel):
    id: str | None = None
    event_id: str
    user_id: str
    registration_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    attendance_time: datetime | None = None