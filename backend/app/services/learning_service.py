"""Learning management service (LM-01 through LM-09)."""

from datetime import datetime, timezone

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Chapter, Course, CourseStatus
from app.models.exam import Exam, ExamRecord
from app.models.learning import (
    AssignmentType, CompletionStatus, CourseAssignment, LearningPath,
    LearningRecord, TrainingPlan, plan_courses, path_courses,
)
from app.models.notification import NotificationType
from app.models.role import Role, UserRole
from app.models.user import User
from app.schemas.learning import (
    CourseAssignmentCreate, LearningPathCreate, LearningPathUpdate,
    ProgressUpdateRequest, TrainingPlanCreate, TrainingPlanUpdate,
)
from app.services.notification_service import NotificationService


def _get_plan_course_ids(db: Session, plan_id: str):
    rows = db.execute(select(plan_courses.c.course_id).where(plan_courses.c.plan_id == plan_id)).all()
    return [r[0] for r in rows]


def _set_plan_courses(db: Session, plan_id: str, course_ids: list[str]):
    db.execute(delete(plan_courses).where(plan_courses.c.plan_id == plan_id))
    db.flush()
    for cid in course_ids:
        db.execute(insert(plan_courses).values(plan_id=plan_id, course_id=cid))
    db.flush()


def _get_path_course_ids(db: Session, path_id: str):
    rows = db.execute(select(path_courses.c.course_id).where(path_courses.c.path_id == path_id)).all()
    return [r[0] for r in rows]


def _set_path_courses(db: Session, path_id: str, course_ids: list[str]):
    db.execute(delete(path_courses).where(path_courses.c.path_id == path_id))
    db.flush()
    for cid in course_ids:
        db.execute(insert(path_courses).values(path_id=path_id, course_id=cid))
    db.flush()


class TrainingPlanService:

    @staticmethod
    def list_plans(db: Session, page: int = 1, page_size: int = 20):
        stmt = select(TrainingPlan)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(TrainingPlan.created_at.desc())
        plans = list(db.execute(stmt).scalars().all())
        for p in plans:
            p._course_ids = _get_plan_course_ids(db, p.id)
        return plans, total

    @staticmethod
    def get_plan(db: Session, plan_id: str):
        plan = db.execute(select(TrainingPlan).where(TrainingPlan.id == plan_id)).scalar_one_or_none()
        if plan:
            plan._course_ids = _get_plan_course_ids(db, plan.id)
        return plan

    @staticmethod
    def create_plan(db: Session, body: TrainingPlanCreate, creator_id: str):
        plan = TrainingPlan(
            name=body.name, description=body.description,
            target_audience=body.target_audience, start_date=body.start_date,
            end_date=body.end_date, completion_requirement=body.completion_requirement,
            created_by=creator_id,
        )
        db.add(plan)
        db.flush()
        if body.course_ids:
            _set_plan_courses(db, plan.id, body.course_ids)
        plan._course_ids = body.course_ids
        return plan

    @staticmethod
    def update_plan(db: Session, plan: TrainingPlan, body: TrainingPlanUpdate):
        data = body.model_dump(exclude_unset=True, exclude={"course_ids"})
        for k, v in data.items():
            setattr(plan, k, v)
        db.flush()
        if body.course_ids is not None:
            _set_plan_courses(db, plan.id, body.course_ids)
            plan._course_ids = body.course_ids
        return plan

    @staticmethod
    def delete_plan(db: Session, plan: TrainingPlan):
        db.execute(delete(plan_courses).where(plan_courses.c.plan_id == plan.id))
        db.delete(plan)
        db.flush()


class LearningPathService:

    @staticmethod
    def list_paths(db: Session, page: int = 1, page_size: int = 20):
        stmt = select(LearningPath)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(LearningPath.created_at.desc())
        paths = list(db.execute(stmt).scalars().all())
        for p in paths:
            p._course_ids = _get_path_course_ids(db, p.id)
        return paths, total

    @staticmethod
    def get_path(db: Session, path_id: str):
        path = db.execute(select(LearningPath).where(LearningPath.id == path_id)).scalar_one_or_none()
        if path:
            path._course_ids = _get_path_course_ids(db, path.id)
        return path

    @staticmethod
    def create_path(db: Session, body: LearningPathCreate, creator_id: str):
        path = LearningPath(
            name=body.name, description=body.description,
            target_job_level=body.target_job_level, target_position=body.target_position,
            deadline_days=body.deadline_days, created_by=creator_id,
        )
        db.add(path)
        db.flush()
        if body.course_ids:
            _set_path_courses(db, path.id, body.course_ids)
        path._course_ids = body.course_ids
        return path

    @staticmethod
    def update_path(db: Session, path: LearningPath, body: LearningPathUpdate):
        data = body.model_dump(exclude_unset=True, exclude={"course_ids"})
        for k, v in data.items():
            setattr(path, k, v)
        db.flush()
        if body.course_ids is not None:
            _set_path_courses(db, path.id, body.course_ids)
            path._course_ids = body.course_ids
        return path

    @staticmethod
    def delete_path(db: Session, path: LearningPath):
        db.execute(delete(path_courses).where(path_courses.c.path_id == path.id))
        db.delete(path)
        db.flush()


