"""Course-scoped homework, current submissions and grading."""
from datetime import datetime, timezone
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import campus_access as access
from app.database import get_db
from app.models.course import Course, CourseStatus
from app.models.homework import Homework, HomeworkSubmission
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.common import PageMeta, PageResponse
from app.schemas.homework import GradeWrite, HomeworkResponse, HomeworkWrite, SubmissionResponse
from app.services import storage_service
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/courses/{course_id}/homeworks", tags=["homework"])


def _course(db, user, course_id, *, write=False, manage=False, edit=False):
    if write:
        db.scalar(select(Course).where(Course.id == course_id).with_for_update().execution_options(populate_existing=True))
    return access.get_course(db, user, course_id, manage=manage, edit=edit, learn=True)


def _homework(db, course_id, homework_id):
    homework = db.scalar(select(Homework).where(Homework.id == homework_id, Homework.course_id == course_id).with_for_update().execution_options(populate_existing=True))
    if homework is None:
        raise HTTPException(404, "作业不存在")
    return homework


@router.get("", response_model=PageResponse[HomeworkResponse])
def list_homeworks(course_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _course(db, user, course_id)
    stmt = select(Homework).where(Homework.course_id == course_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Homework.created_at, Homework.id).offset((page-1)*page_size).limit(page_size)).all()
    responses = []
    for homework in items:
        response = HomeworkResponse.model_validate(homework)
        submission = db.scalar(select(HomeworkSubmission).where(HomeworkSubmission.homework_id == homework.id, HomeworkSubmission.user_id == user.id))
        if submission:
            response.submission = SubmissionResponse.model_validate(submission)
        responses.append(response)
    return PageResponse(items=responses, meta=PageMeta(page=page, page_size=page_size, total=total))


