"""
Validate event date/time: future start, end after start.
Times are interpreted in EVENT_TZ (default America/Los_Angeles) so API rules stay consistent.
"""

import os
from datetime import datetime

from zoneinfo import ZoneInfo


def _event_tz() -> ZoneInfo:
    name = os.getenv("EVENT_TZ", "America/Los_Angeles")
    return ZoneInfo(name)


def resolve_lifecycle_clock_tz(client_tz_name: str | None) -> ZoneInfo:
    """
    Timezone for interpreting stored date + wall-clock times on read paths
    (e.g. auto-end). Prefer the browser's IANA zone when provided; otherwise EVENT_TZ.
    """
    if client_tz_name and client_tz_name.strip():
        try:
            return ZoneInfo(client_tz_name.strip())
        except Exception:
            pass
    return _event_tz()


def parse_event_end_datetime(
    date: str | None,
    end_time: str | None,
    *,
    clock_tz: ZoneInfo | None = None,
) -> datetime | None:
    """
    End instant for ``date`` + ``end_time`` in ``clock_tz`` (default EVENT_TZ),
    or None if missing/invalid. Accepts HH:MM or HH:MM:SS from clients.
    """
    if not date or not end_time:
        return None
    tz = clock_tz if clock_tz is not None else _event_tz()
    combined = f"{date.strip()} {end_time.strip()}"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(combined, fmt).replace(tzinfo=tz)
        except ValueError:
            continue
    return None


def validate_event_schedule(
    date: str | None,
    start_time: str | None,
    end_time: str | None,
) -> None:
    """
    Raises ValueError with a user-facing message if validation fails.
    """
    if not date or not start_time or not end_time:
        raise ValueError("Date, start time, and end time are required.")

    tz = _event_tz()
    try:
        start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M").replace(
            tzinfo=tz
        )
        end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M").replace(
            tzinfo=tz
        )
    except ValueError as e:
        raise ValueError("Invalid date or time format.") from e

    now = datetime.now(tz)
    if end_dt <= start_dt:
        raise ValueError("End time must be after start time.")
    if start_dt <= now:
        raise ValueError("Event start must be in the future.")
