# backend/app/accounts/schemas.py
"""
Schemas for the Accounts service.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, field_validator


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    ALUMNI = "ALUMNI"


# Register request schema
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str
    role: UserRole  # Now required and validated

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v):
        if isinstance(v, str):
            try:
                return UserRole(v)
            except ValueError:
                raise ValueError(f"Invalid role: {v}. Must be one of {[r.value for r in UserRole]}")
        return v

# Verify request schema
class VerifyRequest(BaseModel):
    email: str
    code: str

# Login request schema
class LoginRequest(BaseModel):
    username: str
    password: str


# Public user schema (used for response, hide sensitive information)
class PublicUser(BaseModel):
    id: str | None
    username: str
    email: str
    verified: bool
    role: UserRole
    bio: str = ""
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


# Update profile request schema
class UpdateProfileRequest(BaseModel):
    user_id: str
    bio: str
    tags: list[str]

# Register response schema
class RegisterResponse(BaseModel):
    message: str
    user: PublicUser | None
    code: int

# Verify response schema
class VerifyResponse(BaseModel):
    message: str
    user: PublicUser | None
    token: str | None
    code: int

# Login response schema
class LoginResponse(BaseModel):
    message: str
    user: PublicUser | None
    token: str | None 
    code: int

