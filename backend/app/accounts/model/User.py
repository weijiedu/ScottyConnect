# Domain shape for a user document (persistence via UserDAO).

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    ALUMNI = "ALUMNI"


class User(BaseModel):
    id: str | None = None
    username: str
    email: str
    password: str
    verification_code: str
    verified: bool = False
    role: UserRole = UserRole.STUDENT  # Now uses enum with default
    bio: str = ""
    tags: list[str] = []
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
