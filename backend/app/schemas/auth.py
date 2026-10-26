"""Request/response schemas for authentication endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    employee_id: str | None = Field(None, max_length=50)
    phone: str | None = None


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

    model_config = {"from_attributes": True}
