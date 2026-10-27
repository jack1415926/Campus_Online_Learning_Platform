"""Learning management models (LM-01 through LM-09).

TrainingPlan: training project with target audience and course list.
LearningPath: structured course sequence by job/level.
CourseAssignment: assigns courses to users/departments.
LearningRecord: tracks per-chapter learning progress.
"""

import enum

from sqlalchemy import (
    CHAR, Boolean, Column, Enum, ForeignKey, Integer, JSON,
    String, Table, Text, Float, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey

# Many-to-many: TrainingPlan <-> Course
plan_courses = Table(
    "plan_courses",
    Base.metadata,
    Column("plan_id", CHAR(36), ForeignKey("training_plans.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
)

# Many-to-many: LearningPath <-> Course (with order and required flag)
path_courses = Table(
    "path_courses",
    Base.metadata,
    Column("path_id", CHAR(36), ForeignKey("learning_paths.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("sort_order", Integer, default=0),
    Column("is_required", Boolean, default=True),
)


class AssignmentType(str, enum.Enum):
    user = "user"
    department = "department"
    user_group = "user_group"
    job_level = "job_level"
    position = "position"


class CompletionStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"


class TrainingPlan(Base, UUIDPrimaryKey, TimestampMixin):
    """A training project with target audience and course list (LM-01)."""

    __tablename__ = "training_plans"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. {"departments": [...], "job_levels": [...], "positions": [...]}
    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completion_requirement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. {"min_minutes": 120, "must_pass_exam": true, "pass_score": 60}
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)

    courses: Mapped[list] = relationship("Course", secondary=plan_courses, )


class LearningPath(Base, UUIDPrimaryKey, TimestampMixin):
    """Structured course sequence by job/level (LM-02)."""

    __tablename__ = "learning_paths"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_job_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deadline_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)

    courses: Mapped[list] = relationship("Course", secondary=path_courses, )


class CourseAssignment(Base, UUIDPrimaryKey, TimestampMixin):
    """Assigns a course to users/departments/levels (LM-03)."""

    __tablename__ = "course_assignments"
    __table_args__ = (UniqueConstraint("course_id", "assignment_type", "target_id", name="uq_course_assignment_target"),)

    course_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType, name="assignment_type"),
    )
    target_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # user_id, department_id, job_level value, or position name
    deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    training_plan_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("training_plans.id", ondelete="SET NULL"), nullable=True
    )
    assigned_by: Mapped[str | None] = mapped_column(CHAR(36), nullable=True)

    course: Mapped["Course"] = relationship("Course", )


class LearningRecord(Base, UUIDPrimaryKey, TimestampMixin):
    """Per-chapter learning progress tracking (LM-04, LM-05)."""

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
    # LM-05: resume position
    resume_position: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. {"video_time": 120, "page": 3}
    status: Mapped[CompletionStatus] = mapped_column(
        Enum(CompletionStatus, name="completion_status"),
        default=CompletionStatus.not_started,
    )
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_accessed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # LM-07 partial: minimum watch time validation
    min_watch_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
