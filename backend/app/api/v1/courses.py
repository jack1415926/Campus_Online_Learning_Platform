"""Course management API (CM-01 through CM-07)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from datetime import datetime, timezone
from app.core import campus_access as access
from app.models.learning import CourseAssignment, AssignmentType, LearningRecord
from app.models.exam import Exam, ExamRecord
from app.models.media import MediaAsset
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


def _course_to_response(course: Course, db, user) -> dict:
    data = {}
    for k in CourseResponse.model_fields:
        if k in ("tag_ids", "is_enrolled", "can_manage", "can_edit", "can_learn", "cover_preview_url"):
            continue
        data[k] = getattr(course, k)
    data["tag_ids"] = [str(t.id) for t in course.tags]
    data["cover_preview_url"] = course.cover_image_url
    data["can_manage"] = access.can_manage(db, user, course)
    data["can_edit"] = data["can_manage"] and course.status == CourseStatus.draft
    data["is_enrolled"] = str(course.id) in access.enrolled_ids(db, user)
    data["can_learn"] = "student" in access.roles_for(db, user) and data["is_enrolled"] and course.status in (CourseStatus.published, CourseStatus.archived)
    if not data["can_manage"]:
        data["completion_config"] = None
    if course.cover_image_url and course.cover_image_url.startswith("/storage/"):
        asset = db.scalar(select(MediaAsset).where(MediaAsset.storage_key == course.cover_image_url.removeprefix("/storage/")))
        if asset:
            from app.core.media_access import ticket_url
            data["cover_preview_url"] = ticket_url(user, asset)
    return data


def _validate_resources(db, requester, body, course_id=None):
    references = [c.content_ref_id for c in getattr(body, "chapters", []) if c.content_ref_id]
    if getattr(body, "content_ref_id", None):
        references.append(body.content_ref_id)
    for asset_id in references:
        asset = db.get(MediaAsset, asset_id)
        if not asset:
            raise HTTPException(422, "引用的资料不存在")
        access.require_asset_owner(db, requester, asset)
    cover = getattr(body, "cover_image_url", None)
    if cover and cover.startswith("/storage/"):
        asset = db.scalar(select(MediaAsset).where(MediaAsset.storage_key == cover.removeprefix("/storage/")))
        if not asset or asset.media_type.value != "image":
            raise HTTPException(422, "请使用素材库中上传的封面图片")
        access.require_asset_owner(db, requester, asset)
    for link in (getattr(body, "completion_config", None) or {}).get("exams", []):
        exam = db.get(Exam, link.get("exam_id"))
        if not exam or ("admin" not in access.roles_for(db, requester) and str(exam.created_by) != str(requester.id)):
            raise HTTPException(403, "不能关联其他教师的考试")
        if exam.course_id and str(exam.course_id) != course_id:
            raise HTTPException(409, "考试已关联其他课程")


@router.get("", response_model=PageResponse[CourseResponse])
def list_courses(
    course_status: CourseStatus | None = Query(None, alias="status"),
    category_id: str | None = Query(None),
    difficulty: Difficulty | None = Query(None),
    keyword: str | None = Query(None),
    managed: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filt = CourseListFilter(status=course_status, category_id=category_id, difficulty=difficulty, keyword=keyword)
    _check_perm(db, requester, Perm.COURSE_READ)
    roles = access.roles_for(db, requester)
    creator_id = None
    if "admin" not in roles and managed and "teacher" in roles:
        creator_id = str(requester.id)
    elif "admin" not in roles:
        filt.status = CourseStatus.published
    courses, total = CourseService.list_courses(db, filt, page, page_size, creator_id=creator_id)
    return PageResponse(
        items=[CourseResponse(**_course_to_response(c, db, requester)) for c in courses],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course(
    course_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_READ)
    course = access.get_course(db, requester, course_id)
    data = _course_to_response(course, db, requester)
    data["chapters"] = [ChapterResponse.model_validate(ch) for ch in course.chapters]
    if not data["can_manage"] and not data["can_learn"]:
        for chapter in data["chapters"]:
            chapter.text_content = chapter.content_ref_id = chapter.unlock_condition = None
    return CourseDetailResponse(**data)


@router.post("", response_model=CourseDetailResponse, status_code=201)
def create_course(
    body: CourseCreate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_CREATE)
    _validate_resources(db, requester, body)
    body.instructor = requester.full_name
    course = CourseService.create_course(db, body, requester.id)
    db.commit()
    course = CourseService.get_course(db, course.id)
    data = _course_to_response(course, db, requester)
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
    course = access.get_course(db, requester, course_id, manage=True, edit=True)
    if not course:
        raise HTTPException(404, "Course not found")
    _validate_resources(db, requester, body, course_id)
    if "title" in body.model_fields_set and not (body.title or "").strip():
        raise HTTPException(422, "课程标题不能为空")
    if "admin" not in access.roles_for(db, requester):
        body.instructor = requester.full_name
    CourseService.update_course(db, course, body)
    db.commit()
    course = CourseService.get_course(db, course.id)
    data = _course_to_response(course, db, requester)
    data["chapters"] = [ChapterResponse.model_validate(ch) for ch in course.chapters]
    return CourseDetailResponse(**data)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_DELETE)
    course = access.get_course(db, requester, course_id, manage=True, edit=True)
    if not course:
        raise HTTPException(404, "Course not found")
    _ensure_no_activity(db, course_id)
    CourseService.delete_course(db, course)
    db.commit()


@router.post("/{course_id}/publish", response_model=CourseResponse)
def publish_action(
    course_id: str,
    body: PublishAction,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    course = access.get_course(db, requester, course_id, manage=True)
    if not course:
        raise HTTPException(404, "Course not found")
    # Lock the row shared by joins and workflow transitions.
    course = db.scalar(select(Course).where(Course.id == course_id).with_for_update().execution_options(populate_existing=True))
    if body.action != "submit_review":
        access.require_admin(db, requester)
    try:
        if body.action == "submit_review":
            if not course.chapters or not all((ch.text_content or "").strip() if ch.content_type == "text" else bool(ch.content_ref_id) for ch in course.chapters):
                raise ValueError("请至少添加一个有效章节，再提交审核")
            course.review_reason = None
        if body.action == "reject":
            if course.status != CourseStatus.pending_review or not body.reason.strip():
                raise ValueError("只有待审核课程可以驳回，且需填写原因")
            course.status = CourseStatus.draft
            course.review_reason = body.reason.strip()
        elif body.action == "unpublish":
            if course.status not in (CourseStatus.published, CourseStatus.archived):
                raise ValueError("仅已发布或归档课程可退回草稿")
            _ensure_no_activity(db, course_id)
            course.status = CourseStatus.draft
        else:
            course = CourseService.publish_action(db, course, body.action)
        if body.action != "submit_review":
            course.reviewed_by = str(requester.id)
            course.reviewed_at = datetime.now(timezone.utc)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return CourseResponse(**_course_to_response(course, db, requester))


@router.post("/{course_id}/chapters", response_model=ChapterResponse, status_code=201)
def add_chapter(
    course_id: str,
    body: ChapterCreate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_UPDATE)
    course = access.get_course(db, requester, course_id, manage=True, edit=True)
    if not course:
        raise HTTPException(404, "Course not found")
    _validate_resources(db, requester, body, course_id)
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
    access.get_course(db, requester, course_id, manage=True, edit=True)
    _validate_resources(db, requester, body, course_id)
    chapter = (db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.course_id == course_id)
    )).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    if "title" in body.model_fields_set and not (body.title or "").strip():
        raise HTTPException(422, "章节标题不能为空")
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
    access.get_course(db, requester, course_id, manage=True, edit=True)
    chapter = (db.execute(
        select(Chapter).where(Chapter.id == chapter_id, Chapter.course_id == course_id)
    )).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    db.delete(chapter)
    db.commit()


def _ensure_no_activity(db, course_id):
    for model in (CourseAssignment, LearningRecord, Exam):
        if db.scalar(select(model.id).where(model.course_id == course_id).limit(1).with_for_update()):
            raise HTTPException(409, "课程已有成员、记录或考核，请使用归档保留历史")


@router.post("/{course_id}/join", response_model=CourseResponse)
def join_course(course_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if "student" not in access.roles_for(db, requester):
        raise HTTPException(403, "仅学生可加入学习")
    course = db.execute(select(Course).where(Course.id == course_id).with_for_update()).scalar_one_or_none()
    if not course:
        raise HTTPException(404, "课程不存在")
    if course.status != CourseStatus.published:
        raise HTTPException(409, "只能加入已发布课程")
    existing = db.scalar(select(CourseAssignment.id).where(
        CourseAssignment.course_id == course_id, CourseAssignment.assignment_type == AssignmentType.user,
        CourseAssignment.target_id == str(requester.id),
    ).with_for_update())
    if not existing:
        db.add(CourseAssignment(course_id=course_id, assignment_type=AssignmentType.user, target_id=str(requester.id), assigned_by=str(requester.id), is_required=False))
        db.commit()
    requester._enrolled_ids = access.enrolled_ids(db, requester) | {course_id}
    return CourseResponse(**_course_to_response(course, db, requester))
