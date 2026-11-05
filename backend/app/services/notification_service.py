"""Notification service."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification, NotificationChannel, NotificationStatus,
    NotificationType,
)


class NotificationService:

    @staticmethod
    def notify_user(db: Session, user_id: str, notification_type: NotificationType,
                    title: str, body: str,
                    channel: NotificationChannel = NotificationChannel.in_app,
                    extra_data: dict | None = None):
        """Create an in-app notification for a single user (used by business events)."""
        if not user_id:
            return None
        notif = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title, body=body,
            channel=channel,
            status=NotificationStatus.sent,
            sent_at=datetime.now(timezone.utc).isoformat(),
            extra_data=extra_data,
        )
        db.add(notif)
        db.flush()
        return notif

    @staticmethod
    def notify_users(db: Session, user_ids: list[str], notification_type: NotificationType,
                     title: str, body: str,
                     channel: NotificationChannel = NotificationChannel.in_app,
                     extra_data: dict | None = None):
        """Create an in-app notification for multiple users (used by business events)."""
        created = []
        for uid in set(filter(None, user_ids)):
            created.append(NotificationService.notify_user(
                db, uid, notification_type, title, body, channel, extra_data,
            ))
        return created


    @staticmethod
    def list_user_notifications(db: Session, user_id: str, unread_only: bool = False,
                                page: int = 1, page_size: int = 20):
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
        stmt = (stmt.offset((page - 1) * page_size).limit(page_size)
                .order_by(Notification.created_at.desc()))
        return list(db.execute(stmt).scalars().all()), total

    @staticmethod
    def mark_read(db: Session, user_id: str, notification_ids: list[str]):
        notifs = db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.id.in_(notification_ids) if notification_ids else True
            )
        ).scalars().all()
        for n in notifs:
            n.is_read = True
        db.flush()
        return len(notifs)

    @staticmethod
    def mark_all_read(db: Session, user_id: str):
        notifs = db.execute(
            select(Notification).where(
                Notification.user_id == user_id, Notification.is_read == False
            )
        ).scalars().all()
        for n in notifs:
            n.is_read = True
        db.flush()
        return len(notifs)

    @staticmethod
    def get_unread_count(db: Session, user_id: str):
        return db.execute(
            select(func.count()).select_from(
                select(Notification).where(
                    Notification.user_id == user_id, Notification.is_read == False
                ).subquery()
            )
        ).scalar() or 0
