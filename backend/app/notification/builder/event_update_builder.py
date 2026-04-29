"""
Event Update Email Builder
"""

from app.notification.builder.base_builder import EmailBuilder
from app.notification.model.Email import Email
from app.bus.message import Message
from app.bus.message import MessageType

class EventUpdateBuilder(EmailBuilder):
    def __init__(self, message: Message):
        # Check message type is EVENT_UPDATED
        if message.get_type() != MessageType.EVENT_UPDATED:
            raise ValueError("System Error:Message type is not EVENT_UPDATED")
        super().__init__(message)
        
    def fill_template(self):
        self.body = self.template.format(
            previous_event_info=self._event_json_to_string(self.message.data["previous_event_info"]),
            updated_event_info=self._event_json_to_string(self.message.data["updated_event_info"])
        )
        
    def build(self) -> Email:
        self.fill_template()
        return super().build()