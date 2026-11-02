"""Learning management service (LM-01 through LM-09)."""

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.course import Chapter, Course, CourseStatus
from app.models.exam import Exam, ExamRecord
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

        # Notify the learner.
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
        learner = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        learner_name = learner.full_name if learner else user_id
        NotificationService.notify_users(
            db, list(admin_user_ids), NotificationType.course_reminder,
            "学员完成课程",
            f"学员 {learner_name} 已完成课程《{course_title}》。",
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

        course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
        # Required exams for completion (from course completion_config)
        exam_links = []
        if course and course.completion_config:
            exam_links = course.completion_config.get("exams") or []

        # Determine exam status for each linked exam
        exams_status = []
        chapters_done = completed == total_chapters and total_chapters > 0
        if exam_links:
            for link in exam_links:
                exam_id = link.get("exam_id")
                exam = db.execute(select(Exam).where(Exam.id == exam_id)).scalar_one_or_none()
                if not exam:
                    continue
                passed = db.execute(
                    select(func.count()).select_from(
                        select(ExamRecord).where(
                            ExamRecord.user_id == user_id,
                            ExamRecord.exam_id == exam_id,
                            ExamRecord.is_pass == True,  # noqa: E712
                        ).subquery()
                    )
                ).scalar() or 0
                attempts = db.execute(
                    select(func.count()).select_from(
                        select(ExamRecord).where(
                            ExamRecord.user_id == user_id,
                            ExamRecord.exam_id == exam_id,
                        ).subquery()
                    )
                ).scalar() or 0
                max_attempts = link.get("max_attempts") or exam.max_attempts or 10
                exams_status.append({
                    "exam_id": str(exam.id),
                    "title": exam.title,
                    "passed": passed > 0,
                    "attempts": attempts,
                    "max_attempts": max_attempts,
                    "remaining": max(0, max_attempts - attempts),
                })
            all_exams_passed = all(e["passed"] for e in exams_status)
        else:
            all_exams_passed = True

        # Learning completion is separate from exam results and certificate eligibility.
        exam_required = bool(exam_links)
        can_take_exam = chapters_done
        is_complete = chapters_done

        if is_complete:
            status = CompletionStatus.completed
        elif chapters_done:
            # Chapters finished but exams not all passed yet -> still in progress
            status = CompletionStatus.in_progress
        else:
            status = CompletionStatus.in_progress if records else CompletionStatus.not_started

        return {
            "course_id": course_id, "total_chapters": total_chapters,
            "completed_chapters": completed, "overall_percent": round(overall, 1),
            "total_learning_seconds": total_seconds, "status": status, "is_complete": is_complete,
            "exam_required": exam_required, "can_take_exam": can_take_exam,
            "all_exams_passed": all_exams_passed, "exams": exams_status,
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

    @staticmethod
    def reset_progress(db: Session, user_id: str, course_id: str):
        """Reset learning progress so the user can re-learn.

        Deletes chapter learning records and resets exam attempts for the
        course's required exams, so the user must re-study and re-take the
        exams. Previous exam records are removed (kept only as-is when the
        learner re-attempts after re-learning).
        """
        db.execute(
            delete(LearningRecord).where(
                LearningRecord.user_id == user_id, LearningRecord.course_id == course_id,
            )
        )
        # Reset exam attempts for required exams linked to this course
        course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
        exam_ids = []
        if course and course.completion_config:
            exam_ids = [link.get("exam_id") for link in (course.completion_config.get("exams") or []) if link.get("exam_id")]
        if exam_ids:
            db.execute(
                delete(ExamRecord).where(
                    ExamRecord.user_id == user_id, ExamRecord.exam_id.in_(exam_ids)
                )
            )
        db.flush()
