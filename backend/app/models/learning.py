"""Campus course membership and per-chapter progress."""
import enum

from sqlalchemy import CHAR, Boolean, Enum, ForeignKey, Integer, JSON, String, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey

class AssignmentType(str, enum.Enum):
    user = "user"


class CompletionStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"


class CourseAssignment(Base, UUIDPrimaryKey, TimestampMixin):
    """Student membership in a course."""

    __tablename__ = "course_assignments"
    __table_args__ = (UniqueConstraint("course_id", "assignment_type", "target_id", name="uq_course_assignment_target"),)

    course_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType, name="assignment_type"),
    )
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Student user ID
    deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)

    course: Mapped["Course"] = relationship("Course", )


class LearningRecord(Base, UUIDPrimaryKey, TimestampMixin):
    """Per-chapter learning progress tracking."""

    __tablename__ = "learning_records"
    __table_args__ = (UniqueConstraint("user_id", "course_id", "chapter_id", name="uq_learning_user_chapter"),)

    user_id: Mapped[str] = mapped_column(CHAR(36), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_id: Mapped[str | None] = mapped_column(CHAR(36), nullable=True, index=True)
    # Progress tracking
    learning_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resume_position: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. {"video_time": 120, "page": 3}
    status: Mapped[CompletionStatus] = mapped_column(
        Enum(CompletionStatus, name="completion_status"),
        default=CompletionStatus.not_started,
    )
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_accessed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
