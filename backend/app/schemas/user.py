"""User-related request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """Full user representation for API responses."""

    id: uuid.UUID
    username: str
    email: str
    full_name: str
    employee_id: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    department_id: uuid.UUID | None = None
    department_name: str | None = None
    job_level: str | None = None
    position: str | None = None
    hire_date: datetime | None = None
    status: str
    custom_fields: dict | None = None
    roles: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    """Partial update for user profile."""

    full_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None
    job_level: str | None = Field(None, max_length=50)
    position: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
    custom_fields: dict | None = None


class UserCreateRequest(BaseModel):
    """Admin-created user (UM-03 manual user creation)."""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    employee_id: str | None = Field(None, max_length=50)
    phone: str | None = None
    department_id: uuid.UUID | None = None
    department_name: str | None = Field(None, max_length=200)
    job_level: str | None = None
    position: str | None = None
    custom_fields: dict | None = None
    role_code: str | None = None
    data_scope: str = "self"


class UserGroupFilter(BaseModel):
    """Filter criteria for user grouping (UM-04)."""

    department_id: uuid.UUID | None = None
    job_level: str | None = None
    position: str | None = None
    status: str | None = None
    keyword: str | None = None  # search name/username/employee_id