class AssignmentService:

    @staticmethod
    def resolve_target_users(db: Session, assignment: CourseAssignment) -> list[User]:
        """Resolve the concrete users who receive an assignment."""
        from sqlalchemy import or_
        stmt = select(User)
        atype = assignment.assignment_type
        if atype == AssignmentType.user:
            stmt = stmt.where(User.id == assignment.target_id)
        elif atype == AssignmentType.department:
            stmt = stmt.where(User.department_id == assignment.target_id)
        elif atype == AssignmentType.user_group:
            # Groups are not modeled; fall back to no direct members for now.
            return []
        elif atype == AssignmentType.job_level:
            stmt = stmt.where(User.job_level == assignment.target_id)
        elif atype == AssignmentType.position:
            stmt = stmt.where(User.position == assignment.target_id)
        else:
            return []
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def create_assignment(db: Session, body: CourseAssignmentCreate, assigner_id: str):
        assignment = CourseAssignment(
            course_id=body.course_id, assignment_type=body.assignment_type,
            target_id=body.target_id, deadline=body.deadline,
            is_required=body.is_required, training_plan_id=body.training_plan_id,
            assigned_by=assigner_id,
        )
        db.add(assignment)
        db.flush()

        # Notify the users who receive this assignment (LM-03).
        targets = AssignmentService.resolve_target_users(db, assignment)
        if targets:
            course = db.execute(
                select(Course).where(Course.id == assignment.course_id)
            ).scalar_one_or_none()
            course_title = course.title if course else assignment.course_id
            assigner = db.execute(
                select(User).where(User.id == assigner_id)
            ).scalar_one_or_none()
            assigner_name = assigner.full_name if assigner else "管理员"
            deadline_txt = f"\n完成期限: {assignment.deadline}" if assignment.deadline else ""
            required_txt = "必修" if assignment.is_required else "选修"
            NotificationService.notify_users(
                db, [u.id for u in targets], NotificationType.assignment,
                "课程已分配",
                f"{assigner_name} 为您分配了课程《{course_title}》({required_txt})。"
                f"请前往\"我的课程\"开始学习。{deadline_txt}",
                extra_data={"course_id": assignment.course_id, "assignment_id": assignment.id},
            )
        return assignment

    @staticmethod
    def list_assignments(db: Session, course_id=None, page=1, page_size=20):
        stmt = select(CourseAssignment)
        if course_id:
            stmt = stmt.where(CourseAssignment.course_id == course_id)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size).order_by(CourseAssignment.created_at.desc())
        return list(db.execute(stmt).scalars().all()), total

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
        now = datetime.now(timezone.utc).isoformat()
        stmt = select(LearningRecord).where(
            LearningRecord.user_id == user_id,
            LearningRecord.course_id == body.course_id,
        )
        if body.chapter_id:
            stmt = stmt.where(LearningRecord.chapter_id == body.chapter_id)
        else:
            stmt = stmt.where(LearningRecord.chapter_id.is_(None))
        record = db.execute(stmt).scalar_one_or_none()
        if not record:
            record = LearningRecord(
                user_id=user_id, course_id=body.course_id,
                chapter_id=body.chapter_id, started_at=now,
                status=CompletionStatus.in_progress,
            )
            db.add(record)
        record.learning_seconds = (record.learning_seconds or 0) + body.learning_seconds
        record.progress_percent = max(record.progress_percent or 0, body.progress_percent)
        record.last_accessed_at = now
        if body.resume_position:
            record.resume_position = body.resume_position
        if body.min_watch_seconds:
            record.min_watch_seconds = body.min_watch_seconds
        if body.progress_percent >= 100.0:
            if not record.min_watch_seconds or record.learning_seconds >= record.min_watch_seconds:
                # Mark completed and notify (only once on the transition).
                if record.status != CompletionStatus.completed:
                    record.status = CompletionStatus.completed
                    record.completed_at = now
                    LearningRecordService._notify_completion(db, user_id, body.course_id)
        db.flush()
        return record

    @staticmethod
    def _notify_completion(db: Session, user_id: str, course_id: str):
        """Send a notification to the user (and admins) when a course is completed."""
        course = db.execute(
            select(Course).where(Course.id == course_id)
        ).scalar_one_or_none()
        course_title = course.title if course else course_id

        # Notify the learner.
        NotificationService.notify_user(
            db, user_id, NotificationType.course_reminder,
            "课程已完成",
            f"恭喜您完成课程《{course_title}》！",
            extra_data={"course_id": course_id},
        )

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
    def get_course_progress(db: Session, user_id: str, course_id: str):
        chapters = db.execute(
            select(Chapter).where(Chapter.course_id == course_id)
        ).scalars().all()
        total_chapters = len(chapters)
        records = db.execute(
            select(LearningRecord).where(
                LearningRecord.user_id == user_id, LearningRecord.course_id == course_id,
            )
        ).scalars().all()
        completed = sum(1 for r in records if r.status == CompletionStatus.completed)
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

        # Course is complete when all required chapters are done AND all required exams pass
        exam_required = bool(exam_links)
        can_take_exam = chapters_done
        is_complete = chapters_done and all_exams_passed

        if is_complete:
            status = CompletionStatus.completed
        elif chapters_done:
            # Chapters finished but exams not all passed yet -> still in progress
            status = CompletionStatus.in_progress
        else:
            status = CompletionStatus.in_progress if total_seconds > 0 else CompletionStatus.not_started

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
            select(LearningRecord).where(
                LearningRecord.user_id == user_id, LearningRecord.course_id == course_id,
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
