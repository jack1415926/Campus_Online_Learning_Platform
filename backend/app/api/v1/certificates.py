"""Course certificate eligibility, issue and lists; printing uses the browser."""
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models.platform import PlatformSettings
from app.core import campus_access as access
from app.database import get_db
from app.models.certificate import Certificate
from app.models.course import Course, CourseStatus
from app.models.exam import ExamRecord, ExamStatus
from app.models.homework import Homework, HomeworkSubmission
from app.models.user import User
from app.schemas.certificate import CertificateResponse, CertificateStatus
from app.schemas.common import PageMeta, PageResponse
from app.services.learning_service import LearningRecordService

router = APIRouter(tags=["certificates"])


def eligibility(db, user, course):
    reasons = []
    if not course.certificate_exam_id:
        reasons.append("本课程未启用证书")
    if not LearningRecordService.get_course_progress(db, user.id, course.id)["is_complete"]:
        reasons.append("尚未完成全部章节")
    required = db.scalars(select(Homework.id).where(Homework.course_id == course.id, Homework.is_required.is_(True))).all()
    graded = set(db.scalars(select(HomeworkSubmission.homework_id).where(
        HomeworkSubmission.homework_id.in_(required), HomeworkSubmission.user_id == user.id,
        HomeworkSubmission.graded_at.is_not(None), HomeworkSubmission.score.is_not(None))))
    if set(required) - graded:
        reasons.append("必交作业尚未全部提交并批改")
    record_id = db.scalar(select(ExamRecord.id).where(
        ExamRecord.exam_id == course.certificate_exam_id, ExamRecord.user_id == user.id,
        ExamRecord.status == ExamStatus.graded, ExamRecord.is_pass.is_(True)
    ).order_by(ExamRecord.id).limit(1)) if course.certificate_exam_id else None
    if course.certificate_exam_id and not record_id:
        reasons.append("指定结课考试尚无最终及格成绩")
    return reasons, record_id


def student_course(db, user, course_id):
    if "student" not in access.roles_for(db, user) or course_id not in access.enrolled_ids(db, user):
        raise HTTPException(403, "仅已加入课程的学生可领取证书")
    return access.get_course(db, user, course_id, learn=True)


@router.get("/courses/{course_id}/certificate", response_model=CertificateStatus)
def certificate_status(course_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = student_course(db, user, course_id)
    certificate = db.scalar(select(Certificate).where(Certificate.course_id == course_id, Certificate.user_id == user.id))
    reasons, _ = eligibility(db, user, course) if certificate is None else ([], None)
    return CertificateStatus(enabled=bool(course.certificate_exam_id), eligible=not reasons, reasons=reasons, certificate=certificate)


@router.post("/courses/{course_id}/certificate", response_model=CertificateResponse)
def claim_certificate(course_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Reuse the course lock already used by progress, grading and workflow changes.
    db.scalar(select(Course).where(Course.id == course_id).with_for_update().execution_options(populate_existing=True))
    course = student_course(db, user, course_id)
    certificate = db.scalar(select(Certificate).where(Certificate.course_id == course_id, Certificate.user_id == user.id).with_for_update())
    if certificate:
        return certificate
    if course.status != CourseStatus.published:
        raise HTTPException(409, "课程已归档，不能新领取证书")
    reasons, record_id = eligibility(db, user, course)
    if reasons:
        raise HTTPException(409, "；".join(reasons))
    certificate = Certificate(course_id=course_id, user_id=str(user.id), exam_record_id=record_id,
        number="CE-" + datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex,
        student_name=user.full_name, course_title=course.title, platform_name=db.get(PlatformSettings, 1).platform_name)
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


@router.get("/courses/{course_id}/certificates", response_model=PageResponse[CertificateResponse])
def course_certificates(course_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                        user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    access.get_course(db, user, course_id, manage=True)
    stmt = select(Certificate).where(Certificate.course_id == course_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Certificate.issued_at.desc(), Certificate.id).offset((page-1)*page_size).limit(page_size)).all()
    return PageResponse(items=items, meta=PageMeta(page=page, page_size=page_size, total=total))
