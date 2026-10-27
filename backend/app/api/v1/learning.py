"""Learning management API (LM-01 through LM-09)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from app.core import campus_access as access
from app.models.course import Chapter, CourseStatus
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.course import Course
from app.models.learning import CourseAssignment, LearningRecord
from app.models.user import User
from app.schemas.common import PageMeta, PageResponse
from app.schemas.learning import (
    CourseAssignmentCreate, CourseAssignmentResponse,
    CourseProgressResponse, LearningPathCreate, LearningPathResponse,
    LearningPathUpdate, LearningRecordResponse, ProgressUpdateRequest,
    TrainingPlanCreate, TrainingPlanResponse, TrainingPlanUpdate,
)
from app.services.learning_service import (
    AssignmentService, LearningPathService, LearningRecordService, TrainingPlanService,
)

def learning_access(request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    if request.url.path.startswith(("/api/v1/learning/plans", "/api/v1/learning/paths", "/api/v1/learning/assignments")):
        access.require_admin(db, user)
    elif not access.roles_for(db, user):
        raise HTTPException(403, "账号尚未获得校园角色")


router = APIRouter(prefix="/learning", tags=["learning"], dependencies=[Depends(learning_access)])


def _check_perm(db: Session, user: User, *perms: str):
    user_perms = load_user_permissions(db, user.id)
    if not any(p in user_perms for p in perms):
        raise HTTPException(403, f"Requires permission: {', '.join(perms)}")


def _to_plan_response(plan):
    data = {k: getattr(plan, k) for k in TrainingPlanResponse.model_fields if k != "course_ids"}
    data["course_ids"] = getattr(plan, "_course_ids", [])
    return TrainingPlanResponse(**data)


def _to_path_response(path):
    data = {k: getattr(path, k) for k in LearningPathResponse.model_fields if k != "course_ids"}
    data["course_ids"] = getattr(path, "_course_ids", [])
    return LearningPathResponse(**data)


# --- Training Plans (LM-01) ---

@router.get("/plans", response_model=PageResponse[TrainingPlanResponse])
def list_plans(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
               requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plans, total = TrainingPlanService.list_plans(db, page, page_size)
    return PageResponse(items=[_to_plan_response(p) for p in plans], meta=PageMeta(page=page, page_size=page_size, total=total))


@router.get("/plans/{plan_id}", response_model=TrainingPlanResponse)
def get_plan(plan_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = TrainingPlanService.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, "Training plan not found")
    return _to_plan_response(plan)


@router.post("/plans", response_model=TrainingPlanResponse, status_code=201)
def create_plan(body: TrainingPlanCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    plan = TrainingPlanService.create_plan(db, body, requester.id)
    db.commit()
    return _to_plan_response(plan)


@router.put("/plans/{plan_id}", response_model=TrainingPlanResponse)
def update_plan(plan_id: str, body: TrainingPlanUpdate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    plan = TrainingPlanService.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, "Training plan not found")
    TrainingPlanService.update_plan(db, plan, body)
    db.commit()
    return _to_plan_response(plan)


@router.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    plan = TrainingPlanService.get_plan(db, plan_id)
    if not plan:
        raise HTTPException(404, "Training plan not found")
    TrainingPlanService.delete_plan(db, plan)
    db.commit()


# --- Learning Paths (LM-02) ---

@router.get("/paths", response_model=PageResponse[LearningPathResponse])
def list_paths(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
               requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    paths, total = LearningPathService.list_paths(db, page, page_size)
    return PageResponse(items=[_to_path_response(p) for p in paths], meta=PageMeta(page=page, page_size=page_size, total=total))


@router.get("/paths/{path_id}", response_model=LearningPathResponse)
def get_path(path_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    path = LearningPathService.get_path(db, path_id)
    if not path:
        raise HTTPException(404, "Learning path not found")
    return _to_path_response(path)


@router.post("/paths", response_model=LearningPathResponse, status_code=201)
def create_path(body: LearningPathCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    path = LearningPathService.create_path(db, body, requester.id)
    db.commit()
    return _to_path_response(path)


@router.put("/paths/{path_id}", response_model=LearningPathResponse)
def update_path(path_id: str, body: LearningPathUpdate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    path = LearningPathService.get_path(db, path_id)
    if not path:
        raise HTTPException(404, "Learning path not found")
    LearningPathService.update_path(db, path, body)
    db.commit()
    return _to_path_response(path)


@router.delete("/paths/{path_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_path(path_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    path = LearningPathService.get_path(db, path_id)
    if not path:
        raise HTTPException(404, "Learning path not found")
    LearningPathService.delete_path(db, path)
    db.commit()


# --- Course Assignment (LM-03) ---

@router.post("/assignments", response_model=CourseAssignmentResponse, status_code=201)
def create_assignment(body: CourseAssignmentCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_ASSIGN)
    assignment = AssignmentService.create_assignment(db, body, requester.id)
    db.commit()
    return assignment


@router.get("/assignments", response_model=PageResponse[CourseAssignmentResponse])
def list_assignments(course_id: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assignments, total = AssignmentService.list_assignments(db, course_id, page, page_size)
    return PageResponse(items=assignments, meta=PageMeta(page=page, page_size=page_size, total=total))


@router.get("/my-assignments", response_model=list[CourseAssignmentResponse])
def get_my_assignments(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get courses assigned to the current user (LM-03)."""
    return AssignmentService.get_user_assignments(db, requester)


# --- Learning Records & Progress (LM-04, LM-05, LM-06, LM-07, LM-08) ---

@router.post("/progress", response_model=LearningRecordResponse)
def update_progress(body: ProgressUpdateRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """LM-04, LM-05: update learning progress. Works for both PC and mobile (LM-06)."""
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
    """LM-04, LM-08: get aggregated course progress."""
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
    """LM-05: get last learning position for resume."""
    access.get_course(db, requester, course_id, learn=True)
    record = LearningRecordService.get_resume_position(db, requester.id, course_id)
    return record


@router.post("/reset/{course_id}", status_code=200)
def reset_course_progress(course_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reset all learning records for a course, allowing re-learning."""
    access.require_admin(db, requester)
    LearningRecordService.reset_progress(db, requester.id, course_id)
    db.commit()
    return {"message": "Progress reset"}
