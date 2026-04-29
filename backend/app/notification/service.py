"""
Notification Service

Handles notification operations using NotificationDAO for persistence.
"""

# Email Domain Utilities
from app.notification.notification_dao import EmailDAO
from app.notification.model.Email import Email
from app.notification.gmail_sender import GmailSender
from app.logging.service import LoggerService

# Standard Utilities
import time
from datetime import datetime, timedelta, timezone
from threading import Lock, Thread

# Builders
from app.notification.builder.verification_builder import VerificationBuilder
from app.notification.builder.event_register_builder import EventRegisterBuilder
from app.notification.builder.event_unregister_builder import EventUnregisterBuilder
from app.notification.builder.event_update_builder import EventUpdateBuilder
from app.notification.builder.attendance_builder import AttendanceBuilder
from app.notification.builder.event_reminder_builder import EventReminderBuilder
from app.notification.builder.event_cancel_builder import EventCancelBuilder
from app.notification.builder.feedback_builder import FeedbackBuilder
from app.notification.builder.coffee_request_builder import CoffeeChatRequestBuilder
from app.notification.builder.coffee_accept_builder import CoffeeChatAcceptedBuilder
from app.notification.builder.coffee_decline_builder import CoffeeChatDeclinedBuilder
from app.notification.builder.coffee_cancel_builder import CoffeeChatCancelledBuilder

# Message Bus
from app.bus.message_bus import Service
from app.bus.message import Message
from app.bus.message import MessageType

import logging
logger = logging.getLogger(__name__)

NOTIFICATION_SERVICE_EXTENSION_KEY = "notification_service"

SUBSCRIBED_MESSAGE_TYPES = [
    MessageType.REGISTER_MESSAGE,
    MessageType.EVENT_REGISTRATION_CONFIRMATION,
    MessageType.EVENT_REGISTRATION_CANCELLED,
    MessageType.EVENT_REMINDER,
    MessageType.EVENT_CANCELLED,
    MessageType.EVENT_UPDATED,
    MessageType.ATTENDANCE_RECORDED,
    MessageType.FEEDBACK_MESSAGE,
    MessageType.COFFEE_CHAT_REQUESTED,
    MessageType.COFFEE_CHAT_ACCEPTED,
    MessageType.COFFEE_CHAT_DECLINED,
    MessageType.COFFEE_CHAT_CANCELLED,
]

