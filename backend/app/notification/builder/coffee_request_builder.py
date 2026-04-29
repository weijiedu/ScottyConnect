"""
Coffee Chat Request Email Builder
"""

from app.notification.builder.base_builder import EmailBuilder
from app.notification.model.Email import Email
from app.bus.message import Message
from app.bus.message import MessageType

class CoffeeChatRequestBuilder(EmailBuilder):
    def __init__(self, message: Message):
        # Check message type is COFFEE_CHAT_REQUESTED
        if message.get_type() != MessageType.COFFEE_CHAT_REQUESTED:
            raise ValueError("System Error:Message type is not COFFEE_CHAT_REQUESTED")
        super().__init__(message)
        
    def fill_template(self):
        self.body = self.template.format(
            sender_name=self.message.data["sender_name"],
            coffee_chat_info=self._coffee_chat_json_to_string(self.message.data["sender_name"], self.message.data["receiver_name"], self.message.data["coffee_chat_info"])
        )
        
    def build(self) -> Email:
        self.fill_template()
        return super().build()