"""Notification and template models (NTF-01 through NTF-04)."""

import enum

from sqlalchemy import Enum, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class NotificationType(str, enum.Enum):
    system = "system"
    course_reminder = "course_reminder"
    exam_reminder = "exam_reminder"
    assignment = "assignment"
    certificate = "certificate"


class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    email = "email"
    wecom = "wecom"  # reserved for Phase 8


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class TriggerMode(str, enum.Enum):
    event = "event"
    scheduled = "scheduled"


class NotificationTemplate(Base, UUIDPrimaryKey, TimestampMixin):
    """Configurable notification template with variable substitution (NTF-03)."""

    __tablename__ = "notification_templates"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), index=True
    )
    title_template: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    channels: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. {"in_app": true, "email": true, "wecom": false}
    trigger_mode: Mapped[TriggerMode] = mapped_column(
        Enum(TriggerMode, name="trigger_mode"), default=TriggerMode.event
    )
    is_active: Mapped[bool] = mapped_column(default=True)


class Notification(Base, UUIDPrimaryKey, TimestampMixin):
    """A notification sent to a user (NTF-01, NTF-02)."""

    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notif_type"), index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notif_channel")
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notif_status"), default=NotificationStatus.sent
    )
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    sent_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Extra context data
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
