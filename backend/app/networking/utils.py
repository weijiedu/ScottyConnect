"""
Networking Utilities
Helps with timezone conversions and formatting to ensure consistency across the module.
"""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from typing import Tuple

# Default system timezone for display and day-boundary calculation.
LA_TZ = ZoneInfo("America/Los_Angeles")


def get_la_day_boundaries_in_utc(dt: datetime) -> Tuple[datetime, datetime]:
    """
    Calculates the UTC boundaries (start and end) for the LA-local day of the given datetime.
    Used for daily quota enforcement.
    """
    # 1. Convert input to LA context to identify the "local day"
    la_dt = dt.astimezone(LA_TZ)
    
    # 2. Get local midnight and local 11:59 PM
    start_la = datetime.combine(la_dt.date(), time.min).replace(tzinfo=LA_TZ)
    end_la = datetime.combine(la_dt.date(), time.max).replace(tzinfo=LA_TZ)
    
    # 3. Convert those boundaries back to UTC for DB queries
    return start_la.astimezone(timezone.utc), end_la.astimezone(timezone.utc)


def format_to_la_display(dt: datetime) -> str:
    """
    Formats a UTC datetime into a human-readable LA local string.
    Example: "Mon, Apr 20 @ 4:00 PM"
    """
    # Ensure dt is aware before conversion
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        
    la_time = dt.astimezone(LA_TZ)
    return la_time.strftime("%a, %b %d @ %I:%M %p").replace(" 0", " ")
