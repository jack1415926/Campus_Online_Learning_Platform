"""Exam API (EX-01 through EX-07)."""

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions, require_permission
from app.database import get_db
from app.models.exam import Exam, ExamRecord, ExamStatus, Question
from app.models.course import Course, CourseStatus
from app.core import campus_access as access
from app.services import campus_exam_service as campus
from app.models.user import User
from app.schemas.common import PageMeta, PageResponse
from app.schemas.exam import (
    ExamCreate, ExamRecordResponse, ExamResponse, ExamResultAnalysis,
    GradeExamRequest, QuestionBankCreate, QuestionBankResponse, QuestionBankUpdate,
    QuestionCreate, QuestionImportItem, QuestionResponse,
    SubmitExamRequest,
)
from app.services.exam_service import ExamService, QuestionBankService, QuestionService

router = APIRouter(prefix="/exams", tags=["exams"])


def _check_perm(db: Session, user: User, *perms: str):
    user_perms = load_user_permissions(db, user.id)
    if not any(p in user_perms for p in perms):
        raise HTTPException(403, f"Requires: {', '.join(perms)}")


# --- Questions (EX-01, EX-02) ---

@router.get("/questions", response_model=PageResponse[QuestionResponse])
def list_questions(question_type: str | None = Query(None), knowledge_point: str | None = Query(None),
                   question_bank_id: str | None = Query(None),
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=500),
                   requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    campus.bank_access(db, requester, question_bank_id)
    qs, total = QuestionService.list_questions(db, question_type, knowledge_point, page, page_size, question_bank_id, creator_id=None if "admin" in access.roles_for(db,requester) else str(requester.id))
    return PageResponse(items=qs, meta=PageMeta(page=page, page_size=page_size, total=total))


