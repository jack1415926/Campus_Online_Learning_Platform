"""Course management service (CM-01 through CM-07)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.category import Tag
from app.models.course import Chapter, Course, CourseStatus
from app.models.exam import Exam
from app.models.media import MediaAsset
from app.schemas.course import (
    ChapterCreate,
    CourseCreate,
    CourseListFilter,
    CourseUpdate,
    PublishAction,
)
from app.schemas.category import TagResponse


class CourseService:

    @staticmethod
    def list_courses(
        db: Session,
        filt: CourseListFilter | None = None,
        page: int = 1,
        page_size: int = 20,
        course_ids: list[str] | None = None,
    ) -> tuple[list[Course], int]:
        stmt = select(Course)
        if course_ids is not None:
            if not course_ids:
                return [], 0
            stmt = stmt.where(Course.id.in_(course_ids))
        if filt:
            if filt.status:
                stmt = stmt.where(Course.status == filt.status)
            if filt.category_id:
                stmt = stmt.where(Course.category_id == filt.category_id)
            if filt.difficulty:
                stmt = stmt.where(Course.difficulty == filt.difficulty)
            if filt.keyword:
                kw = f"%{filt.keyword}%"
                stmt = stmt.where(Course.title.ilike(kw))
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (db.execute(count_stmt)).scalar() or 0
        stmt = (
            stmt.offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(Course.created_at.desc())
            .options(selectinload(Course.tags))
        )
        result = db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    def get_course(db: Session, course_id: str) -> Course | None:
        result = db.execute(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.tags), selectinload(Course.chapters))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def create_course(
        db: Session, body: CourseCreate, creator_id: str
    ) -> Course:
        course = Course(
            title=body.title,
            description=body.description,
            cover_image_url=body.cover_image_url,
            category_id=body.category_id,
            difficulty=body.difficulty,
            estimated_minutes=body.estimated_minutes,
            instructor=body.instructor,
            status=CourseStatus.draft,
            created_by=creator_id,
            completion_config=body.completion_config,
        )
        db.add(course)
        db.flush()

        if body.completion_config:
            CourseService._apply_exam_links(db, str(course.id), body.completion_config)

        # Attach tags
        if body.tag_ids:
            tags_result = db.execute(
                select(Tag).where(Tag.id.in_(body.tag_ids))
            )
            for t in tags_result.scalars().all():
                course.tags.append(t)

        # Create chapters
        for ch in body.chapters:
            chapter = Chapter(
                course_id=course.id,
                title=ch.title,
                content_type=ch.content_type,
                content_ref_id=ch.content_ref_id,
                text_content=ch.text_content,
                sort_order=ch.sort_order,
                is_required=ch.is_required,
                estimated_minutes=ch.estimated_minutes,
                unlock_condition=ch.unlock_condition,
            )
            db.add(chapter)

        if body.completion_config is not None:
            course.completion_config = body.completion_config
            CourseService._apply_exam_links(db, str(course.id), body.completion_config)

        db.flush()
        return course

    @staticmethod
    def _apply_exam_links(
        db: Session, course_id: str, completion_config: dict | None
    ):
        """Associate exams with a course and set their per-exam max_attempts.

        completion_config format:
            {"exam_mode": "all", "exams": [{"exam_id": "...", "max_attempts": 10}, ...]}
        """
        if not completion_config:
            return
        exam_links = completion_config.get("exams") or []
        linked_ids = []
        for link in exam_links:
            exam_id = link.get("exam_id")
            if not exam_id:
                continue
            linked_ids.append(str(exam_id))
            exam = db.execute(select(Exam).where(Exam.id == exam_id)).scalar_one_or_none()
            if exam:
                exam.course_id = course_id
                attempts = link.get("max_attempts")
                if attempts:
                    exam.max_attempts = int(attempts)
        # Detach exams no longer linked to this course
        if linked_ids:
            stale = db.execute(
                select(Exam).where(Exam.course_id == course_id, ~Exam.id.in_(linked_ids))
            ).scalars().all()
        else:
            stale = db.execute(select(Exam).where(Exam.course_id == course_id)).scalars().all()
        for exam in stale:
            exam.course_id = None
        db.flush()

    @staticmethod
    def update_course(
        db: Session, course: Course, body: CourseUpdate
    ) -> Course:
        data = body.model_dump(exclude_unset=True, exclude={"tag_ids"})
        for k, v in data.items():
            setattr(course, k, v)

        if body.tag_ids is not None:
            course.tags.clear()
            db.flush()
            tags_result = db.execute(
                select(Tag).where(Tag.id.in_(body.tag_ids))
            )
            for t in tags_result.scalars().all():
                course.tags.append(t)

        db.flush()
        return course

    @staticmethod
    def publish_action(
        db: Session, course: Course, action: str
    ) -> Course:
        """Handle publish workflow transitions (CM-04).

        draft -> pending_review -> published -> archived
        """
        transitions = {
            "submit_review": (CourseStatus.draft, CourseStatus.pending_review),
            "publish": (CourseStatus.pending_review, CourseStatus.published),
            "archive": (CourseStatus.published, CourseStatus.archived),
            "unpublish": (CourseStatus.archived, CourseStatus.draft),
        }
        if action not in transitions:
            raise ValueError(f"Unknown action: {action}")
        from_state, to_state = transitions[action]
        if course.status != from_state:
            raise ValueError(
                f"Cannot {action}: current status is {course.status.value}, "
                f"expected {from_state.value}"
            )
        course.status = to_state
        db.flush()
        return course

    @staticmethod
    def delete_course(db: Session, course: Course) -> None:
        db.delete(course)
        db.flush()