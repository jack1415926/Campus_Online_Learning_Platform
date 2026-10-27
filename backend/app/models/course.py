"""Course and Chapter models (CM-01 through CM-07).

Course: basic info, category, tags, difficulty, publish workflow.
Chapter: ordered content units with mixed media types and unlock conditions.
"""

import enum

from sqlalchemy import (
    CHAR,
    Boolean,
    Column,
    Enum,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey
from app.models.category import Tag  # noqa: F401 - needed for relationship

# Many-to-many: Course <-> Tag
course_tags = Table(
    "course_tags",
    Base.metadata,
    Column("course_id", CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", CHAR(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class CourseStatus(str, enum.Enum):
    """Course publish workflow states (CM-04)."""
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
    """Chapter content types (CM-02)."""
    video = "video"
    document = "document"
    text = "text"
    image = "image"
    scorm = "scorm"


class Course(Base, UUIDPrimaryKey, TimestampMixin):
    """A course with metadata, category, tags, and chapters (CM-01)."""

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
    version: Mapped[int] = mapped_column(Integer, default=1)
    completion_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    certificate_exam_id: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    category: Mapped["Category | None"] = relationship(
        "Category", back_populates="courses"
    )
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=course_tags, back_populates="courses"
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        "Chapter",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Chapter.sort_order",
    )


class Chapter(Base, UUIDPrimaryKey, TimestampMixin):
    """A course chapter with content reference and unlock conditions (CM-02, CM-03)."""

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
    unlock_condition: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    course: Mapped["Course"] = relationship("Course", back_populates="chapters")
