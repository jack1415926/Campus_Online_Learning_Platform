"""Login session model for single sign-on and session timeout."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class SessionStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    expired = "expired"


class Session(Base, UUIDPrimaryKey, TimestampMixin):
    """A user's login session (single sign-on + 2h timeout).

    Each login creates a session. When a user logs in again, all older
    active sessions for that user are revoked (single sign-on), so the
    previously logged-in device is kicked out ("已异地登录").
    """

    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # A random token stored in the JWT's `sid` claim to identify this session.
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    # Client info for display / debugging (device, ip, user-agent).
    client_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), default=SessionStatus.active, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
