"""Course management API (CM-01 through CM-07)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.course import Chapter, Course, CourseStatus, Difficulty
from app.models.user import User
from app.schemas.common import PageMeta, PageResponse
from app.schemas.course import (
    ChapterCreate, ChapterResponse, ChapterUpdate,
    CourseCreate, CourseDetailResponse, CourseListFilter,
    CourseResponse, CourseUpdate, PublishAction,
)
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])


def _check_perm(db: Session, user: User, *perms: str):
    user_perms = load_user_permissions(db, user.id)
    if not any(p in user_perms for p in perms):
        raise HTTPException(403, f"Requires permission: {', '.join(perms)}")


def _course_to_response(course: Course) -> dict:
    data = {}
    for k in CourseResponse.model_fields:
        if k == "tag_ids":
            continue
        data[k] = getattr(course, k)
    data["tag_ids"] = [str(t.id) for t in course.tags]
    return data


@router.get("", response_model=PageResponse[CourseResponse])
def list_courses(
    course_status: CourseStatus | None = Query(None, alias="status"),
    category_id: str | None = Query(None),
    difficulty: Difficulty | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filt = CourseListFilter(status=course_status, category_id=category_id, difficulty=difficulty, keyword=keyword)
    user_perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_CREATE not in user_perms:
        # Learners: only see published courses assigned to them
        from app.services.learning_service import AssignmentService
        filt.status = CourseStatus.published
        assignments = AssignmentService.get_user_assignments(db, requester)
        assigned_course_ids = list(set(str(a.course_id) for a in assignments))
        courses, total = CourseService.list_courses(db, filt, page, page_size, course_ids=assigned_course_ids)
    else:
        courses, total = CourseService.list_courses(db, filt, page, page_size)
    return PageResponse(
        items=[CourseResponse(**_course_to_response(c)) for c in courses],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course(
    course_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = CourseService.get_course(db, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    # Learners can only access published courses assigned to them
    user_perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_CREATE not in user_perms:
        if course.status != CourseStatus.published:
            raise HTTPException(403, "Course not available")
        from app.services.learning_service import AssignmentService
        assignments = AssignmentService.get_user_assignments(db, requester)
        assigned_ids = set(str(a.course_id) for a in assignments)
        if str(course.id) not in assigned_ids:
            raise HTTPException(403, "Course not assigned to you")
    data = _course_to_response(course)
    data["chapters"] = [ChapterResponse.model_validate(ch) for ch in course.chapters]
    return CourseDetailResponse(**data)


@router.post("", response_model=CourseDetailResponse, status_code=201)
def create_course(
    body: CourseCreate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_CREATE)
    course = CourseService.create_course(db, body, requester.id)
    db.commit()
    course = CourseService.get_course(db, course.id)
    data = _course_to_response(course)
    data["chapters"] = [ChapterResponse.model_validate(ch) for ch in course.chapters]
    return CourseDetailResponse(**data)


@router.put("/{course_id}", response_model=CourseDetailResponse)
def update_course(
    course_id: str,
    body: CourseUpdate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_UPDATE)
    course = CourseService.get_course(db, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    CourseService.update_course(db, course, body)
    db.commit()
    course = CourseService.get_course(db, course.id)
    data = _course_to_response(course)
    data["chapters"] = [ChapterResponse.model_validate(ch) for ch in course.chapters]
    return CourseDetailResponse(**data)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_DELETE)
    course = CourseService.get_course(db, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    CourseService.delete_course(db, course)
    db.commit()


@router.post("/{course_id}/publish", response_model=CourseResponse)
def publish_action(
    course_id: str,
    body: PublishAction,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_PUBLISH)
    course = CourseService.get_course(db, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    try:
        course = CourseService.publish_action(db, course, body.action)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return CourseResponse(**_course_to_response(course))


@router.post("/{course_id}/chapters", response_model=ChapterResponse, status_code=201)
def add_chapter(
    course_id: str,
    body: ChapterCreate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_UPDATE)
    course = CourseService.get_course(db, course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    chapter = Chapter(
        course_id=course_id,
        title=body.title, content_type=body.content_type,
        content_ref_id=body.content_ref_id, text_content=body.text_content,
        sort_order=body.sort_order, is_required=body.is_required,
        estimated_minutes=body.estimated_minutes, unlock_condition=body.unlock_condition,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.put("/{course_id}/chapters/{chapter_id}", response_model=ChapterResponse)
def update_chapter(
    course_id: str,
    chapter_id: str,
    body: ChapterUpdate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_UPDATE)
    chapter = (db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.course_id == course_id)
    )).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(chapter, k, v)
    db.commit()
    db.refresh(chapter)
    return chapter


@router.delete("/{course_id}/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(
    course_id: str,
    chapter_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_UPDATE)
    chapter = (db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.course_id == course_id)
    )).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    db.delete(chapter)
    db.commit()