"""
Lifecycle Service
Handles event lifecycle operations using LifecycleDAO for persistence
and the State Pattern for transition/permission validation.
"""

from datetime import datetime

from app.attendance.attendance_dao import AttendanceDAO
from app.bus.message import Message, MessageType
from app.bus.message_bus import Service
from app.lifecycle.lifecycle_dao import LifecycleDAO
from app.lifecycle.model.Event import Event
from app.lifecycle.schemas import (
    CreateEventRequest,
    EventListResponse,
    EventResponse,
    PublicEvent,
    UpdateEventRequest,
)
from zoneinfo import ZoneInfo

from app.lifecycle.schedule_validation import (
    parse_event_end_datetime,
    resolve_lifecycle_clock_tz,
    validate_event_schedule,
)
from app.lifecycle.states import resolve_state
from app.logging.service import LoggerService

LIFECYCLE_SERVICE_EXTENSION_KEY = "lifecycle_service"


def get_lifecycle_service() -> "LifecycleService":
    from flask import current_app

    return current_app.extensions[LIFECYCLE_SERVICE_EXTENSION_KEY]


class LifecycleService(Service):
    def __init__(
        self,
        lifecycle_dao: LifecycleDAO | None = None,
        attendance_dao: AttendanceDAO | None = None,
    ) -> None:
        super().__init__()
        self.key = LIFECYCLE_SERVICE_EXTENSION_KEY
        self._dao = lifecycle_dao or LifecycleDAO()
        self._attendance_dao = attendance_dao or AttendanceDAO()
        self._logger = LoggerService(service_name=self.key)
    def _can_read_event_detail(
        self, event: Event, requester_id: str | None
    ) -> bool:
        """Public feed is published-only; owners and registered attendees may see other states."""
        if event.status == "published":
            return True
        if requester_id is None:
            return False
        if requester_id == event.owner_id:
            return True
        if not event.id:
            return False
        return (
            self._attendance_dao.find_record_by_event_and_user(
                event.id, requester_id
            )
            is not None
        )

    @staticmethod
    def _to_public_event(event: Event) -> PublicEvent:
        return PublicEvent(
            id=event.id,
            title=event.title,
            description=event.description,
            date=event.date,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            capacity=event.capacity,
            owner_id=event.owner_id,
            status=event.status,
            created_at=event.created_at.isoformat(),
            updated_at=event.updated_at.isoformat(),
        )

    @staticmethod
    def _published_schedule_end_has_passed(
        event: Event, clock_tz: ZoneInfo
    ) -> bool:
        if event.status != "published":
            return False
        end_dt = parse_event_end_datetime(
            event.date, event.end_time, clock_tz=clock_tz
        )
        if end_dt is None:
            return False
        return datetime.now(clock_tz) >= end_dt

    def _persist_transition(self, event: Event, target_status: str) -> Event:
        """Update status and emit the same bus notifications as ``transition``."""
        old_status = event.status
        event_id = event.id
        if not event_id:
            raise ValueError("Event id is required to persist a transition")
        updated = self._dao.update_status(event_id, target_status)
        self.publishMessage(
            Message(
                MessageType.LIFECYCLE_MESSAGE,
                {
                    "event_id": event_id,
                    "new_status": target_status,
                    "old_status": old_status,
                },
            )
        )
        if target_status == "cancelled":
            self.publishMessage(
                Message(
                    MessageType.EVENT_CANCELLED,
                    {
                        "event_id": event_id,
                        "event_info": self._to_public_event(event).model_dump(
                            mode="json"
                        ),
                    },
                )
            )
        if updated is None:
            raise ValueError("Failed to load event after status update")
        return updated

    def _sync_expired_published_event(
        self, event: Event, clock_tz: ZoneInfo
    ) -> Event:
        """
        If a published event's scheduled end is in the past, persist ``ended``
        using the same transition path as a manual end (state validation + bus).
        """
        if not self._published_schedule_end_has_passed(event, clock_tz):
            return event
        state = resolve_state(event.status)
        try:
            state.handle_transition("ended")
        except ValueError:
            return event
        return self._persist_transition(event, "ended")

    def sync_all_expired_published_events(
        self, client_tz: str | None = None
    ) -> tuple[int, int]:
        """
        Sync all expired published events to ``ended``.

        Returns (ended_count, scanned_count).
        """
        clock_tz = resolve_lifecycle_clock_tz(client_tz)
        events = self._dao.find_by_status("published")
        scanned_count = len(events)
        ended_count = 0
        for ev in events:
            updated = self._sync_expired_published_event(ev, clock_tz)
            if ev.status == "published" and updated.status == "ended":
                ended_count += 1
        return ended_count, scanned_count

    def create_event(
        self, req: CreateEventRequest, owner_id: str
    ) -> EventResponse:
        try:
            validate_event_schedule(req.date, req.start_time, req.end_time)
        except ValueError as e:
            return EventResponse(message=str(e), event=None, code=400)

        event = Event(
            title=req.title,
            description=req.description,
            date=req.date,
            start_time=req.start_time,
            end_time=req.end_time,
            location=req.location,
            capacity=req.capacity,
            owner_id=owner_id,
            status=req.status,
        )
        saved = self._dao.insert(event)
        if req.status == "published":
            self._logger.info(
                f"Event {saved.title} created as published by {owner_id}",
                event_id=saved.id,
                user_id=owner_id,
            )
        else:
            self._logger.info(
                f"Draft event {saved.title} created by user {owner_id}",
                event_id=saved.id,
                user_id=owner_id,
            )
        self._logger.info(f"Event {req.title} created by {owner_id} with status {req.status}", event_id=saved.id, user_id=owner_id)
        return EventResponse(
            message="Event created",
            event=self._to_public_event(saved),
            code=201,
        )

    def get_event(
        self,
        event_id: str,
        requester_id: str | None = None,
        client_tz: str | None = None,
    ) -> EventResponse:
        event = self._dao.find_by_id(event_id)
        if event is None:
            return EventResponse(message="Event not found", event=None, code=404)

        clock_tz = resolve_lifecycle_clock_tz(client_tz)
        event = self._sync_expired_published_event(event, clock_tz)

        if not self._can_read_event_detail(event, requester_id):
            return EventResponse(message="Event not found", event=None, code=404)

        return EventResponse(
            message="Success",
            event=self._to_public_event(event),
            code=200,
        )

    def transition(
        self, event_id: str, target_status: str, requester_id: str
    ) -> EventResponse:
        event = self._dao.find_by_id(event_id)
        prev_status = event.status
        if event is None:
            return EventResponse(message="Event not found", event=None, code=404)

        if event.owner_id != requester_id:
            return EventResponse(
                message="Only the event owner can change the event state",
                event=None,
                code=403,
            )

        state = resolve_state(event.status)
        try:
            state.handle_transition(target_status)
        except ValueError as e:
            return EventResponse(message=str(e), event=None, code=400)

        updated = self._persist_transition(event, target_status)
        self._logger.info(f"Event {updated.title} transitioned from {prev_status} to {target_status} by {requester_id}", event_id=updated.id, user_id=requester_id)
        return EventResponse(
            message="Success",
            event=self._to_public_event(updated),
            code=200,
        )

    def list_mine(self, user_id: str, client_tz: str | None = None) -> EventListResponse:
        clock_tz = resolve_lifecycle_clock_tz(client_tz)
        events = self._dao.find_by_owner(user_id)
        synced = [self._sync_expired_published_event(e, clock_tz) for e in events]
        return EventListResponse(
            message="Success",
            events=[self._to_public_event(e) for e in synced],
            code=200,
        )

    def list_published(self, client_tz: str | None = None) -> EventListResponse:
        clock_tz = resolve_lifecycle_clock_tz(client_tz)
        events = self._dao.find_by_status("published")
        synced = [self._sync_expired_published_event(e, clock_tz) for e in events]
        live = [e for e in synced if e.status == "published"]
        return EventListResponse(
            message="Success",
            events=[self._to_public_event(e) for e in live],
            code=200,
        )

    def update_event(
        self, event_id: str, req: UpdateEventRequest, user_id: str
    ) -> EventResponse:
        event = self._dao.find_by_id(event_id)
        if event is None:
            return EventResponse(message="Event not found", event=None, code=404)
        is_owner = event.owner_id == user_id
        if event.owner_id != user_id:
            return EventResponse(
                message="Only the event owner can update this event",
                event=None,
                code=403,
            )
        state = resolve_state(event.status)
        try:
            state.validate_edit_event(is_owner)
        except ValueError as e:
            return EventResponse(message=str(e), event=None, code=400)

        data = req.model_dump(exclude_unset=True)
        target_status = data.pop("status", None)
        if target_status is None:
            target_status = event.status

        if target_status != event.status:
            state = resolve_state(event.status)
            try:
                state.handle_transition(target_status)
            except ValueError as e:
                return EventResponse(message=str(e), event=None, code=400)

        merged_date = data.get("date", event.date)
        merged_start = data.get("start_time", event.start_time)
        merged_end = data.get("end_time", event.end_time)
        try:
            validate_event_schedule(merged_date, merged_start, merged_end)
        except ValueError as e:
            return EventResponse(message=str(e), event=None, code=400)

        updates: dict = {}
        field_map = (
            ("title", "title"),
            ("description", "description"),
            ("date", "date"),
            ("start_time", "start_time"),
            ("end_time", "end_time"),
            ("location", "location"),
            ("capacity", "capacity"),
        )
        for key, mongo_key in field_map:
            if key in data:
                updates[mongo_key] = data[key]
        if target_status != event.status:
            updates["status"] = target_status

        updated = self._dao.update_fields(event_id, updates)
        self._logger.info(f"Draft event {updated.title} updated by user {user_id}", event_id=event_id, user_id=user_id)
        return EventResponse(
            message="Success",
            event=self._to_public_event(updated),
            code=200,
        )

    def delete_event(self, event_id: str, user_id: str) -> EventResponse:
        event = self._dao.find_by_id(event_id)
        if event is None:
            return EventResponse(message="Event not found", event=None, code=404)
        is_owner = event.owner_id == user_id
        if event.owner_id != user_id:
            return EventResponse(
                message="Only the event owner can delete this event",
                event=None,
                code=403,
            )
        state = resolve_state(event.status)
        try:
            state.validate_delete_event(is_owner)
        except ValueError as e:
            return EventResponse(message=str(e), event=None, code=400)
        self._dao.delete_by_id(event_id)
        self._logger.info(f"Draft event {event.title} deleted by user {user_id}", event_id=event_id, user_id=user_id)
        return EventResponse(message="Event deleted", event=None, code=200)