class NotificationService(Service):
    
    def __init__(self):
        super().__init__()
        self._worker: Thread | None = None
        self._worker_lock = Lock()
        self._dao = EmailDAO()
        self.key = NOTIFICATION_SERVICE_EXTENSION_KEY
        self._logger = LoggerService(service_name=self.key)
        self.subscribeToMessages(SUBSCRIBED_MESSAGE_TYPES)

    @staticmethod
    def _get_event_datetime(event_info: dict) -> datetime | None:
        event_date = event_info.get("date")
        start_time = event_info.get("start_time")
        if not isinstance(event_date, str) or not isinstance(start_time, str):
            return None
        try:
            event_time = datetime.strptime(
                f"{event_date} {start_time[:5]}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            return None
        # Treat schedule timestamps as UTC for consistent comparisons.
        return event_time.replace(tzinfo=timezone.utc)

    def _handle_register_message(self, message: Message) -> list[Email]:
        return [VerificationBuilder(message).build()]

    def _handle_event_registration_confirmation(self, message: Message) -> list[Email]:
        email = EventRegisterBuilder(message).build()
        prev_email = self._dao.find_confirmation_email(email.recipient_email, email.event_id)
        # Delete previous confirmation and reminder email if it exists.
        if prev_email:
            self._dao.delete(prev_email.id)
            self._dao.delete_reminder(email.event_id, email.recipient_email)
        # Publish EVENT_REMINDER message.
        event_info = message.data["event_info"]
        event_time = self._get_event_datetime(event_info)
        send_time = event_time - timedelta(hours=1)
        self.publishMessage(Message(MessageType.EVENT_REMINDER, {
            "event_id": event_info["id"],
            "event_info": event_info,
            "recipient_email": email.recipient_email,
            "send_time": send_time.isoformat(),
        }))
        return [email]

    def _handle_event_registration_cancelled(self, message: Message) -> list[Email]:
        email = EventUnregisterBuilder(message).build()
        # Delete previous confirmation email if it exists.
        prev_email = self._dao.find_confirmation_email(email.recipient_email, email.event_id)
        if prev_email:
            self._dao.delete(prev_email.id)
        # Remove reminder for the recipient
        self._dao.delete_reminder(email.event_id, email.recipient_email)
        return [email]

    def _handle_event_reminder(self, message: Message) -> list[Email]:
        return [EventReminderBuilder(message).build()]

    def _handle_event_cancelled(self, message: Message) -> list[Email]:
        data = dict(message.get_data())
        emails = []
        # Send email to the recipient.
        event_id = data.get("event_id")
        recipients = self._dao.find_registered_user_emails(event_id)
        for recipient_email in recipients:
            fanout_message = Message(
                MessageType.EVENT_CANCELLED,
                {**data, "recipient_email": recipient_email},
            )
            emails.append(EventCancelBuilder(fanout_message).build())
        # Delete all reminders for the event.
        if event_id:
            self._dao.delete_all_reminders_by_event_id(event_id)
        return emails

    def _handle_event_updated(self, message: Message) -> list[Email]:
        # Not used for now - published events cannot be changed atm.
        return [EventUpdateBuilder(message).build()]

    def _handle_attendance_recorded(self, message: Message) -> list[Email]:
        return [AttendanceBuilder(message).build()]

    def _handle_feedback_message(self, message: Message) -> list[Email]:
        data = dict(message.get_data())
        event_id = data.get("event_id")
        recipient_email = self._dao.find_event_owner_email(event_id)
        event_info = self._dao.find_event_info(event_id)
        complete_message = Message(
            MessageType.FEEDBACK_MESSAGE,
            {
                "event_id": event_id,
                "recipient_email": recipient_email,
                "event_info": event_info,
            },
        )
        return [FeedbackBuilder(complete_message).build()]

    def _handle_coffee_chat_requested(self, message: Message) -> list[Email]:
        data = dict(message.get_data())
        sender_id = data.get("sender_id")
        receiver_id = data.get("receiver_id")
        invite_id = data.get("invite_id")
        sender_name = self._dao.find_user_name_by_id(sender_id)
        receiver_name = self._dao.find_user_name_by_id(receiver_id)
        recipient_email = self._dao.find_user_email_by_id(receiver_id)
        coffee_chat_info = self._dao.find_coffee_chat_info(invite_id)
        complete_message = Message(MessageType.COFFEE_CHAT_REQUESTED, {
            "sender_name": sender_name,
            "receiver_name": receiver_name,
            "recipient_email": recipient_email,
            "coffee_chat_info": coffee_chat_info,
        })
        return [CoffeeChatRequestBuilder(complete_message).build()]

    def _handle_coffee_chat_accepted(self, message: Message) -> list[Email]:
        data = dict(message.get_data())
        sender_id = data.get("sender_id")
        receiver_id = data.get("receiver_id")
        invite_id = data.get("invite_id")
        sender_name = self._dao.find_user_name_by_id(sender_id)
        receiver_name = self._dao.find_user_name_by_id(receiver_id)
        recipient_email = self._dao.find_user_email_by_id(sender_id)
        coffee_chat_info = self._dao.find_coffee_chat_info(invite_id)
        complete_message = Message(MessageType.COFFEE_CHAT_ACCEPTED, {
            "sender_name": sender_name,
            "receiver_name": receiver_name,
            "recipient_email": recipient_email,
            "coffee_chat_info": coffee_chat_info,
        })
        return [CoffeeChatAcceptedBuilder(complete_message).build()]

    def _handle_coffee_chat_declined(self, message: Message) -> list[Email]:
        data = dict(message.get_data())
        sender_id = data.get("sender_id")
        receiver_id = data.get("receiver_id")
        invite_id = data.get("invite_id")
        sender_name = self._dao.find_user_name_by_id(sender_id)
        receiver_name = self._dao.find_user_name_by_id(receiver_id)
        recipient_email = self._dao.find_user_email_by_id(sender_id)
        coffee_chat_info = self._dao.find_coffee_chat_info(invite_id)
        complete_message = Message(MessageType.COFFEE_CHAT_DECLINED, {
            "sender_name": sender_name,
            "receiver_name": receiver_name,
            "recipient_email": recipient_email,
            "coffee_chat_info": coffee_chat_info,
        })
        return [CoffeeChatDeclinedBuilder(complete_message).build()]

    def _handle_coffee_chat_cancelled(self, message: Message) -> list[Email]:
        data = dict(message.get_data())
        sender_id = data.get("sender_id")
        receiver_id = data.get("receiver_id")
        invite_id = data.get("invite_id")
        sender_name = self._dao.find_user_name_by_id(sender_id)
        receiver_name = self._dao.find_user_name_by_id(receiver_id)
        sender_email = self._dao.find_user_email_by_id(sender_id)
        receiver_email = self._dao.find_user_email_by_id(receiver_id)
        coffee_chat_info = self._dao.find_coffee_chat_info(invite_id)
        # Send email to the sender and receiver.
        complete_message_sender = Message(MessageType.COFFEE_CHAT_CANCELLED, {
            "sender_name": sender_name,
            "receiver_name": receiver_name,
            "recipient_email": sender_email,
            "coffee_chat_info": coffee_chat_info,
        })
        complete_message_receiver = Message(MessageType.COFFEE_CHAT_CANCELLED, {
            "sender_name": sender_name,
            "receiver_name": receiver_name,
            "recipient_email": receiver_email,
            "coffee_chat_info": coffee_chat_info,
        })
        return [
            CoffeeChatCancelledBuilder(complete_message_sender).build(), 
            CoffeeChatCancelledBuilder(complete_message_receiver).build()
        ]

    def processMessage(self, message: Message) -> None:
        message_type = message.get_type()
        handlers = {
            MessageType.REGISTER_MESSAGE: self._handle_register_message,
            MessageType.EVENT_REGISTRATION_CONFIRMATION: self._handle_event_registration_confirmation,
            MessageType.EVENT_REGISTRATION_CANCELLED: self._handle_event_registration_cancelled,
            MessageType.EVENT_REMINDER: self._handle_event_reminder,
            MessageType.EVENT_CANCELLED: self._handle_event_cancelled,
            MessageType.EVENT_UPDATED: self._handle_event_updated,
            MessageType.ATTENDANCE_RECORDED: self._handle_attendance_recorded,
            MessageType.FEEDBACK_MESSAGE: self._handle_feedback_message,
            MessageType.COFFEE_CHAT_REQUESTED: self._handle_coffee_chat_requested,
            MessageType.COFFEE_CHAT_ACCEPTED: self._handle_coffee_chat_accepted,
            MessageType.COFFEE_CHAT_DECLINED: self._handle_coffee_chat_declined,
            MessageType.COFFEE_CHAT_CANCELLED: self._handle_coffee_chat_cancelled,
        }
        handler = handlers.get(message_type)
        if handler is None:
            self._logger.error(f"Invalid message type: {message_type}")
            return
        emails = handler(message)
        for email in emails:
            self._dao.insert(email)

    def poll_and_send_emails(self) -> None:
        cnt = 1
        while True:
            try:
                emails = self._dao.find_unsent_emails()
                for email in emails:
                    try:
                        if self._send_email(email):
                            self._dao.update_sent_successfully(email.id)
                    except Exception:
                        self._logger.error(
                            f"Failed to process email notification id={email.id}", 
                            event_id=email.event_id if email.event_id else None
                        )
            except Exception as e:
                self._logger.error(f"Notification polling cycle {cnt} failed: {e}")
            cnt += 1
            time.sleep(60)
        
    def _send_email(self, email: Email) -> bool:
        self._logger.info(f"Sending email to {email.recipient_email} for event {email.event_id}")
        return GmailSender().send_email(email.recipient_email, email.subject, email.body)
        
    
    def start_worker(self) -> None:
        with self._worker_lock:
            if self._worker and self._worker.is_alive():
                return
            self._worker = Thread(
                target=self.poll_and_send_emails,
                name="notification-worker",
                daemon=True,
            )
            self._worker.start()
            logger.info("Started notification worker thread")