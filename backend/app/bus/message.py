from enum import Enum
import json

"""
Enum class to represent the types of messages in the message bus.
"""
class MessageType(Enum):
    # Message for user registration success, should submit request to send verification email.

    # Should send verification email.
    REGISTER_MESSAGE = "REGISTER_MESSAGE"
    # Should send event registration confirmation email.
    EVENT_REGISTRATION_CONFIRMATION = "EVENT_REGISTRATION_CONFIRMATION"
    # Should send event registration cancelled email.
    EVENT_REGISTRATION_CANCELLED = "EVENT_REGISTRATION_CANCELLED"
    # Should send event reminder email.
    EVENT_REMINDER = "EVENT_REMINDER"
    # Should send event cancelled email.
    EVENT_CANCELLED = "EVENT_CANCELLED"
    # Should send event updated email.
    EVENT_UPDATED = "EVENT_UPDATED"
    # Should send attendance recorded email.
    ATTENDANCE_RECORDED = "ATTENDANCE_RECORDED"
    # Should send feedback submitted email.
    FEEDBACK_MESSAGE = "FEEDBACK_MESSAGE"

    LIFECYCLE_MESSAGE = "LIFECYCLE_MESSAGE"
    # Networking related messages
    COFFEE_CHAT_REQUESTED = "COFFEE_CHAT_REQUESTED"
    COFFEE_CHAT_ACCEPTED = "COFFEE_CHAT_ACCEPTED"
    COFFEE_CHAT_DECLINED = "COFFEE_CHAT_DECLINED"
    COFFEE_CHAT_CANCELLED = "COFFEE_CHAT_CANCELLED"
    
    TASKS_MESSAGE = "TASKS_MESSAGE"

class Message:
    """
    Message class to represent a message in the message bus.
    """
    def __init__(self, type: MessageType, data: dict):
        self.type = type
        self.data = data
    
    def __str__(self):
        return f"Message(type={self.type.value}, data={json.dumps(self.data)})"

    def get_type(self) -> MessageType:
        return self.type
    
    def get_data(self) -> dict:
        return self.data