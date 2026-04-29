"""
Attendance Recorded Email Builder
"""

from app.notification.builder.base_builder import EmailBuilder
from app.notification.model.Email import Email
from app.bus.message import Message
from app.bus.message import MessageType

class AttendanceBuilder(EmailBuilder):
    def __init__(self, message: Message):
        # Check message type is ATTENDANCE_RECORDED
        if message.get_type() != MessageType.ATTENDANCE_RECORDED:
            raise ValueError("System Error:Message type is not ATTENDANCE_RECORDED")
        super().__init__(message)
        
    def fill_template(self):
        self.body = self.template.format(
            event_info=self._event_json_to_string(self.message.data["event_info"])
        )
        
    def build(self) -> Email:
        self.fill_template()
        return super().build()