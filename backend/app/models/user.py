"""User model for campus accounts."""

import enum
from datetime import datetime

from sqlalchemy import CHAR, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class User(Base, UUIDPrimaryKey, TimestampMixin):
    """Platform user. Authenticates via username and password."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_role: Mapped[str] = mapped_column(String(20), default="student", server_default="student")
    teacher_review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    teacher_review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_reviewed_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    teacher_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.active,
    )


    role_assignments: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
