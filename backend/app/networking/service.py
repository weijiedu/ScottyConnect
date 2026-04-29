"""
Networking Service
Service layer for managing 1-on-1 coffee chat orchestration.
Implements the ICoffeeChatMediator protocol to coordinate between Participants.
"""

from datetime import datetime, timezone
from typing import Optional, Tuple, List

from app.accounts.service import get_account_service
from app.bus.message import MessageType, Message
from app.bus.message_bus import MessageBus
from app.networking.appointment_dao import AppointmentDAO
from app.networking.model.Appointment import Appointment, AppointmentStatus
from app.networking.model.Participant import Participant, ParticipantFactory, ICoffeeChatMediator
from app.networking.policies.policy_factory import InvitePolicyFactory
from app.networking.schemas import (
    AppointmentResponse,
    BusySlotsResponse,
    InviteRequest,
    RespondRequest,
)
from app.logging.service import LoggerService
from app.networking.utils import format_to_la_display, LA_TZ

NETWORKING_SERVICE_EXTENSION_KEY = "networking_service"


class NetworkingService(ICoffeeChatMediator):
    """
    Service responsible for coordinating coffee chat interactions.
    Flattened architecture: Implements ICoffeeChatMediator directly to reduce complexity.
    """
    
    def __init__(self, dao: Optional[AppointmentDAO] = None) -> None:
        self._dao = dao or AppointmentDAO()
        self._invite_policy_factory = InvitePolicyFactory()
        self.key = NETWORKING_SERVICE_EXTENSION_KEY
        self._logger = LoggerService(service_name=self.key)

    # --- ICoffeeChatMediator Implementation ---

    def dispatch_invite(
        self,
        sender: Participant,
        receiver_id: str,
        scheduled_at: datetime,
        receiver_role: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Centralized orchestration for sending an invitation.
        Enforces policy and availability before persisting.
        """
        
        # 1. Policy enforcement
        policy = self._invite_policy_factory.for_role(sender.get_role())
        allowed, reason = policy.can_send_invite(
            sender_id=sender.user_id,
            receiver_role=receiver_role,
            receiver_id=receiver_id,
            scheduled_at=scheduled_at,
            dao=self._dao,
            now=datetime.now(timezone.utc),
        )

        if not allowed:
            return False, reason or "Policy restriction"

        # 2. Availability checks
        if not self.validate_availability(sender.user_id, scheduled_at):
            return False, "You are already booked at this time"
            
        if not self.validate_availability(receiver_id, scheduled_at):
            return False, "The recipient is already booked at this time"

        # 3. Persistence
        appointment = Appointment(
            sender_id=sender.user_id,
            receiver_id=receiver_id,
            sender_role=sender.get_role(),
            receiver_role=receiver_role.upper(),
            scheduled_at=scheduled_at,
            status=AppointmentStatus.PENDING
        )
        saved = self._dao.insert(appointment)

        # 4. Event Notification
        if saved.id:
            self.publishMessage(
                MessageType.COFFEE_CHAT_REQUESTED,
                {"sender_id": sender.user_id, "receiver_id": receiver_id, "invite_id": saved.id}
            )
            self._logger.info(f"Invitation sent successfully from {sender.user_id} to {receiver_id}", user_id=sender.user_id, event_id=saved.id)
            return True, "Invitation sent successfully"
            
        return False, "Failed to save invitation"

    def finalize_invite_response(self, responder: Participant, invite_id: str, accept: bool) -> Tuple[bool, Optional[str]]:
        """
        Updates invitation status and emits corresponding events.
        Enforces availability checks before transition to ACCEPTED.
        """
        if accept:
            appt = self._dao.find_by_id(invite_id)
            if not appt:
                return False, "Invitation not found"
            
            # 1. Availability validation (only for Acceptance)
            if not self.validate_availability(appt.sender_id, appt.scheduled_at):
                self._logger.warning(f"Acceptance blocked: Sender {appt.sender_id} is already booked", user_id=responder.user_id, event_id=invite_id)
                return False, "The meeting host is already booked at this time"
            
            if not self.validate_availability(appt.receiver_id, appt.scheduled_at):
                self._logger.warning(f"Acceptance blocked: Receiver {appt.receiver_id} is already booked", user_id=responder.user_id, event_id=invite_id)
                return False, "You are already booked at this time. Please cancel your other meeting first."

        # 2. Persist the state transition
        status = AppointmentStatus.ACCEPTED if accept else AppointmentStatus.DECLINED
        updated = self._dao.update_status_atomically(
            invite_id,
            expected_status=AppointmentStatus.PENDING,
            new_status=status,
        )

        if updated:
            appt = self._dao.find_by_id(invite_id)
            if not appt:
                return False, "Failed to retrieve updated invitation"
              
            msg_type = MessageType.COFFEE_CHAT_ACCEPTED if accept else MessageType.COFFEE_CHAT_DECLINED
            self.publishMessage(msg_type, {
                "invite_id": invite_id, 
                "sender_id": appt.sender_id, 
                "receiver_id": appt.receiver_id, 
                "responder_id": responder.user_id
            })
            self._logger.info(f"Invitation {'accepted' if accept else 'declined'} by {responder.user_id} for invite {invite_id}", user_id=responder.user_id, event_id=invite_id)

            return True, f"Invitation {status.value.lower()} successfully"

        return False, "Failed to update invitation status (it may have been cancelled or already processed)"


    def dispatch_cancellation(self, canceller: Participant, invite_id: str) -> bool:
        """
        Internal mediator logic for cancelling an invitation.
        """
        appt = self._dao.find_by_id(invite_id)
        if not appt:
            return False

        # Enforce cancellation policy: only future meetings
        now = datetime.now(timezone.utc)
        
        # Ensure scheduled_at is aware before comparison to prevent TypeError
        test_dt = appt.scheduled_at
        if test_dt.tzinfo is None:
            test_dt = test_dt.replace(tzinfo=timezone.utc)

        if test_dt < now:
            return False


        success = self._dao.update_status_atomically(
            invite_id, expected_status=appt.status, new_status=AppointmentStatus.CANCELLED
        )
        if success:
            self.publishMessage(
                MessageType.COFFEE_CHAT_CANCELLED,
                {"invite_id": invite_id, "sender_id": appt.sender_id, "receiver_id": appt.receiver_id, "canceller_id": canceller.user_id}
            )
            self._logger.info(f"Invitation cancelled by {canceller.user_id} for invite {invite_id}", user_id=canceller.user_id, event_id=invite_id)
            return True


        return False

    def validate_availability(self, user_id: str, scheduled_at: datetime) -> bool:
        """Checks if a timeslot is free for the specified user."""
        busy_slots = self._dao.get_occupied_slots(user_id)
        
        # Convert UTC input to LA time via utility for consistent comparison
        slot_label = format_to_la_display(scheduled_at)
        return slot_label not in busy_slots

    # --- Public Service Methods ---

    def request_invite(self, req: InviteRequest, sender_id: str) -> AppointmentResponse:
        """Initiates a coffee chat request by coordinating domain participants."""
        user_service = get_account_service()
        sender_user = user_service._users.find_by_id(sender_id)
        receiver_user = user_service._users.find_by_id(req.receiver_id)

        if not sender_user or not receiver_user:
            return AppointmentResponse(message="User not found", code=404)
        
        participant = ParticipantFactory.create(
            user_id=sender_user.id,
            username=sender_user.username,
            role=sender_user.role
        )
        participant.set_mediator(self)
        
        scheduled_at = self._normalize_to_utc(req.scheduled_at)
        success, reason = participant.initiate_chat(
            receiver_id=req.receiver_id,
            scheduled_at=scheduled_at,
            receiver_role=receiver_user.role,
        )

        code = 201 if success else 400
        return AppointmentResponse(message=reason or "Failed to initiate chat", code=code)

    def process_invite_response(self, req: RespondRequest, responder_id: str) -> AppointmentResponse:
        """Processes a response (accept/decline) to an existing invitation."""
        user_service = get_account_service()
        responder_user = user_service._users.find_by_id(responder_id)
        if not responder_user:
             return AppointmentResponse(message="Responder not found", code=404)

        appt = self._dao.find_by_id(req.invite_id)
        if not appt or appt.receiver_id != responder_id:
            return AppointmentResponse(message="Invalid invitation for this user", code=403 if appt else 404)

        target_status = AppointmentStatus.ACCEPTED if req.accept else AppointmentStatus.DECLINED
        if not appt.can_transition(target_status):
            return AppointmentResponse(message=f"Invalid transition from {appt.status}", code=400)

        participant = ParticipantFactory.create(
            user_id=responder_user.id,
            username=responder_user.username,
            role=responder_user.role
        )
        participant.set_mediator(self)
        
        success, reason = participant.accept_chat(req.invite_id) if req.accept else participant.decline_chat(req.invite_id)
        
        code = 200 if success else 400
        return AppointmentResponse(message=reason or "Failed to process response", code=code)

    def cancel_invite(self, appointment_id: str, sender_id: str) -> AppointmentResponse:
        """Allows participants to cancel an active appointment."""
        user_service = get_account_service()
        user = user_service._users.find_by_id(sender_id)
        if not user:
            return AppointmentResponse(message="User not found", code=404)

        appt = self._dao.find_by_id(appointment_id)
        if not appt:
            return AppointmentResponse(message="Appointment not found", code=404)
        
        if appt.sender_id != sender_id and appt.receiver_id != sender_id:
            return AppointmentResponse(message="Unauthorized", code=403)
        
        if not appt.can_transition(AppointmentStatus.CANCELLED):
            return AppointmentResponse(message="Cannot cancel in current state", code=400)
        
        participant = ParticipantFactory.create(
            user_id=user.id,
            username=user.username,
            role=user.role
        )
        participant.set_mediator(self)
        
        success = participant.cancel_chat(appointment_id)
        
        if success:
            return AppointmentResponse(message="Invitation cancelled", code=200)


        return AppointmentResponse(message="Cancellation failed or invalid timing", code=400)

    def get_appointments(self, user_id: str) -> List[dict]:
        """Fetches history and resolves participant names."""
        appts = self._dao.find_all_by_user(user_id)
        user_service = get_account_service()
        
        results = []
        user_cache = {}
        
        for a in appts:
            for uid in [a.sender_id, a.receiver_id]:
                if uid not in user_cache:
                    u = user_service._users.find_by_id(uid)
                    user_cache[uid] = u.username if u else "Unknown User"
            
            data = a.model_dump(mode="json")
            data["sender_name"] = user_cache[a.sender_id]
            data["receiver_name"] = user_cache[a.receiver_id]
            results.append(data)
            
        return results

    def get_busy_slots(self, user_id: str) -> BusySlotsResponse:
        """Returns occupied labels for client-side conflict prevention."""
        slots = self._dao.get_occupied_slots(user_id)
        return BusySlotsResponse(busy_slots=slots, code=200)

    # --- Internal Helpers ---

    def publishMessage(self, msg_type: MessageType, data: dict):
        MessageBus.publish(Message(msg_type, data))

    @staticmethod
    def _normalize_to_utc(value: datetime) -> datetime:
        """
        Normalizes any incoming datetime (aware or naive) into a timezone-aware UTC datetime.
        
        If the value is naive, it assumes it was intended for the local context (LA time)
        and converts it to UTC accordingly.
        """
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc)
        
        # Assume naive input is from our default LA timezone and convert to UTC
        return value.replace(tzinfo=LA_TZ).astimezone(timezone.utc)


def get_networking_service() -> NetworkingService:
    from flask import current_app
    return current_app.extensions[NETWORKING_SERVICE_EXTENSION_KEY]
