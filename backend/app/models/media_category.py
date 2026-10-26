"""Media category model for organizing media assets."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class MediaCategory(Base, UUIDPrimaryKey, TimestampMixin):
    """A media library category (e.g. training videos, product docs)."""

    __tablename__ = "media_categories"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
