"""Request/response schemas for authentication endpoints."""

import uuid
from typing import Literal
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password(value):
    if len(value.encode("utf-8")) > 72:
        raise ValueError("密码最多 72 个 UTF-8 字节，请缩短密码")
    return value


class RegisterRequest(BaseModel):
    model_config = {"extra": "forbid"}
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    employee_id: str | None = Field(None, max_length=50)
    phone: str | None = None
    role: Literal["student", "teacher"] = "student"
    _password_limit = field_validator("password")(validate_password)


class ChangePasswordRequest(BaseModel):
    model_config = {"extra": "forbid"}
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)
    _password_limit = field_validator("new_password")(validate_password)


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserBrief(BaseModel):
    """Minimal user info embedded in token / used by other modules."""

    id: uuid.UUID
    username: str
    email: str
    full_name: str
    status: str
    permissions: list[str] = []
    roles: list[str] = []
    requested_role: str = "student"
    teacher_review_status: str | None = None
    teacher_review_reason: str | None = None

    model_config = {"from_attributes": True}
