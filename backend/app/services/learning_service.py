"""Learning management service."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Chapter, Course, CourseStatus
from app.models.learning import AssignmentType, CompletionStatus, CourseAssignment, LearningRecord
from app.models.notification import Notification, NotificationType
from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.learning import ProgressUpdateRequest
from app.services.notification_service import NotificationService


class AssignmentService:

    @staticmethod
    def resolve_target_users(db: Session, assignment: CourseAssignment) -> list[User]:
        """Resolve the concrete users who receive an assignment."""
        if assignment.assignment_type != AssignmentType.user:
            return []
        return list(db.scalars(select(User).where(User.id == assignment.target_id)))

    @staticmethod
    def get_user_assignments(db: Session, user: User):
        stmt = select(CourseAssignment, Course.title).join(Course, Course.id == CourseAssignment.course_id).where(
            CourseAssignment.assignment_type == AssignmentType.user, CourseAssignment.target_id == str(user.id),
            Course.status.in_([CourseStatus.published, CourseStatus.archived]),
        )
        assignments = []
        for assignment, title in db.execute(stmt):
            assignment.course_title = title
            assignments.append(assignment)
        return assignments


class LearningRecordService:

    @staticmethod
    def update_progress(db: Session, user_id: str, body: ProgressUpdateRequest):
        # Serialize progress and completion notifications with course transitions.
        db.execute(select(Course.id).where(Course.id == body.course_id).with_for_update()).one()
        was_complete = LearningRecordService.get_course_progress(db, user_id, body.course_id, for_update=True)["is_complete"]
        now = datetime.now(timezone.utc).isoformat()
        stmt = select(LearningRecord).where(
            LearningRecord.user_id == user_id,
            LearningRecord.course_id == body.course_id,
        )
        if body.chapter_id:
            stmt = stmt.where(LearningRecord.chapter_id == body.chapter_id)
        else:
            stmt = stmt.where(LearningRecord.chapter_id.is_(None))
        record = db.execute(stmt.with_for_update().execution_options(populate_existing=True)).scalar_one_or_none()
        if not record:
            record = LearningRecord(
                user_id=user_id, course_id=body.course_id,
                chapter_id=body.chapter_id, started_at=now,
                status=CompletionStatus.in_progress,
            )
            db.add(record)
        if record.status != CompletionStatus.completed:
            record.learning_seconds = (record.learning_seconds or 0) + body.learning_seconds
        record.progress_percent = max(record.progress_percent or 0, body.progress_percent)
        record.last_accessed_at = now
        if body.resume_position:
            record.resume_position = body.resume_position
        if body.progress_percent >= 100.0:
            if record.status != CompletionStatus.completed:
                record.status = CompletionStatus.completed
                record.completed_at = now
        db.flush()
        if not was_complete and LearningRecordService.get_course_progress(db, user_id, body.course_id, for_update=True)["is_complete"]:
            LearningRecordService._notify_completion(db, user_id, body.course_id)
        return record

    @staticmethod
    def _notify_completion(db: Session, user_id: str, course_id: str):
        """Send a notification to the user (and admins) when a course is completed."""
        course = db.execute(
            select(Course).where(Course.id == course_id)
        ).scalar_one_or_none()
        course_title = course.title if course else course_id
        event_key = f"learning:{course_id}:{user_id}"
        if db.scalar(select(Notification.id).where(Notification.event_key == event_key)):
            return

        # Notify the student.
        notification = NotificationService.notify_user(
            db, user_id, NotificationType.course_reminder,
            "课程已完成",
            f"恭喜您完成课程《{course_title}》！",
            extra_data={"course_id": course_id},
        )
        notification.event_key = event_key
        db.flush()

        # Notify admins (role code 'admin') so they can track completions.
        admin_user_ids = db.execute(
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code == "admin")
        ).scalars().all()
        student = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        student_name = student.full_name if student else user_id
        NotificationService.notify_users(
            db, list(admin_user_ids), NotificationType.course_reminder,
            "学员完成课程",
            f"学员 {student_name} 已完成课程《{course_title}》。",
            extra_data={"course_id": course_id, "user_id": user_id},
        )

    @staticmethod
    def get_course_progress(db: Session, user_id: str, course_id: str, *, for_update=False):
        chapters = db.execute(
            select(Chapter).where(Chapter.course_id == course_id)
        ).scalars().all()
        chapter_ids = {str(ch.id) for ch in chapters}
        total_chapters = len(chapter_ids)
        record_query = select(LearningRecord).where(
                LearningRecord.user_id == user_id, LearningRecord.course_id == course_id,
                LearningRecord.chapter_id.in_(chapter_ids),
            )
        if for_update:
            record_query = record_query.with_for_update().execution_options(populate_existing=True)
        records = db.scalars(record_query).all()
        completed = len({str(r.chapter_id) for r in records if r.status == CompletionStatus.completed})
        total_seconds = sum(r.learning_seconds for r in records)
        if total_chapters > 0:
            overall = (completed / total_chapters) * 100.0
        elif records:
            overall = max(r.progress_percent for r in records)
        else:
            overall = 0.0

        is_complete = completed == total_chapters and total_chapters > 0
        status = CompletionStatus.completed if is_complete else (CompletionStatus.in_progress if records else CompletionStatus.not_started)

        return {
            "course_id": course_id, "total_chapters": total_chapters,
            "completed_chapters": completed, "overall_percent": round(overall, 1),
            "total_learning_seconds": total_seconds, "status": status, "is_complete": is_complete,
        }

    @staticmethod
    def get_user_records(db: Session, user_id: str, course_id=None):
        stmt = select(LearningRecord).where(LearningRecord.user_id == user_id)
        if course_id:
            stmt = stmt.where(LearningRecord.course_id == course_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_resume_position(db: Session, user_id: str, course_id: str):
        return db.execute(
            select(LearningRecord).join(Chapter, Chapter.id == LearningRecord.chapter_id).where(
                LearningRecord.user_id == user_id, LearningRecord.course_id == course_id,
                Chapter.course_id == course_id,
            ).order_by(LearningRecord.last_accessed_at.desc())
        ).scalars().first()
