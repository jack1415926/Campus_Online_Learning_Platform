"""Course topics, one-level replies and private teacher/student messages."""
from datetime import datetime, timezone

from sqlalchemy import CHAR, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DiscussionTopic(Base, UUIDPrimaryKey):
    __tablename__ = "discussion_topics"
    course_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("courses.id"), index=True)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)


class DiscussionReply(Base, UUIDPrimaryKey):
    __tablename__ = "discussion_replies"
    topic_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("discussion_topics.id"), index=True)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)


class PrivateMessage(Base, UUIDPrimaryKey):
    __tablename__ = "private_messages"
    course_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("courses.id"), index=True)
    sender_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), index=True)
    recipient_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), default=utc_now)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
