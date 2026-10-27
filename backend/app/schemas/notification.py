"""Schemas for notifications (NTF-01 through NTF-04)."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.notification import (
    NotificationChannel, NotificationStatus, NotificationType, TriggerMode,
)


class NotificationTemplateBase(BaseModel):
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    notification_type: NotificationType
    title_template: str = Field(..., max_length=500)
    body_template: str
    channels: dict | None = None
    trigger_mode: TriggerMode = TriggerMode.event
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateResponse(NotificationTemplateBase):
    id: str
    created_at: datetime
    model_config = {"from_attributes": True}


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


class SendNotificationRequest(BaseModel):
    """Send a notification to a user (NTF-04 event trigger)."""
    user_id: str
    template_code: str | None = None
    notification_type: NotificationType = NotificationType.system
    title: str | None = None
    body: str | None = None
    channel: NotificationChannel = NotificationChannel.in_app
    variables: dict | None = None
    extra_data: dict | None = None


class MarkReadRequest(BaseModel):
    notification_ids: list[str] = []
