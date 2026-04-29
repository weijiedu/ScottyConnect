"""
Email Persistence Model

This model is used to store email data in the database.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

class EmailType(str, Enum):
    # User registration related emails
    VERIFICATION = "VERIFICATION"
    
    # Event related emails
    EVENT_REGISTRATION_CONFIRMATION = "EVENT_REGISTRATION_CONFIRMATION"
    EVENT_REGISTRATION_CANCELLED = "EVENT_REGISTRATION_CANCELLED"
    EVENT_REMINDER = "EVENT_REMINDER"
    EVENT_CANCELLED = "EVENT_CANCELLED"
    EVENT_UPDATED = "EVENT_UPDATED"
    ATTENDANCE_RECORDED = "ATTENDANCE_RECORDED" # Not used for now
    
    # Feedback related emails
    FEEDBACK_SUBMITTED = "FEEDBACK_SUBMITTED"
    
    # Networking related emails
    COFFEE_CHAT_REQUESTED = "COFFEE_CHAT_REQUESTED"
    COFFEE_CHAT_ACCEPTED = "COFFEE_CHAT_ACCEPTED"
    COFFEE_CHAT_DECLINED = "COFFEE_CHAT_DECLINED"
    COFFEE_CHAT_CANCELLED = "COFFEE_CHAT_CANCELLED"


class Email(BaseModel):
    id: str | None = None
    recipient_email: str
    subject: str
    body: str
    email_type: EmailType
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    send_time: datetime | None = None
    sent_successfully: bool = False
    event_id: str | None = None
    