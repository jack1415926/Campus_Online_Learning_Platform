"""Schemas for notifications (NTF-01 through NTF-04)."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.notification import (
    NotificationChannel, NotificationStatus, NotificationType,
)


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    notification_type: NotificationType
    title: str
    body: str
    channel: NotificationChannel
    status: NotificationStatus
    is_read: bool
    sent_at: str | None = None
    extra_data: dict[str,str] | None = None
    created_at: datetime
    model_config = {"from_attributes": True}

    @field_validator("extra_data",mode="before")
    @classmethod
    def routing_context(cls,value):
        if not isinstance(value,dict):
            return None
        return {key:value[key] for key in ("course_id","topic_id","peer_id") if isinstance(value.get(key),str)}


class MarkReadRequest(BaseModel):
    notification_ids: list[str] = []
