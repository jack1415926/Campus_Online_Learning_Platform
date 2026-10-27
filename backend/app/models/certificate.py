"""One fixed certificate per student and course, with issue-time display values."""
from datetime import datetime, timezone

from sqlalchemy import CHAR, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class Certificate(Base, UUIDPrimaryKey):
    __tablename__ = "certificates"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_certificate_student_course"),)

    course_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("courses.id"), index=True)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), index=True)
    exam_record_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("exam_records.id"))
    number: Mapped[str] = mapped_column(String(50), unique=True)
    student_name: Mapped[str] = mapped_column(String(100))
    course_title: Mapped[str] = mapped_column(String(255))
    platform_name: Mapped[str] = mapped_column(String(100))
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
