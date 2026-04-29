"""
Coffee Chat Cancelled Email Builder
"""

from app.notification.builder.base_builder import EmailBuilder
from app.notification.model.Email import Email
from app.bus.message import Message
from app.bus.message import MessageType

class CoffeeChatCancelledBuilder(EmailBuilder):
    def __init__(self, message: Message):
        # Check message type is COFFEE_CHAT_CANCELLED
        if message.get_type() != MessageType.COFFEE_CHAT_CANCELLED:
            raise ValueError("System Error:Message type is not COFFEE_CHAT_CANCELLED")
        super().__init__(message)
        
    def fill_template(self):
        self.body = self.template.format(
            coffee_chat_info=self._coffee_chat_json_to_string(self.message.data["sender_name"], self.message.data["receiver_name"], self.message.data["coffee_chat_info"])
        )
        
    def build(self) -> Email:
        self.fill_template()
        return super().build()