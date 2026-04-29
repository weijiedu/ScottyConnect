"""
Verification Email Builder
"""

from app.notification.builder.base_builder import EmailBuilder
from app.notification.model.Email import Email
from app.bus.message import Message
from app.bus.message import MessageType

class VerificationBuilder(EmailBuilder):
    def __init__(self, message: Message):
        # Check message type is REGISTER_MESSAGE
        if message.get_type() != MessageType.REGISTER_MESSAGE:
            raise ValueError("System Error:Message type is not REGISTER_MESSAGE")
        super().__init__(message)
        
    def fill_template(self):
        self.body = self.template.format(
            verification_code=self.message.data["verification_code"]
        )
    
    def build(self) -> Email:
        self.fill_template()
        return super().build()