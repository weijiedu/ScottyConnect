"""
Feedback Service
Handles feedback operations using FeedbackDAO for persistence.
Subscribes to LIFECYCLE_MESSAGE to open feedback when an event ends.
Publishes FEEDBACK_MESSAGE when a new feedback is submitted.
"""

from app.bus.message import Message, MessageType
from app.bus.message_bus import MessageBus, Service
from app.feedback.feedback_dao import FeedbackDAO
from app.feedback.model.Feedback import Feedback
from app.feedback.schemas import (
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackStatusResponse,
    PublicFeedback,
    SubmitFeedbackRequest,
)
from app.logging.service import LoggerService

FEEDBACK_SERVICE_EXTENSION_KEY = "feedback_service"


def get_feedback_service() -> "FeedbackService":
    from flask import current_app

    return current_app.extensions[FEEDBACK_SERVICE_EXTENSION_KEY]


class FeedbackService(Service):
    def __init__(self, feedback_dao: FeedbackDAO | None = None) -> None:
        super().__init__()
        self.key = FEEDBACK_SERVICE_EXTENSION_KEY
        self._dao = feedback_dao or FeedbackDAO()
        self._logger = LoggerService(service_name=self.key)
        # Subscribe to lifecycle events to be notified when events end
        self.subscribeToMessages([MessageType.LIFECYCLE_MESSAGE])

    @staticmethod
    def _to_public_feedback(feedback: Feedback) -> PublicFeedback:
        return PublicFeedback(
            id=feedback.id,
            event_id=feedback.event_id,
            participant_id=feedback.participant_id,
            rating=feedback.rating,
            comment=feedback.comment,
            created_at=feedback.created_at,
        )

    # Submits feedback for an event on behalf of an authenticated attendee.
    def submit_feedback(
        self, event_id: str, participant_id: str, req: SubmitFeedbackRequest
    ) -> FeedbackResponse:
        #  feedback window must be open for this event.
        if not self._dao.is_feedback_enabled(event_id):
            return FeedbackResponse(
                message="Feedback is not yet available for this event.",
                feedback=None,
                code=403,
            )
        # the user must be in the eligible pool (confirmed attendee).
        if participant_id not in self._dao.get_eligible_user_ids(event_id):
            return FeedbackResponse(
                message="You must have attended the event to submit feedback.",
                feedback=None,
                code=403,
            )
        #  prevent duplicate submissions.
        if self._dao.find_by_event_and_participant(event_id, participant_id):
            return FeedbackResponse(
                message="You have already submitted feedback for this event.",
                feedback=None,
                code=409,
            )

        feedback = Feedback(
            event_id=event_id,
            participant_id=participant_id,
            rating=req.rating,
            comment=req.comment,
        )
        saved = self._dao.insert(feedback)
        self._logger.info(f"Feedback submitted for event {event_id} by participant {participant_id}", event_id=event_id, user_id=participant_id)
        # Notify Notification
        self.publishMessage(
            Message(
                MessageType.FEEDBACK_MESSAGE,
                {
                    "action": "feedback_submitted",
                    "feedback_id": saved.id,
                    "event_id": saved.event_id,
                    "participant_id": saved.participant_id,
                    "rating": saved.rating,
                },
            )
        )

        return FeedbackResponse(
            message="Feedback submitted successfully.",
            feedback=self._to_public_feedback(saved),
            code=201,
        )

    def get_feedback_status(self, event_id: str, user_id: str) -> FeedbackStatusResponse:
        enabled = self._dao.is_feedback_enabled(event_id)
        eligible = user_id in self._dao.get_eligible_user_ids(event_id) if enabled else False
        return FeedbackStatusResponse(
            message="Feedback status retrieved.",
            enabled=enabled,
            eligible=eligible,
            code=200,
        )

    def get_my_event_feedback(self, event_id: str, user_id: str) -> FeedbackResponse:
        feedback = self._dao.find_by_event_and_participant(event_id, user_id)
        if not feedback:
            return FeedbackResponse(
                message="You have not submitted feedback for this event.",
                feedback=None,
                code=404,
            )
        return FeedbackResponse(
            message="Successfully retrieved your feedback for this event.",
            feedback=self._to_public_feedback(feedback),
            code=200,
        )

    def get_feedbacks(self, event_id: str) -> FeedbackListResponse:
        feedbacks = self._dao.find_by_event(event_id)
        return FeedbackListResponse(
            message="Successfully retrieved feedback for the event.",
            feedbacks=[self._to_public_feedback(f) for f in feedbacks],
            code=200,
        )

    def get_my_feedbacks(self, user_id: str) -> FeedbackListResponse:
        feedbacks = self._dao.find_by_user(user_id)
        return FeedbackListResponse(
            message="Successfully retrieved your feedback history.",
            feedbacks=[self._to_public_feedback(f) for f in feedbacks],
            code=200,
        )

    # Handles messages from the event bus.
    # Enable feedback session so the feedback window is open for those users.
    def processMessage(self, message: Message) -> None:
        self._logger.info(f"Processing message: {message}")
        if message.get_type() == MessageType.LIFECYCLE_MESSAGE:
            data = message.get_data()
            new_status = data.get("new_status")
            event_id = data.get("event_id")

            if new_status == "ended":
                eligible_user_ids = self._dao.find_attendees_by_event(event_id)
                self._dao.enable_feedback(event_id, eligible_user_ids)
