"""User-related request/response schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator
from app.schemas.auth import validate_password


class UserResponse(BaseModel):
    """Full user representation for API responses."""

    id: uuid.UUID
    username: str
    email: str
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    status: str
    roles: list[str] = []
    requested_role: str = "student"
    teacher_review_status: str | None = None
    teacher_review_reason: str | None = None
    teacher_reviewed_by: str | None = None
    teacher_reviewed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Partial update for user profile."""

    full_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = Field(None, max_length=500)


class UserCreateRequest(BaseModel):
    """Admin-created user."""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = None
    role_code: Literal["student", "teacher", "admin"] = "student"
    _password_limit = field_validator("password")(validate_password)


class UserGroupFilter(BaseModel):
    status: str | None = None
    keyword: str | None = None  # search name/username
