"""Manual course exams using fixed papers and one server deadline per attempt."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select

from app.core import campus_access as access
from app.models.course import Course, CourseStatus
from app.models.exam import Exam, ExamRecord, ExamStatus, Question
from app.models.notification import Notification, NotificationType
from app.models.question_bank import QuestionBank
from app.schemas.exam import ExamRecordResponse, QuestionCreate
from app.services.notification_service import NotificationService


def now():
    return datetime.now(timezone.utc)


def owner(db, user, obj):
    if not access.roles_for(db, user) & {"teacher", "admin"}:
        raise HTTPException(403, "仅审核通过的教师或管理员可管理考核")
    if obj is None:
        raise HTTPException(404, "题目或题库不存在")
    if "admin" not in access.roles_for(db, user) and str(obj.created_by) != str(user.id):
        raise HTTPException(403, "只能管理本人的题库和题目")
    return obj


def bank_access(db, user, bank_id):
    if bank_id:
        owner(db, user, db.get(QuestionBank, bank_id))


def load_exam(db, user, exam_id, *, manage=False, edit=False, write=False):
    exam = db.get(Exam, exam_id)
    if exam is None or not exam.course_id:
        raise HTTPException(404, "课程考试不存在")
    if write or edit:
        db.scalar(select(Course).where(Course.id == exam.course_id).with_for_update().execution_options(populate_existing=True))
        exam = db.scalar(select(Exam).where(Exam.id == exam_id).with_for_update().execution_options(populate_existing=True))
        if exam is None:
            raise HTTPException(404, "课程考试不存在")
    course = access.get_course(db, user, exam.course_id, manage=manage, edit=edit, learn=not manage)
    return exam, course


def write_exam(db, user, body, exam=None):
    course_id = exam.course_id if exam else body.course_id
    if body.course_id != course_id:
        raise HTTPException(409, "考试不能转移到其他课程")
    access.get_course(db, user, course_id, manage=True, edit=True)
    if exam and db.scalar(select(ExamRecord.id).where(ExamRecord.exam_id == exam.id).limit(1)):
        raise HTTPException(409, "已有答卷，不能修改考试")
    paper = []
    for question_id in body.question_ids:
        q = owner(db, user, db.get(Question, question_id))
        # Existing legacy questions must satisfy the same four-type validation.
        try:
            QuestionCreate.model_validate({k: getattr(q, k) for k in QuestionCreate.model_fields})
        except ValueError:
            raise HTTPException(422, "题库中有题目不满足四题型校验，请先修正") from None
        paper.append({"id": str(q.id), "type": q.question_type.value, "content": q.content, "options": deepcopy(q.options), "correct_answer": deepcopy(q.correct_answer), "explanation": q.explanation, "score": body.question_scores.get(str(q.id), q.score)})
    if exam is None:
        exam = Exam(created_by=str(user.id))
        db.add(exam)
    for key in ("title", "description", "course_id", "duration_minutes", "max_attempts", "pass_score", "grading_notes"):
        setattr(exam, key, getattr(body, key))
    exam.start_time = body.start_time.astimezone(timezone.utc).isoformat()
    exam.end_time = body.end_time.astimezone(timezone.utc).isoformat()
    exam.question_ids = list(body.question_ids)
    exam.question_mode = "manual"
    exam.paper_snapshot = paper
    exam.status = "active"
    db.flush()
    return exam


def validate_answers(paper, answers):
    questions = {q["id"]: q for q in paper}
    seen = set()
    for item in answers:
        if item.question_id in seen or item.question_id not in questions:
            raise HTTPException(422, "答案中存在重复题目或试卷外题目")
        seen.add(item.question_id)
        q, value = questions[item.question_id], item.answer
        if value is None or value == "" or value == []:
            continue
        if q["type"] in ("single_choice", "true_false"):
            valid = {o["key"] for o in q.get("options") or []} if q["type"] == "single_choice" else {"true", "false"}
            if not isinstance(value, str) or value not in valid:
                raise HTTPException(422, "答案不属于题目选项")
        elif q["type"] == "multiple_choice":
            valid = {o["key"] for o in q.get("options") or []}
            if not isinstance(value, list) or any(not isinstance(v,str) or v not in valid for v in value) or len(set(value)) != len(value):
                raise HTTPException(422, "多选答案必须是无重复的有效选项")
        elif not isinstance(value,str) or len(value) > 20000:
            raise HTTPException(422, "简答题答案须为不超过20000字符的文字")


def finalize(db, record):
    complete = all(a["graded"] for a in record.answers)
    record.total_score = sum(a["score"] for a in record.answers)
    record.status = ExamStatus.graded if complete else ExamStatus.submitted
    record.is_pass = record.total_score / record.max_score * 100 >= record.pass_percent if complete else None
    if complete:
        record.graded_at = now().isoformat()
        key = f"exam:{record.id}"
        if not db.scalar(select(Notification.id).where(Notification.event_key == key)):
            exam = db.get(Exam, record.exam_id)
            notification = NotificationService.notify_user(db, record.user_id, NotificationType.exam_reminder, "考试成绩已发布", f"《{exam.title}》已产生最终成绩，请到课程内查看。", extra_data={"course_id": exam.course_id, "exam_id": str(exam.id)})
            notification.event_key = key
    db.flush()


def submit(db, record, answers):
    if record.status != ExamStatus.in_progress:
        return record
    validate_answers(record.question_snapshot, answers)
    submitted = {a.question_id: a.answer for a in answers}
    results = []
    for q in record.question_snapshot:
        answer = submitted.get(q["id"])
        subjective = q["type"] == "short_answer"
        if q["type"] == "multiple_choice":
            correct = set(answer or []) == set(q["correct_answer"])
        else:
            correct = answer == q["correct_answer"]
        results.append({"question_id": q["id"], "answer": answer, "score": q["score"] if correct and not subjective else 0.0, "is_correct": None if subjective else correct, "graded": not subjective, "grader_comment": None})
    record.answers = results
    record.submitted_at = now().isoformat()
    record.time_spent_seconds = max(0, int((min(now(), datetime.fromisoformat(record.deadline_at)) - datetime.fromisoformat(record.started_at)).total_seconds()))
    finalize(db, record)
    return record


def expire(db, record):
    if record.status == ExamStatus.in_progress and now() >= datetime.fromisoformat(record.deadline_at):
        from app.schemas.exam import SubmitAnswerItem
        submit(db, record, [SubmitAnswerItem.model_validate(a) for a in record.draft_answers or []])


def start(db, user, exam_id):
    exam, course = load_exam(db, user, exam_id, write=True)
    if "student" not in access.roles_for(db, user) or course.status != CourseStatus.published:
        raise HTTPException(403, "仅已加入学生可参加已发布课程考试")
    if not exam.paper_snapshot:
        raise HTTPException(409, "该旧考试尚未配置固定试卷")
    records = db.scalars(select(ExamRecord).where(ExamRecord.exam_id == exam_id, ExamRecord.user_id == user.id).order_by(ExamRecord.attempt_number.desc()).with_for_update().execution_options(populate_existing=True)).all()
    if records and records[0].status == ExamStatus.in_progress:
        if not records[0].question_snapshot or not records[0].deadline_at:
            raise HTTPException(409, "该旧答卷缺少试卷快照，请先核对历史记录")
        expire(db, records[0])
        return records[0]
    current = now()
    if exam.status != "active" or not datetime.fromisoformat(exam.start_time) <= current < datetime.fromisoformat(exam.end_time):
        raise HTTPException(409, "考试尚未开放或已经结束")
    if len(records) >= exam.max_attempts:
        raise HTTPException(409, "已达到最大考试次数")
    record = ExamRecord(exam_id=exam_id, user_id=str(user.id), attempt_number=max((r.attempt_number for r in records),default=0)+1, status=ExamStatus.in_progress, started_at=current.isoformat(), deadline_at=min(current+timedelta(minutes=exam.duration_minutes),datetime.fromisoformat(exam.end_time)).isoformat(), question_snapshot=deepcopy(exam.paper_snapshot), pass_percent=exam.pass_score, max_score=sum(q["score"] for q in exam.paper_snapshot), draft_answers=[])
    db.add(record)
    db.flush()
    return record


def load_record(db, user, record_id, *, grade=False):
    record = db.get(ExamRecord, record_id)
    if record is None:
        raise HTTPException(404, "答卷不存在")
    exam, course = load_exam(db, user, record.exam_id, manage=grade, write=True)
    record = db.scalar(select(ExamRecord).where(ExamRecord.id == record_id).with_for_update().execution_options(populate_existing=True))
    if not grade and str(record.user_id) != str(user.id) and not access.can_manage(db, user, course):
        raise HTTPException(403, "只能查看本人或本人课程的答卷")
    if not record.question_snapshot or not record.deadline_at:
        raise HTTPException(409, "旧答卷缺少固定试卷和截止时间，不重新推算历史成绩")
    expire(db, record)
    return record, exam, course


def grade(db, record, body, grader_id):
    if record.status not in (ExamStatus.submitted, ExamStatus.graded):
        raise HTTPException(409, "只能批改已提交答卷")
    questions = {q["id"]: q for q in record.question_snapshot}
    ids = [a.question_id for a in body.answers]
    if len(set(ids)) != len(ids) or any(q not in questions or questions[q]["type"] != "short_answer" for q in ids):
        raise HTTPException(422, "只能批改本卷简答题，题目不能重复")
    if any(a.score > questions[a.question_id]["score"] for a in body.answers):
        raise HTTPException(422, "分数不能超过该题满分")
    updates = {a.question_id: a for a in body.answers}
    answers = deepcopy(record.answers)
    for answer in answers:
        if answer["question_id"] in updates:
            item = updates[answer["question_id"]]
            answer.update(score=item.score, graded=True, grader_comment=item.grader_comment)
    record.answers = answers
    record.graded_by = str(grader_id)
    finalize(db, record)


def view(record, *, manager=False):
    data = ExamRecordResponse.model_validate(record).model_dump()
    reveal = manager or record.status == ExamStatus.graded
    data["questions"] = [{k: deepcopy(v) for k,v in q.items() if reveal or k not in ("correct_answer", "explanation")} for q in record.question_snapshot or []]
    if record.status == ExamStatus.in_progress:
        data["answers"] = deepcopy(record.draft_answers or [])
    data["server_time"] = now().isoformat()
    return data
