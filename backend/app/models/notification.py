"""Fixed business-event notifications."""

import enum

from sqlalchemy import Enum, String, Text, JSON, UniqueConstraint
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


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class Notification(Base, UUIDPrimaryKey, TimestampMixin):
    """A notification sent to a user."""

    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("event_key", name="uq_notification_event"),)
    event_key: Mapped[str | None] = mapped_column(String(180), nullable=True)

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
