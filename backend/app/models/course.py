"""Course and Chapter models.

Course: basic info, category, difficulty, publish workflow.
Chapter: ordered content units with mixed media types.
"""

import enum

from sqlalchemy import CHAR, Boolean, Enum, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey

class CourseStatus(str, enum.Enum):
    """Course publish workflow states."""
    draft = "draft"
    pending_review = "pending_review"
    published = "published"
    archived = "archived"


class Difficulty(str, enum.Enum):
    """Course difficulty levels."""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ContentType(str, enum.Enum):
    """Chapter content types."""
    video = "video"
    document = "document"
    text = "text"
    image = "image"


class Course(Base, UUIDPrimaryKey, TimestampMixin):
    """A course with metadata, category and chapters."""

    __tablename__ = "courses"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("categories.id"), nullable=True, index=True
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="difficulty"),
        default=Difficulty.beginner,
    )
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0)
    instructor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, name="course_status"),
        default=CourseStatus.draft,
        index=True,
    )
    certificate_exam_id: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="courses"
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Chapter.sort_order",
    )


class Chapter(Base, UUIDPrimaryKey, TimestampMixin):
    """A course chapter with content reference."""

    __tablename__ = "chapters"

    course_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, name="content_type"),
        default=ContentType.video,
    )
    content_ref_id: Mapped[str | None] = mapped_column(
        CHAR(36), nullable=True
    )
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped["Course"] = relationship("Course", back_populates="chapters")
