# backend/app/lifecycle/schemas.py
"""
Schemas for the Lifecycle service.
"""
from typing import Literal

from pydantic import BaseModel


class CreateEventRequest(BaseModel):
    title: str
    description: str
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    capacity: int | None = None
    status: Literal["draft", "published"] = "draft"


class UpdateEventRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    capacity: int | None = None
    status: Literal["draft", "published"] | None = None


class TransitionRequest(BaseModel):
    target_status: str


class PublicEvent(BaseModel):
    id: str | None
    title: str
    description: str
    date: str | None
    start_time: str | None
    end_time: str | None
    location: str | None
    capacity: int | None
    owner_id: str
    status: str
    created_at: str
    updated_at: str


class EventResponse(BaseModel):
    message: str
    event: PublicEvent | None
    code: int


class EventListResponse(BaseModel):
    message: str
    events: list[PublicEvent]
    code: int


class SyncExpiredResponse(BaseModel):
    scanned: int
    ended: int
