"""Learning management API."""


from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.core import campus_access as access
from app.models.course import Chapter, CourseStatus
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.course import Course
from app.models.learning import CourseAssignment
from app.models.user import User
from app.schemas.learning import CourseAssignmentResponse, CourseProgressResponse, LearningRecordResponse, ProgressUpdateRequest
from app.services.learning_service import AssignmentService, LearningRecordService

def learning_access(request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    if not access.roles_for(db, user):
        raise HTTPException(403, "账号尚未获得校园角色")


router = APIRouter(prefix="/learning", tags=["learning"], dependencies=[Depends(learning_access)])


@router.get("/my-assignments", response_model=list[CourseAssignmentResponse])
def get_my_assignments(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get courses assigned to the current user."""
    return AssignmentService.get_user_assignments(db, requester)


# --- Learning Records & Progress ---

@router.post("/progress", response_model=LearningRecordResponse)
def update_progress(body: ProgressUpdateRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """update learning progress. Works for both PC and mobile."""
    db.scalar(select(Course).where(Course.id == body.course_id).with_for_update().execution_options(populate_existing=True))
    course = access.get_course(db, requester, body.course_id, learn=True)
    if "student" not in access.roles_for(db, requester) or course.status != CourseStatus.published:
        raise HTTPException(403, "仅已加入的学生可更新已发布课程的学习记录")
    chapter = db.get(Chapter, body.chapter_id) if body.chapter_id else None
    if chapter is None or str(chapter.course_id) != body.course_id:
        raise HTTPException(422, "章节不属于该课程")
    record = LearningRecordService.update_progress(db, requester.id, body)
    db.commit()
    return record


@router.get("/progress/{course_id}", response_model=CourseProgressResponse)
def get_course_progress(course_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """get aggregated course progress."""
    access.get_course(db, requester, course_id, learn=True)
    return LearningRecordService.get_course_progress(db, requester.id, course_id)


@router.get("/records", response_model=list[LearningRecordResponse])
def get_my_records(course_id: str | None = Query(None), requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get learning records for the current user."""
    if course_id:
        access.get_course(db, requester, course_id, learn=True)
    return LearningRecordService.get_user_records(db, requester.id, course_id)


@router.get("/courses/{course_id}/students")
def course_students(course_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from app.models.learning import AssignmentType
    from app.models.homework import Homework, HomeworkSubmission
    from app.models.exam import ExamRecord, Exam, ExamStatus
    access.get_course(db, requester, course_id, manage=True)
    stmt = select(User).join(CourseAssignment, CourseAssignment.target_id == User.id).where(CourseAssignment.course_id == course_id, CourseAssignment.assignment_type == AssignmentType.user)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = []
    homework_total = db.scalar(select(func.count()).select_from(Homework).where(Homework.course_id == course_id))
    for user in db.scalars(stmt.order_by(User.full_name, User.id).offset((page-1)*page_size).limit(page_size)):
        progress = LearningRecordService.get_course_progress(db, str(user.id), course_id)
        submissions = db.scalars(select(HomeworkSubmission).join(Homework, Homework.id == HomeworkSubmission.homework_id).where(Homework.course_id == course_id, HomeworkSubmission.user_id == user.id)).all()
        exam_results = db.execute(select(ExamRecord, Exam.title).join(Exam, Exam.id == ExamRecord.exam_id).where(Exam.course_id == course_id, ExamRecord.user_id == user.id, ExamRecord.status == ExamStatus.graded).order_by(ExamRecord.created_at, ExamRecord.id)).all()
        items.append({"user_id": str(user.id), "full_name": user.full_name, "overall_percent": progress["overall_percent"], "completed_chapters": progress["completed_chapters"], "total_chapters": progress["total_chapters"], "homework_total": homework_total, "submitted": len(submissions), "graded": sum(s.graded_at is not None for s in submissions), "exam_results": [{"exam_id": str(r.exam_id), "title": title, "attempt_number": r.attempt_number, "total_score": r.total_score, "max_score": r.max_score, "is_pass": r.is_pass} for r,title in exam_results]})
    return {"items": items, "meta": {"total": total, "page": page, "page_size": page_size}}


@router.get("/resume/{course_id}", response_model=LearningRecordResponse | None)
def get_resume_position(course_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """get last learning position for resume."""
    access.get_course(db, requester, course_id, learn=True)
    record = LearningRecordService.get_resume_position(db, requester.id, course_id)
    return record
