"""
Email Builder Base Class
"""

from app.notification.model.Email import Email
from app.notification.builder.templates import EmailTemplates
from app.bus.message import Message
from datetime import datetime, timezone, timedelta
from app.networking.utils import format_to_la_display

class EmailBuilder:   
    def __init__(self, message: Message):
        self.message = message
        email_template = EmailTemplates.message_type_to_email_template(message.get_type())
        self.template = email_template.template
        self.subject = email_template.subject
        self.email_type = email_template.email_type
        self.body = None
        self.event_id = message.data["event_id"] if "event_id" in message.data else None
        self.recipient_email = message.data["recipient_email"]
        self.send_time = message.data["send_time"] if "send_time" in message.data else datetime.now(timezone.utc)

    def build(self) -> Email:
        """Build the email."""
        if self.body is None:
            raise ValueError("Body is not set")

        return Email(
            recipient_email=self.recipient_email,
            subject=self.subject,
            body=self.body,
            email_type=self.email_type,
            send_time=self.send_time,
            sent_successfully=False,
            event_id=self.event_id,
        )
    
    def _event_json_to_string(self, event_info: dict) -> str:
        return f"""
        Event Name: {event_info["title"]}
        Event Description: {event_info["description"]}
        Event Date: {event_info["date"]} {event_info["start_time"]} - {event_info["end_time"]}
        Event Location: {event_info["location"]}
        """

    def _coffee_chat_json_to_string(self, sender_name: str, receiver_name: str, coffee_chat_info: dict) -> str:
        scheduled_at = coffee_chat_info["scheduled_at"]
        scheduled_at_str = format_to_la_display(scheduled_at) if isinstance(scheduled_at, datetime) else str(scheduled_at)
        return f"""
        Coffee Chat Requester: {sender_name}
        Coffee Chat Receiver: {receiver_name}
        Coffee Chat Time: {scheduled_at_str}
        Current Status: {coffee_chat_info["status"]}
        """