"""Notification service (NTF-01 through NTF-04)."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification, NotificationChannel, NotificationStatus,
    NotificationTemplate, NotificationType,
)
from app.schemas.notification import SendNotificationRequest


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
    def send(db: Session, body: SendNotificationRequest):
        """Send a notification to a user (NTF-01, NTF-02, NTF-04)."""
        title = body.title
        body_text = body.body

        # Use template if specified (NTF-03)
        if body.template_code:
            tmpl = db.execute(
                select(NotificationTemplate).where(
                    NotificationTemplate.code == body.template_code,
                    NotificationTemplate.is_active == True,
                )
            ).scalar_one_or_none()
            if tmpl:
                title = title or tmpl.title_template
                body_text = body_text or tmpl.body_template
                # Variable substitution (NTF-03)
                if body.variables:
                    for k, v in body.variables.items():
                        title = title.replace("{{" + k + "}}", str(v))
                        body_text = body_text.replace("{{" + k + "}}", str(v))

        if not title or not body_text:
            raise ValueError("Title and body are required")

        notif = Notification(
            user_id=body.user_id,
            notification_type=body.notification_type,
            title=title, body=body_text,
            channel=body.channel,
            status=NotificationStatus.sent,
            sent_at=datetime.now(timezone.utc).isoformat(),
            extra_data=body.extra_data,
        )
        db.add(notif)
        db.flush()

        # NTF-02: email channel (simulated - actual email sending in production)
        # WeComChannel is reserved for Phase 8
        return notif

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


class TemplateService:

    @staticmethod
    def list_templates(db: Session):
        return list(db.execute(
            select(NotificationTemplate).order_by(NotificationTemplate.created_at.desc())
        ).scalars().all())

    @staticmethod
    def create_template(db: Session, code: str, name: str, notification_type: NotificationType,
                        title_template: str, body_template: str, channels=None, trigger_mode=None):
        tmpl = NotificationTemplate(
            code=code, name=name, notification_type=notification_type,
            title_template=title_template, body_template=body_template,
            channels=channels, trigger_mode=trigger_mode,
        )
        db.add(tmpl)
        db.flush()
        return tmpl

    @staticmethod
    def delete_template(db: Session, tmpl: NotificationTemplate):
        db.delete(tmpl)
        db.flush()
