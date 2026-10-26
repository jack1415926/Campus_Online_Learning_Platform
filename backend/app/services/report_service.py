"""Report and analytics service (RPT-01 through RPT-08)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.exam import ExamRecord, ExamStatus
from app.models.learning import (
    CompletionStatus, CourseAssignment, LearningRecord, TrainingPlan,
)
from app.models.notification import Notification
from app.models.user import User, UserStatus


class ReportService:

    @staticmethod
    def personal_report(db: Session, user_id: str):
        """RPT-01: personal learning report."""
        user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            return None

        # Learning records
        records = db.execute(
            select(LearningRecord).where(LearningRecord.user_id == user_id)
        ).scalars().all()
        course_ids = list(set(r.course_id for r in records))
        # Count courses where ALL chapters are completed
        from app.models.course import Chapter
        completed_courses = 0
        for cid in course_ids:
            total_ch = db.execute(
                select(func.count()).select_from(
                    select(Chapter).where(Chapter.course_id == cid).subquery()
                )
            ).scalar() or 0
            completed_ch = sum(1 for r in records if r.course_id == cid and r.status == CompletionStatus.completed)
            if total_ch > 0 and completed_ch >= total_ch:
                completed_courses += 1
        completed = completed_courses
        total_seconds = sum(r.learning_seconds or 0 for r in records)

        # Exam records
        exam_records = db.execute(
            select(ExamRecord).where(
                ExamRecord.user_id == user_id, ExamRecord.status == ExamStatus.graded
            )
        ).scalars().all()
        exam_scores = [r.total_score or 0 for r in exam_records]

        return {
            "user_id": user_id,
            "user_name": user.full_name,
            "total_courses": len(course_ids),
            "completed_courses": completed,
            "total_learning_seconds": total_seconds,
            "completion_rate": round(completed / len(course_ids) * 100, 1) if course_ids else 0.0,
            "exam_count": len(exam_records),
            "exam_average_score": round(sum(exam_scores) / len(exam_scores), 1) if exam_scores else 0.0,
            "certificates": [],
        }

    @staticmethod
    def department_report(db: Session, department_id: str):
        """RPT-02: department report."""
        users = db.execute(
            select(User).where(User.department_id == department_id, User.status == UserStatus.active)
        ).scalars().all()

        if not users:
            return None

        user_ids = [u.id for u in u for u in users]
        total_seconds = 0
        total_completed = 0
        total_courses = 0

        for uid in user_ids:
            records = db.execute(
                select(LearningRecord).where(LearningRecord.user_id == uid)
            ).scalars().all()
            total_seconds += sum(r.learning_seconds or 0 for r in records)
            total_completed += sum(1 for r in records if r.status == CompletionStatus.completed)
            total_courses += len(set(r.course_id for r in records))

        return {
            "department_id": department_id,
            "department_name": "",
            "member_count": len(users),
            "average_learning_seconds": total_seconds // len(users) if users else 0,
            "completion_rate": round(total_completed / total_courses * 100, 1) if total_courses else 0.0,
            "overdue_count": 0,
        }

    @staticmethod
    def course_report(db: Session, course_id: str):
        """RPT-03: course report."""
        course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
        if not course:
            return None

        records = db.execute(
            select(LearningRecord).where(LearningRecord.course_id == course_id)
        ).scalars().all()

        user_ids = list(set(r.user_id for r in records))
        completed = sum(1 for r in records if r.status == CompletionStatus.completed)

        # Exam scores for this course
        exam_scores = []
        if course_id:
            from app.models.exam import Exam
            exams = db.execute(select(Exam).where(Exam.course_id == course_id)).scalars().all()
            for exam in exams:
                ers = db.execute(
                    select(ExamRecord).where(
                        ExamRecord.exam_id == exam.id, ExamRecord.status == ExamStatus.graded
                    )
                ).scalars().all()
                exam_scores.extend([r.total_score or 0 for r in ers])

        return {
            "course_id": course_id,
            "course_title": course.title,
            "enrolled_count": len(user_ids),
            "completed_count": completed,
            "completion_rate": round(completed / len(user_ids) * 100, 1) if user_ids else 0.0,
            "average_score": round(sum(exam_scores) / len(exam_scores), 1) if exam_scores else 0.0,
            "average_rating": course.rating or 0.0,
        }

    @staticmethod
    def training_plan_report(db: Session, plan_id: str):
        """RPT-04: training plan report."""
        plan = db.execute(select(TrainingPlan).where(TrainingPlan.id == plan_id)).scalar_one_or_none()
        if not plan:
            return None

        return {
            "plan_id": plan_id,
            "plan_name": plan.name,
            "total_courses": 0,
            "overall_progress": 0.0,
            "enrolled_count": 0,
            "completed_count": 0,
        }

    @staticmethod
    def compliance_report(db: Session, start_date: str = "", end_date: str = ""):
        """RPT-08: compliance audit report."""
        # Count all users
        total_users = db.execute(
            select(func.count()).select_from(
                select(User).where(User.status == UserStatus.active).subquery()
            )
        ).scalar() or 0

        # Count learning records
        total_records = db.execute(
            select(func.count()).select_from(LearningRecord)
        ).scalar() or 0

        # Count exam records
        total_exams = db.execute(
            select(func.count()).select_from(
                select(ExamRecord).where(ExamRecord.status == ExamStatus.graded).subquery()
            )
        ).scalar() or 0

        # Get sample records for audit
        records = db.execute(
            select(LearningRecord).order_by(LearningRecord.created_at.desc()).limit(100)
        ).scalars().all()

        record_list = []
        for r in records:
            record_list.append({
                "user_id": r.user_id,
                "course_id": r.course_id,
                "learning_seconds": r.learning_seconds,
                "status": r.status.value if r.status else None,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "last_accessed_at": r.last_accessed_at,
            })

        return {
            "period_start": start_date,
            "period_end": end_date,
            "total_users": total_users,
            "total_records": total_records,
            "total_exams": total_exams,
            "records": record_list,
        }