@router.post("", response_model=HomeworkResponse, status_code=201)
def create_homework(course_id: str, body: HomeworkWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _course(db, user, course_id, write=True, manage=True, edit=True)
    homework = Homework(course_id=course_id, **body.model_dump(exclude={"due_at"}), due_at=body.due_at.astimezone(timezone.utc).replace(tzinfo=None))
    db.add(homework)
    db.commit()
    return homework


@router.put("/{homework_id}", response_model=HomeworkResponse)
def update_homework(course_id: str, homework_id: str, body: HomeworkWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _course(db, user, course_id, write=True, manage=True, edit=True)
    homework = _homework(db, course_id, homework_id)
    if db.scalar(select(HomeworkSubmission.id).where(HomeworkSubmission.homework_id == homework_id).limit(1)):
        raise HTTPException(409, "已有提交，不能修改作业要求")
    for key, value in body.model_dump().items():
        setattr(homework, key, value.astimezone(timezone.utc).replace(tzinfo=None) if key == "due_at" else value)
    db.commit()
    return homework


@router.delete("/{homework_id}", status_code=204)
def delete_homework(course_id: str, homework_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _course(db, user, course_id, write=True, manage=True, edit=True)
    homework = _homework(db, course_id, homework_id)
    if db.scalar(select(HomeworkSubmission.id).where(HomeworkSubmission.homework_id == homework_id).limit(1)):
        raise HTTPException(409, "已有提交，不能删除作业")
    db.delete(homework)
    db.commit()


@router.put("/{homework_id}/submission", response_model=SubmissionResponse)
def submit_homework(course_id: str, homework_id: str, text: str = Form("", max_length=20000), remove_attachment: bool = Form(False), file: UploadFile | None = File(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db, user, course_id, write=True)
    if "student" not in access.roles_for(db, user) or course.status != CourseStatus.published or course_id not in access.enrolled_ids(db, user):
        raise HTTPException(403, "仅已加入学生可提交已发布课程的作业")
    homework = _homework(db, course_id, homework_id)
    submission = db.scalar(select(HomeworkSubmission).where(HomeworkSubmission.homework_id == homework_id, HomeworkSubmission.user_id == user.id).with_for_update().execution_options(populate_existing=True))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now >= homework.due_at:
        raise HTTPException(409, "作业已截止")
    if submission and submission.graded_at is not None:
        raise HTTPException(409, "作业已批改，不能修改提交")
    old_key = submission.attachment_key if submission else None
    if submission is None:
        submission = HomeworkSubmission(homework_id=homework_id, user_id=str(user.id))
        db.add(submission)
    new_key = None
    if file:
        ext = Path(file.filename or "").suffix.lower()
        formats = {".pdf": (b"%PDF-", "application/pdf"), ".docx": (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"), ".png": (b"\x89PNG\r\n\x1a\n", "image/png"), ".jpg": (b"\xff\xd8\xff", "image/jpeg"), ".jpeg": (b"\xff\xd8\xff", "image/jpeg")}
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if not 0 < size <= 20 * 1024 * 1024:
            raise HTTPException(413, "附件不能为空且不能超过20MB")
        if ext not in formats or not file.file.read(16).startswith(formats[ext][0]):
            raise HTTPException(422, "附件仅支持内容匹配的 PDF、DOCX、JPG、PNG")
        file.file.seek(0)
        new_key = f"homework/{uuid.uuid4().hex}{ext}"
        submission.attachment_key = new_key
        submission.attachment_name = Path((file.filename or "附件").replace("\\", "/")).name[:255]
        submission.attachment_mime = formats[ext][1]
    elif remove_attachment:
        submission.attachment_key = submission.attachment_name = submission.attachment_mime = None
    submission.text = text.strip()
    if not submission.text and not submission.attachment_key:
        raise HTTPException(422, "请填写文字或上传一个附件")
    submission.submitted_at = now
    try:
        if new_key:
            storage_service.upload_fileobj(new_key, file.file, submission.attachment_mime)
        db.commit()
    except Exception:
        db.rollback()
        if new_key:
            storage_service.delete(new_key)
        raise
    if old_key and old_key != submission.attachment_key:
        storage_service.delete(old_key)
    return submission


@router.get("/{homework_id}/submissions", response_model=PageResponse[SubmissionResponse])
def list_submissions(course_id: str, homework_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _course(db, user, course_id, manage=True)
    _homework(db, course_id, homework_id)
    stmt = select(HomeworkSubmission, User.full_name).join(User, User.id == HomeworkSubmission.user_id).where(HomeworkSubmission.homework_id == homework_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = []
    for submission, name in db.execute(stmt.order_by(HomeworkSubmission.submitted_at, HomeworkSubmission.id).offset((page-1)*page_size).limit(page_size)):
        response = SubmissionResponse.model_validate(submission)
        response.full_name = name
        items.append(response)
    return PageResponse(items=items, meta=PageMeta(page=page, page_size=page_size, total=total))


@router.post("/{homework_id}/submissions/{submission_id}/grade", response_model=SubmissionResponse)
def grade_submission(course_id: str, homework_id: str, submission_id: str, body: GradeWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _course(db, user, course_id, write=True, manage=True)
    homework = _homework(db, course_id, homework_id)
    submission = db.scalar(select(HomeworkSubmission).where(HomeworkSubmission.id == submission_id, HomeworkSubmission.homework_id == homework_id).with_for_update().execution_options(populate_existing=True))
    if submission is None:
        raise HTTPException(404, "提交不存在")
    if body.score > homework.max_score:
        raise HTTPException(422, "分数不能超过作业满分")
    first_grade = submission.graded_at is None
    submission.score, submission.feedback = body.score, body.feedback
    submission.graded_by = str(user.id)
    submission.graded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if first_grade:
        NotificationService.notify_user(db, submission.user_id, NotificationType.assignment, "作业已批改", f"《{homework.title}》已批改，请到课程内查看分数和评语。", extra_data={"course_id": course_id, "homework_id": homework_id})
    db.commit()
    return submission


@router.get("/{homework_id}/submissions/{submission_id}/attachment")
def download_attachment(course_id: str, homework_id: str, submission_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db, user, course_id)
    _homework(db, course_id, homework_id)
    submission = db.scalar(select(HomeworkSubmission).where(HomeworkSubmission.id == submission_id, HomeworkSubmission.homework_id == homework_id))
    if submission is None:
        raise HTTPException(404, "提交不存在")
    if str(submission.user_id) != str(user.id) and not access.can_manage(db, user, course):
        raise HTTPException(403, "只能读取本人的作业附件")
    base = Path(storage_service.STORAGE_DIR).resolve()
    path = (base / (submission.attachment_key or "")).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        raise HTTPException(404, "附件不存在")
    return FileResponse(path, filename=submission.attachment_name, media_type=submission.attachment_mime)
