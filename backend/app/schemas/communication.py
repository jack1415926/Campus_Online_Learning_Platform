from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MessageWrite(BaseModel):
    model_config = {"extra": "forbid"}
    body: str = Field(min_length=1, max_length=20000)

    @field_validator("body")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("内容不能为空")
        return value.strip()


class TopicWrite(MessageWrite):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value):
        if not value.strip():
            raise ValueError("标题不能为空")
        return value.strip()


class PrivateMessageWrite(MessageWrite):
    recipient_id: UUID
