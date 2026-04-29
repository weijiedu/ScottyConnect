"""
Email Templates
"""

from enum import Enum
from textwrap import dedent

from app.notification.model.Email import EmailType
from app.bus.message import MessageType

class EmailTemplate:
    def __init__(self, template: str, subject: str, email_type: EmailType):
        self.template = dedent(template).strip()
        self.subject = subject 
        self.email_type = email_type

class EmailTemplates(Enum):
    VERIFICATION = EmailTemplate(
        """
        ScottyConnect Account Verification
        Welcome to ScottyConnect!
        Your verification code is: {verification_code}

        Enter this code in the app to verify your email address and complete setup.
        If you did not request this verification, you can safely ignore this message.
        """,
        "ScottyConnect Account Verification",
        EmailType.VERIFICATION,
    )
    EVENT_REGISTRATION_CONFIRMATION = EmailTemplate(
        """
        ScottyConnect Event Registration Confirmation
        You are officially registered for:

        {event_info}

        We are excited to have you join.
        You can review event details and updates anytime in the My Events page.
        If your plans change, please cancel early so another attendee can take your spot.
        """,
        "ScottyConnect Event Registration Confirmation",
        EmailType.EVENT_REGISTRATION_CONFIRMATION,
    )

    EVENT_REGISTRATION_CANCELLED = EmailTemplate(
        """
        ScottyConnect Event Registration Cancellation
        We are sorry to share that you have been unregistered from:
       
        {event_info}

        No further action is required from you.
        Please check the app for replacement sessions or related events.
        Thank you for your understanding.
        """,
        "ScottyConnect Event Registration Cancellation",
        EmailType.EVENT_REGISTRATION_CANCELLED,
    )

    EVENT_REMINDER = EmailTemplate(
        """
        ScottyConnect Event Reminder
        This is a reminder for your upcoming event that is scheduled in 1 hour:
        
        {event_info}

        Please double-check the event details in the app before attending.
        Arrive a few minutes early to make check-in smooth.
        We look forward to seeing you there.
        """,
        "ScottyConnect Event Reminder",
        EmailType.EVENT_REMINDER,
    )
    EVENT_CANCELLED = EmailTemplate(
        """
        ScottyConnect Event Cancellation Notice
        We are sorry to share that the following event has been cancelled:
        
        {event_info}

        No further action is required from you.
        Please check the app for replacement sessions or related events.
        Thank you for your understanding.
        """,
        "ScottyConnect Event Cancellation Notice",
        EmailType.EVENT_CANCELLED,
    )
    EVENT_UPDATED = EmailTemplate(
        """
        ScottyConnect Event Update
        There are new changes to one of your events!

        Previous information:
        
        {previous_event_info}

        New event information:
        
        {updated_event_info}

        Please open the event in the app to review the latest schedule and details.
        If the update affects your availability, you can manage your registration there.
        """,
        "ScottyConnect Event Update",
        EmailType.EVENT_UPDATED,
    )

    ATTENDANCE_RECORDED = EmailTemplate(
        """
        ScottyConnect Attendance Confirmation
        Your attendance has been recorded successfully for:
        
        {event_info}

        Thanks for participating.
        Keep attending events to build your activity history and stay engaged with the community.
        """,
        "ScottyConnect Attendance Confirmation",
        EmailType.ATTENDANCE_RECORDED,
    )
    FEEDBACK_SUBMITTED = EmailTemplate(
        """
        ScottyConnect New Event Feedback

        Someone provided feedback for your event:
        {event_info}

        You can view the feedback in the app.
        """,
        "ScottyConnect Feedback Available",
        EmailType.FEEDBACK_SUBMITTED,
    )

    COFFEE_CHAT_REQUESTED = EmailTemplate(
        """
        ScottyConnect Coffee Chat Request
        {sender_name} requested a coffee chat with you:
        
        {coffee_chat_info}

        Please review the request and accept or decline it in the app.
        """,
        "ScottyConnect Coffee Chat Request",
        EmailType.COFFEE_CHAT_REQUESTED,
    )

    COFFEE_CHAT_ACCEPTED = EmailTemplate(
        """
        ScottyConnect Coffee Chat Accepted
        {sender_name} accepted your coffee chat request:
        
        {coffee_chat_info}
        """,
        "ScottyConnect Coffee Chat Accepted",
        EmailType.COFFEE_CHAT_ACCEPTED,
    )

    COFFEE_CHAT_DECLINED = EmailTemplate(
        """
        ScottyConnect Coffee Chat Declined
        {sender_name} declined your coffee chat request:
        
        {coffee_chat_info}
        """,
        "ScottyConnect Coffee Chat Declined",
        EmailType.COFFEE_CHAT_DECLINED,
    )

    COFFEE_CHAT_CANCELLED = EmailTemplate(
        """
        ScottyConnect Coffee Chat Cancelled
        This email confirms that the following coffee chat has been cancelled:

        {coffee_chat_info}
        """,
        "ScottyConnect Coffee Chat Cancelled",
        EmailType.COFFEE_CHAT_CANCELLED,
    )

    @staticmethod
    def message_type_to_email_template(message_type: MessageType) -> EmailTemplate:
        if message_type == MessageType.REGISTER_MESSAGE:
            return EmailTemplates.VERIFICATION.value
        elif message_type == MessageType.EVENT_REGISTRATION_CONFIRMATION:
            return EmailTemplates.EVENT_REGISTRATION_CONFIRMATION.value
        elif message_type == MessageType.EVENT_REGISTRATION_CANCELLED:
            return EmailTemplates.EVENT_REGISTRATION_CANCELLED.value
        elif message_type == MessageType.EVENT_REMINDER:
            return EmailTemplates.EVENT_REMINDER.value
        elif message_type == MessageType.EVENT_CANCELLED:
            return EmailTemplates.EVENT_CANCELLED.value
        elif message_type == MessageType.EVENT_UPDATED:
            return EmailTemplates.EVENT_UPDATED.value
        elif message_type == MessageType.ATTENDANCE_RECORDED:
            return EmailTemplates.ATTENDANCE_RECORDED.value
        elif message_type == MessageType.FEEDBACK_MESSAGE:
            return EmailTemplates.FEEDBACK_SUBMITTED.value
        elif message_type == MessageType.COFFEE_CHAT_REQUESTED:
            return EmailTemplates.COFFEE_CHAT_REQUESTED.value
        elif message_type == MessageType.COFFEE_CHAT_ACCEPTED:
            return EmailTemplates.COFFEE_CHAT_ACCEPTED.value
        elif message_type == MessageType.COFFEE_CHAT_DECLINED:
            return EmailTemplates.COFFEE_CHAT_DECLINED.value
        elif message_type == MessageType.COFFEE_CHAT_CANCELLED:
            return EmailTemplates.COFFEE_CHAT_CANCELLED.value
        else:
            raise ValueError(f"Invalid message type: {message_type}")