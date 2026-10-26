"""Exam API (EX-01 through EX-07)."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.exam import Exam, ExamRecord
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
    qs, total = QuestionService.list_questions(db, question_type, knowledge_point, page, page_size, question_bank_id)
    return PageResponse(items=qs, meta=PageMeta(page=page, page_size=page_size, total=total))


@router.post("/questions", response_model=QuestionResponse, status_code=201)
def create_question(body: QuestionCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    q = QuestionService.create_question(db, body, requester.id)
    db.commit()
    return q


@router.post("/questions/batch", response_model=list[QuestionResponse], status_code=201)
def batch_import_questions(items: list[QuestionImportItem], requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    QuestionService.delete_question(db, q)
    db.commit()


# --- Question Banks (question bank categories) ---

@router.get("/question-banks", response_model=list[QuestionBankResponse])
def list_question_banks(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = QuestionBankService.list_banks(db)
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
    bank = QuestionBankService.update_bank(db, bank, body)
    db.commit()
    return QuestionBankResponse.model_validate(bank)


@router.delete("/question-banks/{bank_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question_bank(bank_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    bank = QuestionBankService.get_bank(db, bank_id)
    if not bank:
        raise HTTPException(404, "Question bank not found")
    QuestionBankService.delete_bank(db, bank)
    db.commit()


@router.post("/question-banks/{bank_id}/import")
async def import_questions(bank_id: str, file: UploadFile = File(...),
                           requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
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

@router.get("", response_model=PageResponse[ExamResponse])
def list_exams(course_id: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=500),
               requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exams, total = ExamService.list_exams(db, course_id, page, page_size)
    return PageResponse(items=exams, meta=PageMeta(page=page, page_size=page_size, total=total))


@router.get("/wrong-questions")
def get_wrong_questions(
    exam_id: str | None = Query(None),
    question_bank_id: str | None = Query(None),
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the user's wrong questions across exam attempts (错题集)."""
    return ExamService.get_wrong_questions(db, requester.id, exam_id, question_bank_id)


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exam = ExamService.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    return exam


@router.post("", response_model=ExamResponse, status_code=201)
def create_exam(body: ExamCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    exam = ExamService.create_exam(db, body, requester.id)
    db.commit()
    return exam


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.EXAM_CREATE)
    exam = ExamService.get_exam(db, exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    ExamService.delete_exam(db, exam)
    db.commit()


# --- Take exam (EX-03) ---

@router.post("/{exam_id}/start")
def start_exam(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start an exam attempt, returns questions."""
    try:
        record, questions = ExamService.start_exam(db, requester.id, exam_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"record_id": record.id, "questions": questions,
            "duration_minutes": ExamService.get_exam(db, exam_id).duration_minutes}


@router.post("/records/{record_id}/submit", response_model=ExamRecordResponse)
def submit_exam(record_id: str, body: SubmitExamRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit exam answers for auto-grading (EX-06)."""
    record = ExamService.get_record(db, record_id)
    if not record or record.user_id != requester.id:
        raise HTTPException(404, "Exam record not found")
    exam = ExamService.get_exam(db, record.exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    record = ExamService.submit_exam(db, record, exam, body)
    db.commit()
    return record


@router.post("/records/{record_id}/grade", response_model=ExamRecordResponse)
def manual_grade(record_id: str, body: GradeExamRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manual grade subjective questions (EX-06)."""
    _check_perm(db, requester, Perm.EXAM_GRADE)
    record = ExamService.get_record(db, record_id)
    if not record:
        raise HTTPException(404, "Exam record not found")
    record = ExamService.manual_grade(db, record, body, requester.id)
    db.commit()
    return record


# --- Records & Analysis (EX-07) ---

@router.get("/records/my", response_model=list[ExamRecordResponse])
def get_my_records(exam_id: str | None = Query(None), requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ExamService.get_user_records(db, requester.id, exam_id)


@router.get("/records/{record_id}")
def get_record(record_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = ExamService.get_record(db, record_id)
    if not record:
        raise HTTPException(404, "Record not found")
    return ExamService.enrich_record(db, record)


@router.get("/{exam_id}/analysis", response_model=ExamResultAnalysis)
def get_exam_analysis(exam_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """EX-07: exam result analysis."""
    return ExamService.get_exam_analysis(db, exam_id)