@router.post("/questions", response_model=QuestionResponse, status_code=201)
def create_question(body: QuestionCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    campus.bank_access(db, requester, body.question_bank_id)
    q = QuestionService.create_question(db, body, requester.id)
    db.commit()
    return q


@router.put("/questions/{q_id}", response_model=QuestionResponse)
def update_question(q_id: str, body: QuestionCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    q = campus.owner(db, requester, db.scalar(select(Question).where(Question.id == q_id).with_for_update()))
    campus.bank_access(db, requester, body.question_bank_id)
    for key, value in body.model_dump().items():
        setattr(q, key, value)
    q.is_objective = body.question_type.value != "short_answer"
    db.commit()
    return q


@router.post("/questions/batch", response_model=list[QuestionResponse], status_code=201)
def batch_import_questions(items: list[QuestionImportItem], requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    access.require_admin(db, requester)
    _check_perm(db, requester, Perm.EXAM_CREATE)
    qs = QuestionService.batch_import(db, items, requester.id)
    db.commit()
    return qs


@router.delete("/questions/{q_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(q_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    from app.models.exam import Question
    q = db.execute(select(Question).where(Question.id == q_id)).scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")
    campus.owner(db, requester, q)
    if any(q_id in (ids or []) for ids in db.scalars(select(Exam.question_ids).where(Exam.question_mode == "manual"))):
        raise HTTPException(409, "题目已被试卷引用，请保留题目或先修改草稿试卷")
    QuestionService.delete_question(db, q)
    db.commit()


# --- Question Banks (question bank categories) ---

@router.get("/question-banks", response_model=list[QuestionBankResponse])
def list_question_banks(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    results = QuestionBankService.list_banks(db, creator_id=None if "admin" in access.roles_for(db,requester) else str(requester.id))
    items = []
    for bank, count in results:
        item = QuestionBankResponse.model_validate(bank)
        item.question_count = count
        items.append(item)
    return items


@router.post("/question-banks", response_model=QuestionBankResponse, status_code=201)
def create_question_bank(body: QuestionBankCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    bank = QuestionBankService.create_bank(db, body, requester.id)
    db.commit()
    return QuestionBankResponse.model_validate(bank)


@router.put("/question-banks/{bank_id}", response_model=QuestionBankResponse)
def update_question_bank(bank_id: str, body: QuestionBankUpdate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    bank = QuestionBankService.get_bank(db, bank_id)
    if not bank:
        raise HTTPException(404, "Question bank not found")
    campus.owner(db, requester, bank)
    bank = QuestionBankService.update_bank(db, bank, body)
    db.commit()
    return QuestionBankResponse.model_validate(bank)


@router.delete("/question-banks/{bank_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_bank(bank_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    bank = QuestionBankService.get_bank(db, bank_id)
    if not bank:
        raise HTTPException(404, "Question bank not found")
    campus.owner(db, requester, bank)
    if db.scalar(select(Question.id).where(Question.question_bank_id == bank_id).limit(1)):
        raise HTTPException(409, "题库内仍有题目，不能删除")
    QuestionBankService.delete_bank(db, bank)
    db.commit()


@router.post("/question-banks/{bank_id}/import")
async def import_questions(bank_id: str, file: UploadFile = File(...),
                           requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    access.require_admin(db, requester)
    _check_perm(db, requester, Perm.EXAM_CREATE)
    bank = QuestionBankService.get_bank(db, bank_id)
    if not bank:
        raise HTTPException(404, "Question bank not found")
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Only .xlsx files are supported")
    file_bytes = await file.read()
    try:
        created, errors, skipped = QuestionBankService.import_excel(db, bank_id, file_bytes, requester.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"imported": len(created), "errors": errors, "skipped": skipped}


@router.get("/question-banks/template")
def download_template(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    access.require_admin(db, requester)
    import io
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "题目导入"
    headers = ["题型", "题干", "选项A", "选项B", "选项C",
               "选项D", "选项E", "正确答案", "分值", "难度", "知识点", "解析"]
    ws.append(headers)
    ws.append(["单选", "2+2等于多少？", "3", "4", "5", "6", None, "B", 2, 1, "基础数学", "选B"])
    ws.append(["多选", "以下哪些是质数？", "2", "4", "3", "6", None, "A,C", 3, 2, "数论", "2和3是质数"])
    ws.append(["判断", "地球是圆的。", None, None, None, None, None, "正确", 1, 1, "常识", None])
    ws.append(["填空", "中国首都是___。", None, None, None, None, None, "北京", 1, 1, "地理", None])
    ws.append(["简答", "简述HTTP协议。", None, None, None, None, None, "HTTP是超文本传输协议", 5, 3, "网络", None])
    for col_idx, width in enumerate([8, 30, 12, 12, 12, 12, 12, 15, 8, 8, 12, 20], 1):
        ws.column_dimensions[chr(64 + col_idx)].width = width
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    wb.close()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=question_import_template.xlsx"}
    )

# --- Exams (EX-03, EX-04, EX-05) ---

def _exam_response(exam):
    response = ExamResponse.model_validate(exam)
    response.question_scores = {q["id"]: q["score"] for q in exam.paper_snapshot or []}
    return response

@router.get("", response_model=PageResponse[ExamResponse])
def list_exams(course_id: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=500),
               requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_READ)
    stmt = select(Exam).join(Course, Course.id == Exam.course_id)
    if course_id:
        access.get_course(db, requester, course_id, learn=True)
        stmt = stmt.where(Exam.course_id == course_id)
    if "admin" not in access.roles_for(db, requester):
        if "teacher" in access.roles_for(db, requester):
            stmt = stmt.where(Course.created_by == requester.id)
        else:
            stmt = stmt.where(Exam.course_id.in_(access.enrolled_ids(db, requester)), Course.status.in_([CourseStatus.published, CourseStatus.archived]), Exam.paper_snapshot.is_not(None))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    exams = db.scalars(stmt.order_by(Exam.created_at, Exam.id).offset((page-1)*page_size).limit(page_size)).all()
    return PageResponse(items=[_exam_response(e) for e in exams], meta=PageMeta(page=page, page_size=page_size, total=total))


@router.get("/wrong-questions")
def get_wrong_questions(
    exam_id: str | None = Query(None),
    question_bank_id: str | None = Query(None),
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's wrong questions across exam attempts (错题集)."""
    access.require_admin(db, requester)
    return ExamService.get_wrong_questions(db, requester.id, exam_id, question_bank_id)


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam, _ = campus.load_exam(db, requester, exam_id)
    return _exam_response(exam)


@router.post("", response_model=ExamResponse, status_code=201)
def create_exam(body: ExamCreate, requester: User = Depends(require_permission(Perm.EXAM_CREATE)), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    exam = campus.write_exam(db, requester, body)
    db.commit()
    return _exam_response(exam)


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(exam_id: str, body: ExamCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    exam, _ = campus.load_exam(db, requester, exam_id, manage=True, edit=True, write=True)
    campus.write_exam(db, requester, body, exam)
    db.commit()
    return _exam_response(exam)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    exam, _ = campus.load_exam(db, requester, exam_id, manage=True, edit=True, write=True)
    if db.scalar(select(ExamRecord.id).where(ExamRecord.exam_id == exam_id).limit(1)):
        raise HTTPException(409, "已有答卷，不能删除考试")
    ExamService.delete_exam(db, exam)
    db.commit()


# --- Take exam (EX-03) ---

@router.post("/{exam_id}/start")
def start_exam(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start an exam attempt, returns questions."""
    record = campus.start(db, requester, exam_id)
    db.commit()
    return {**campus.view(record), "record_id": str(record.id)}


@router.post("/records/{record_id}/submit", response_model=ExamRecordResponse)
def submit_exam(record_id: str, body: SubmitExamRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit exam answers for auto-grading (EX-06)."""
    record, exam, course = campus.load_record(db, requester, record_id)
    if str(record.user_id) != str(requester.id) or "student" not in access.roles_for(db, requester):
        raise HTTPException(403, "只能提交本人答卷")
    if record.status == ExamStatus.in_progress and course.status != CourseStatus.published:
        raise HTTPException(409, "归档课程不接受新交卷")
    campus.submit(db, record, body.answers)
    db.commit()
    return campus.view(record)


@router.put("/records/{record_id}/draft")
def save_draft(record_id: str, body: SubmitExamRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record, _, course = campus.load_record(db, requester, record_id)
    if str(record.user_id) != str(requester.id) or "student" not in access.roles_for(db, requester):
        raise HTTPException(403, "只能保存本人答案")
    if record.status != ExamStatus.in_progress or course.status != CourseStatus.published:
        db.commit()
        raise HTTPException(409, "考试已结束或课程已归档")
    campus.validate_answers(record.question_snapshot, body.answers)
    record.draft_answers = [a.model_dump() for a in body.answers]
    db.commit()
    return {"saved": True, "deadline_at": record.deadline_at}


@router.post("/records/{record_id}/grade", response_model=ExamRecordResponse)
def manual_grade(record_id: str, body: GradeExamRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manual grade subjective questions (EX-06)."""
    _check_perm(db, requester, Perm.EXAM_GRADE)
    record, _, _ = campus.load_record(db, requester, record_id, grade=True)
    campus.grade(db, record, body, requester.id)
    db.commit()
    return campus.view(record, manager=True)


# --- Records & Analysis (EX-07) ---

@router.get("/records/my", response_model=list[ExamRecordResponse])
def get_my_records(exam_id: str | None = Query(None), requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_READ)
    records = ExamService.get_user_records(db, requester.id, exam_id)
    for record in records:
        if record.status == ExamStatus.in_progress and record.question_snapshot and record.deadline_at and campus.now() >= datetime.fromisoformat(record.deadline_at):
            campus.load_record(db, requester, str(record.id))
            db.commit()
    return records


@router.get("/records/{record_id}")
def get_record(record_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record, _, course = campus.load_record(db, requester, record_id)
    response = campus.view(record, manager=access.can_manage(db, requester, course))
    db.commit()
    return response


@router.get("/{exam_id}/records")
def exam_records(exam_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.user import User as Student
    exam, _ = campus.load_exam(db, requester, exam_id, manage=True, write=True)
    stmt = select(ExamRecord, Student.full_name).join(Student, Student.id == ExamRecord.user_id).where(ExamRecord.exam_id == exam_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = []
    for record, name in db.execute(stmt.order_by(ExamRecord.created_at.desc(),ExamRecord.id).offset((page-1)*page_size).limit(page_size).with_for_update().execution_options(populate_existing=True)):
        if record.question_snapshot and record.deadline_at:
            campus.expire(db, record)
        response = ExamRecordResponse.model_validate(record).model_dump()
        response["full_name"] = name
        items.append(response)
    db.commit()
    return {"items": items, "meta": {"total": total, "page": page, "page_size": page_size}}


@router.get("/{exam_id}/analysis", response_model=ExamResultAnalysis)
def get_exam_analysis(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """EX-07: exam result analysis."""
    access.require_admin(db, requester)
    return ExamService.get_exam_analysis(db, exam_id)
