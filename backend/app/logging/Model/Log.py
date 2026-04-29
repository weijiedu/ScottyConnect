"""
Persistence Model for logging.
"""

from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Log(BaseModel):
    id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    log_level: LogLevel
    service_name: str | None = None
    user_id: str | None = None
    event_id: str | None = None
    message: str