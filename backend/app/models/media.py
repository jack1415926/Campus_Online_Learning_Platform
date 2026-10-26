"""Media asset library model (DM-01).

Unified storage for videos, documents, images, audio.
Supports cross-course reuse via content reference.
"""

import enum

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class MediaType(str, enum.Enum):
    video = "video"
    document = "document"
    image = "image"
    audio = "audio"


class MediaAsset(Base, UUIDPrimaryKey, TimestampMixin):
    """A reusable media asset stored in object storage."""

    __tablename__ = "media_assets"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type"),
        index=True,
    )
    # Storage info
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)  # bytes
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Video-specific
    duration: Mapped[int | None] = mapped_column(nullable=True)  # seconds
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)  # e.g. "1080p"
    # Organization
    category_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )  # loose reference, not FK (assets can be uncategorized)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Upload tracking
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="ready")  # ready / processing / failed