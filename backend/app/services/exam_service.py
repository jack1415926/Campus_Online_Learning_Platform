"""Exam service (EX-01 through EX-07)."""

from datetime import datetime, timezone
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.exam import Exam, ExamRecord, ExamStatus, Question, QuestionType
from app.schemas.exam import (
    ExamCreate, GradeExamRequest, QuestionBankCreate, QuestionBankUpdate,
    QuestionCreate, QuestionImportItem,
    SubmitExamRequest,
)
from app.models.question_bank import QuestionBank


class QuestionService:

    @staticmethod
    def list_questions(db: Session, question_type=None, knowledge_point=None, page=1, page_size=20, question_bank_id=None):
        stmt = select(Question)
        if question_type:
            stmt = stmt.where(Question.question_type == question_type)
        if knowledge_point:
            stmt = stmt.where(Question.knowledge_point == knowledge_point)
        if question_bank_id:
            stmt = stmt.where(Question.question_bank_id == question_bank_id)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
        stmt = stmt.offset((page-1)*page_size).limit(page_size).order_by(Question.created_at.desc())
        return list(db.execute(stmt).scalars().all()), total

    @staticmethod
    def create_question(db: Session, body: QuestionCreate, creator_id: str):
        is_obj = body.question_type in (QuestionType.single_choice, QuestionType.multiple_choice,
                                         QuestionType.true_false, QuestionType.fill_blank)
        q = Question(
            question_type=body.question_type, content=body.content,
            options=body.options, correct_answer=body.correct_answer,
            explanation=body.explanation, difficulty=body.difficulty,
            knowledge_point=body.knowledge_point, score=body.score,
            is_objective=is_obj, created_by=creator_id,
            question_bank_id=body.question_bank_id,
        )
        db.add(q)
        db.flush()
        return q

    @staticmethod
    def batch_import(db: Session, items: list[QuestionImportItem], creator_id: str):
        created = []
        for item in items:
            is_obj = item.question_type in (QuestionType.single_choice, QuestionType.multiple_choice,
                                             QuestionType.true_false, QuestionType.fill_blank)
            q = Question(
                question_type=item.question_type, content=item.content,
                options=item.options, correct_answer=item.correct_answer,
                difficulty=item.difficulty, knowledge_point=item.knowledge_point,
                score=item.score, is_objective=is_obj, created_by=creator_id,
            )
            db.add(q)
            created.append(q)
        db.flush()
        return created

    @staticmethod
    def delete_question(db: Session, q: Question):
        db.delete(q)
        db.flush()


class ExamService:

    @staticmethod
    def list_exams(db: Session, course_id=None, page=1, page_size=20):
        stmt = select(Exam)
        if course_id:
            stmt = stmt.where(Exam.course_id == course_id)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
        stmt = stmt.offset((page-1)*page_size).limit(page_size).order_by(Exam.created_at.desc())
        return list(db.execute(stmt).scalars().all()), total

    @staticmethod
    def get_exam(db: Session, exam_id: str):
        return db.execute(select(Exam).where(Exam.id == exam_id)).scalar_one_or_none()

    @staticmethod
    def create_exam(db: Session, body: ExamCreate, creator_id: str):
        question_ids = body.question_ids
        question_mode = body.question_mode
        # Random mode: convert random_rules into question_ids dict
        if body.question_mode == "random" and body.random_rules:
            rules = [r.model_dump() for r in body.random_rules if r.count > 0]
            if rules:
                question_ids = {"strategy": "random", "rules": rules}
            else:
                question_ids = None
        exam = Exam(
            title=body.title, description=body.description, course_id=body.course_id,
            question_ids=question_ids, question_mode=question_mode,
            duration_minutes=body.duration_minutes,
            pass_score=body.pass_score, max_attempts=body.max_attempts,
            shuffle_questions=body.shuffle_questions, shuffle_options=body.shuffle_options,
            screen_lock=body.screen_lock,
            start_time=body.start_time, end_time=body.end_time, created_by=creator_id,
        )
        db.add(exam)
        db.flush()
        return exam

    @staticmethod
    def delete_exam(db: Session, exam: Exam):
        db.delete(exam)
        db.flush()

    @staticmethod
    def start_exam(db: Session, user_id: str, exam_id: str):
        """Start a new exam attempt (EX-03)."""
        exam = ExamService.get_exam(db, exam_id)
        if not exam:
            raise ValueError("Exam not found")

        # Check attempt count
        count = db.execute(
            select(func.count()).select_from(
                select(ExamRecord).where(
                    ExamRecord.user_id == user_id, ExamRecord.exam_id == exam_id
                ).subquery()
            )
        ).scalar() or 0

        if count >= exam.max_attempts:
            raise ValueError(f"Max attempts ({exam.max_attempts}) reached")

        record = ExamRecord(
            user_id=user_id, exam_id=exam_id,
            status=ExamStatus.in_progress,
            started_at=datetime.now(timezone.utc).isoformat(),
            attempt_number=count + 1,
        )
        db.add(record)
        db.flush()

        # Get questions for the exam (EX-04: support random per-bank)
        q_ids = exam.question_ids or []
        questions = []
        import random as _rand
        if isinstance(q_ids, list):
            qs = db.execute(select(Question).where(Question.id.in_(q_ids))).scalars().all()
            questions = [{"id": str(q.id), "type": q.question_type.value, "content": q.content,
                          "options": q.options, "score": q.score} for q in qs]
        elif isinstance(q_ids, dict) and q_ids.get("strategy") == "random":
            rules = q_ids.get("rules")
            if rules:
                # Random per question bank: pick `count` random questions from each bank
                for rule in rules:
                    bank_id = rule.get("question_bank_id")
                    count = int(rule.get("count", 5))
                    stmt = select(Question)
                    if bank_id:
                        stmt = stmt.where(Question.question_bank_id == bank_id)
                    qs = list(db.execute(stmt).scalars().all())
                    count = min(count, len(qs))
                    selected = _rand.sample(qs, count) if count < len(qs) else qs
                    questions.extend(
                        {"id": str(q.id), "type": q.question_type.value, "content": q.content,
                         "options": q.options, "score": q.score} for q in selected
                    )
            else:
                # Legacy random config: {"strategy":"random","count":N,"types":[...]}
                stmt = select(Question)
                if q_ids.get("types"):
                    stmt = stmt.where(Question.question_type.in_(q_ids["types"]))
                qs = list(db.execute(stmt).scalars().all())
                count_q = min(q_ids.get("count", 10), len(qs))
                selected = _rand.sample(qs, count_q) if count_q < len(qs) else qs
                questions = [{"id": str(q.id), "type": q.question_type.value, "content": q.content,
                              "options": q.options, "score": q.score} for q in selected]
            if exam.shuffle_questions:
                _rand.shuffle(questions)

        if exam.shuffle_questions and isinstance(q_ids, list):
            import random
            random.shuffle(questions)

        # Shuffle options for choice questions if enabled
        option_map = {}
        if exam.shuffle_options:
            import random as _rnd
            for q_dict in questions:
                if q_dict["type"] in ("single_choice", "multiple_choice") and q_dict.get("options"):
                    original_opts = list(q_dict["options"])
                    _rnd.shuffle(original_opts)
                    new_opts = []
                    mapping = {}
                    for idx, opt in enumerate(original_opts):
                        new_key = chr(65 + idx)
                        new_opts.append({"key": new_key, "text": opt["text"]})
                        mapping[new_key] = opt.get("key", chr(65 + idx))
                    q_dict["options"] = new_opts
                    option_map[q_dict["id"]] = mapping

        # Store question IDs and option mapping in the record
        record_meta = {}
        if isinstance(q_ids, dict) and q_ids.get("strategy") == "random":
            record_meta["question_ids"] = [q["id"] for q in questions]
        elif isinstance(q_ids, list):
            record_meta["question_ids"] = list(q_ids)
        if option_map:
            record_meta["option_map"] = option_map
            # Persist option map separately so it survives submission (answers get overwritten)
            record.shuffle_map = option_map
        if record_meta:
            record.answers = record_meta

        return record, questions

    @staticmethod
    def submit_exam(db: Session, record: ExamRecord, exam: Exam, body: SubmitExamRequest):
        """Submit and auto-grade objective questions (EX-06)."""
        now = datetime.now(timezone.utc).isoformat()

        # Extract option_map from record (persisted separately so it survives answer overwrite)
        option_map = {}
        if record.shuffle_map:
            option_map = record.shuffle_map
        elif record.answers and isinstance(record.answers, dict):
            option_map = record.answers.get("option_map", {})

        # Get question IDs from exam config
        q_ids = []
        if isinstance(exam.question_ids, list):
            q_ids = exam.question_ids
        elif isinstance(exam.question_ids, dict) and exam.question_ids.get("strategy") == "random":
            if record.answers and isinstance(record.answers, dict):
                q_ids = record.answers.get("question_ids", [])

        # Fetch questions
        questions = {}
        if q_ids:
            qs = db.execute(select(Question).where(Question.id.in_(q_ids))).scalars().all()
            questions = {str(q.id): q for q in qs}

        total_score = 0.0
        max_score = 0.0
        graded_answers = []

        for ans in body.answers:
            q = questions.get(ans.question_id)
            if not q:
                continue
            max_score += q.score
            answer_data = {
                "question_id": ans.question_id,
                "answer": ans.answer,
                "score": 0.0,
                "is_correct": None,
                "grader_comment": None,
            }

            if q.is_objective and q.correct_answer:
                correct = q.correct_answer
                if isinstance(correct, dict):
                    correct = str(correct.get("value", ""))

                if q.question_type in (QuestionType.single_choice, QuestionType.true_false):
                    raw_ans = str(ans.answer).strip() if ans.answer else ""
                    q_map = option_map.get(ans.question_id, {})
                    orig_ans = q_map.get(raw_ans, raw_ans) if q_map else raw_ans
                    is_correct = orig_ans == str(correct).strip() if ans.answer else False
                    # Store the answer in the same (original) coordinate as correct_answer
                    answer_data["answer"] = orig_ans
                elif q.question_type == QuestionType.multiple_choice:
                    q_map = option_map.get(ans.question_id, {})
                    if isinstance(ans.answer, list):
                        raw_list = ans.answer
                    elif ans.answer:
                        raw_list = [ans.answer]
                    else:
                        raw_list = []
                    if q_map:
                        orig_list = [q_map.get(str(a), str(a)) for a in raw_list]
                    else:
                        orig_list = [str(a) for a in raw_list]
                    ans_set = set(orig_list)
                    correct_set = set(correct) if isinstance(correct, list) else set([str(correct)]) if correct else set()
                    is_correct = ans_set == correct_set
                    # Store the answer in the same (original) coordinate as correct_answer
                    answer_data["answer"] = sorted(orig_list)
                elif q.question_type == QuestionType.fill_blank:
                    ans_list = ans.answer if isinstance(ans.answer, list) else [ans.answer]
                    correct_list = correct if isinstance(correct, list) else [correct]
                    is_correct = (len(ans_list) == len(correct_list) and
                                  all(str(a).strip().lower() == str(c).strip().lower()
                                      for a, c in zip(ans_list, correct_list)))
                else:
                    is_correct = False

                answer_data["is_correct"] = is_correct
                answer_data["score"] = q.score if is_correct else 0.0
                total_score += answer_data["score"]
            else:
                answer_data["is_correct"] = None

            graded_answers.append(answer_data)

        has_subjective = any(a["is_correct"] is None for a in graded_answers)

        # Use ORM assignment (no direct SQL)
        record.answers = graded_answers
        record.total_score = total_score
        record.max_score = max_score
        record.submitted_at = now
        record.time_spent_seconds = body.time_spent_seconds

        if has_subjective:
            record.status = ExamStatus.submitted
        else:
            record.status = ExamStatus.graded
            record.graded_at = now
            record.is_pass = (total_score / max_score * 100) >= exam.pass_score if max_score > 0 else False

        db.flush()
        return record

    @staticmethod
    def manual_grade(db: Session, record: ExamRecord, body: GradeExamRequest, grader_id: str):
        """Manual grade subjective questions (EX-06)."""
        now = datetime.now(timezone.utc).isoformat()
        answers = record.answers or []
        grade_map = {g.question_id: g for g in body.answers}

        for ans in answers:
            if ans.get("is_correct") is None and ans["question_id"] in grade_map:
                g = grade_map[ans["question_id"]]
                old_score = ans.get("score", 0.0)
                ans["score"] = g.score
                ans["is_correct"] = g.score > 0
                ans["grader_comment"] = g.grader_comment
                record.total_score = (record.total_score or 0) - old_score + g.score

        record.answers = answers
        record.status = ExamStatus.graded
        record.graded_at = now
        record.graded_by = grader_id

        exam = ExamService.get_exam(db, record.exam_id)
        if exam:
            record.is_pass = ((record.total_score or 0) / record.max_score * 100) >= exam.pass_score if record.max_score else False

        db.flush()
        return record

    @staticmethod
    def get_user_records(db: Session, user_id: str, exam_id=None):
        stmt = (
            select(ExamRecord)
            .where(ExamRecord.user_id == user_id)
            .order_by(ExamRecord.submitted_at.desc())
        )
        if exam_id:
            stmt = stmt.where(ExamRecord.exam_id == exam_id)
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_record(db: Session, record_id: str):
        return db.execute(select(ExamRecord).where(ExamRecord.id == record_id)).scalar_one_or_none()

    @staticmethod
    def _map_correct_answer(mapping: dict, correct_answer):
        """Map a correct answer back to the display key shown during the attempt.

        Handles both single-choice (string) and multiple-choice (list) answers.
        """
        if not mapping:
            return correct_answer
        if isinstance(correct_answer, list):
            # Map each key, then sort by the display order (alphabetical = option display order)
            return sorted(mapping.get(k, k) for k in correct_answer)
        if isinstance(correct_answer, str):
            return mapping.get(correct_answer, correct_answer)
        return correct_answer

    @staticmethod
    def enrich_record(db: Session, record: ExamRecord) -> dict:
        """Enrich an exam record's answers with question content and correct answers."""
        data = {
            "id": record.id,
            "user_id": record.user_id,
            "exam_id": record.exam_id,
            "answers": record.answers,
            "total_score": record.total_score,
            "max_score": record.max_score,
            "is_pass": record.is_pass,
            "status": record.status,
            "started_at": record.started_at,
            "submitted_at": record.submitted_at,
            "attempt_number": record.attempt_number,
            "time_spent_seconds": record.time_spent_seconds,
            "created_at": record.created_at,
        }
        exam = db.execute(select(Exam).where(Exam.id == record.exam_id)).scalar_one_or_none()
        if exam:
            data["exam_title"] = exam.title
        answers = record.answers or []
        shuffle_map = record.shuffle_map or {}
        enriched = []
        for a in answers:
            qid = a.get("question_id") if isinstance(a, dict) else None
            item = dict(a) if isinstance(a, dict) else {"answer": a}
            if qid:
                q = db.execute(select(Question).where(Question.id == qid)).scalar_one_or_none()
                if q:
                    item["question_content"] = q.content
                    item["question_type"] = q.question_type.value if hasattr(q.question_type, "value") else q.question_type
                    item["correct_answer"] = q.correct_answer
                    item["explanation"] = q.explanation
                    item["options"] = q.options
                    # Reconstruct the option order as shown during the attempt
                    mapping = shuffle_map.get(str(qid))
                    if mapping:
                        display_options = []
                        reverse_mapping = {}  # {original_key: display_key}
                        for display_key, original_key in mapping.items():
                            reverse_mapping[original_key] = display_key
                            opt = next((o for o in (q.options or []) if o.get("key") == original_key), None)
                            if opt:
                                display_options.append({"key": display_key, "text": opt["text"]})
                        if display_options:
                            item["options"] = display_options
                        # Map the answer and correct answer(s) to the display key(s) seen by the user
                        # Use reverse_mapping: correct_answer and answer are stored in original keys,
                        # we need to map them to display keys shown to the user
                        item["correct_answer"] = ExamService._map_correct_answer(reverse_mapping, q.correct_answer)
                        if "answer" in item:
                            item["answer"] = ExamService._map_correct_answer(reverse_mapping, item["answer"])
                    else:
                        # No shuffle_map available (old records where option_map was lost
                        # when record.answers was overwritten).  When the answer is correct,
                        # the stored answer (in display keys) is equivalent to the correct
                        # answer (in original keys).  Show the correct answer so the displayed
                        # keys match the displayed (original-order) options.
                        if item.get("is_correct") is True:
                            item["answer"] = q.correct_answer
            enriched.append(item)
        data["answers"] = enriched
        return data

    @staticmethod
    def get_wrong_questions(db: Session, user_id: str, exam_id: str | None = None,
                            question_bank_id: str | None = None):
        """Collect the user's wrong questions across their exam attempts (错题集).

        Aggregates distinct questions that were answered incorrectly, with the
        user's latest wrong answer and the correct answer.
        """
        stmt = select(ExamRecord).where(ExamRecord.user_id == user_id)
        if exam_id:
            stmt = stmt.where(ExamRecord.exam_id == exam_id)
        records = db.execute(stmt).scalars().all()

        # Preload all question banks for resolving bank name (fallback 未分类).
        banks = {b.id: b for b in db.execute(select(QuestionBank)).scalars().all()}

        wrong_map = {}  # question_id -> aggregated info
        for rec in records:
            answers = rec.answers or []
            shuffle_map = rec.shuffle_map or {}
            exam = db.execute(select(Exam).where(Exam.id == rec.exam_id)).scalar_one_or_none()
            exam_title = exam.title if exam else ""
            for a in answers:
                if not isinstance(a, dict):
                    continue
                qid = a.get("question_id")
                if not qid or a.get("is_correct", False):
                    continue
                q = db.execute(select(Question).where(Question.id == qid)).scalar_one_or_none()
                if not q:
                    continue
                # Filter by question bank (question_bank_id), skip if it doesn't match.
                if question_bank_id and q.question_bank_id != question_bank_id:
                    continue
                bank = banks.get(q.question_bank_id)
                # Reconstruct displayed options, answer and correct answer using this attempt's shuffle map
                display_options = q.options
                correct_answer = q.correct_answer
                my_answer = a.get("answer")
                mapping = shuffle_map.get(str(qid))
                if mapping:
                    disp = []
                    reverse_mapping = {}
                    for display_key, original_key in mapping.items():
                        reverse_mapping[original_key] = display_key
                        opt = next((o for o in (q.options or []) if o.get("key") == original_key), None)
                        if opt:
                            disp.append({"key": display_key, "text": opt["text"]})
                    if disp:
                        display_options = disp
                    correct_answer = ExamService._map_correct_answer(reverse_mapping, q.correct_answer)
                    my_answer = ExamService._map_correct_answer(reverse_mapping, my_answer)
                # Keep latest wrong attempt
                wrong_map[qid] = {
                    "question_id": qid,
                    "question_content": q.content,
                    "question_bank_id": q.question_bank_id,
                    "question_bank_name": bank.name if bank else "未分类",
                    "question_type": q.question_type.value if hasattr(q.question_type, "value") else q.question_type,
                    "options": display_options,
                    "correct_answer": correct_answer,
                    "explanation": q.explanation,
                    "my_answer": my_answer,
                    "wrong_count": wrong_map.get(qid, {}).get("wrong_count", 0) + 1,
                    "exam_id": rec.exam_id,
                    "exam_title": exam_title,
                    "exam_time": rec.submitted_at,
                }
        return list(wrong_map.values())

    @staticmethod
    def get_exam_analysis(db: Session, exam_id: str):
        """EX-07: exam result analysis."""
        records = db.execute(
            select(ExamRecord).where(
                ExamRecord.exam_id == exam_id, ExamRecord.status == ExamStatus.graded
            )
        ).scalars().all()

        if not records:
            return {"total_records": 0, "average_score": 0, "pass_rate": 0,
                    "score_distribution": {}, "question_error_rates": {}}

        scores = [r.total_score or 0 for r in records]
        avg = sum(scores) / len(scores)
        passed = sum(1 for r in records if r.is_pass)

        # Score distribution
        dist = {"0-60": 0, "60-70": 0, "70-80": 0, "80-90": 0, "90-100": 0}
        for s in scores:
            if s < 60: dist["0-60"] += 1
            elif s < 70: dist["60-70"] += 1
            elif s < 80: dist["70-80"] += 1
            elif s < 90: dist["80-90"] += 1
            else: dist["90-100"] += 1

        # Question error rates
        error_counts = Counter()
        total_counts = Counter()
        for r in records:
            for ans in (r.answers or []):
                qid = ans.get("question_id")
                if qid:
                    total_counts[qid] += 1
                    if ans.get("is_correct") is False:
                        error_counts[qid] += 1

        error_rates = {qid: error_counts[qid] / total_counts[qid] for qid in total_counts}

        return {
            "total_records": len(records),
            "average_score": round(avg, 1),
            "pass_rate": round(passed / len(records) * 100, 1),
            "score_distribution": dist,
            "question_error_rates": error_rates,
        }


class QuestionBankService:

    @staticmethod
    def list_banks(db: Session):
        stmt = select(QuestionBank).order_by(QuestionBank.created_at.desc())
        banks = list(db.execute(stmt).scalars().all())
        # Count questions per bank
        result = []
        for b in banks:
            count = db.execute(
                select(func.count()).select_from(
                    select(Question).where(Question.question_bank_id == b.id).subquery()
                )
            ).scalar() or 0
            result.append((b, count))
        return result

    @staticmethod
    def get_bank(db: Session, bank_id: str):
        return db.execute(select(QuestionBank).where(QuestionBank.id == bank_id)).scalar_one_or_none()

    @staticmethod
    def create_bank(db: Session, body: QuestionBankCreate, creator_id: str):
        bank = QuestionBank(name=body.name, description=body.description, created_by=creator_id)
        db.add(bank)
        db.flush()
        return bank

    @staticmethod
    def update_bank(db: Session, bank: QuestionBank, body: QuestionBankUpdate):
        if body.name is not None:
            bank.name = body.name
        if body.description is not None:
            bank.description = body.description
        db.flush()
        return bank

    @staticmethod
    def delete_bank(db: Session, bank: QuestionBank):
        # Unlink questions from this bank before deleting
        db.execute(
            Question.__table__.update().where(Question.question_bank_id == bank.id).values(question_bank_id=None)
        )
        db.delete(bank)
        db.flush()

    @staticmethod
    def import_excel(db: Session, bank_id: str, file_bytes: bytes, creator_id: str):
        """Import questions from an Excel file into a question bank."""
        import io
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(min_row=1, values_only=True))
        if not rows:
            raise ValueError("Excel文件为空")

        # Header row: find column indices by Chinese header names
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]

        type_map = {
            "单选": QuestionType.single_choice,
            "多选": QuestionType.multiple_choice,
            "判断": QuestionType.true_false,
            "填空": QuestionType.fill_blank,
            "简答": QuestionType.short_answer,
        }

        col_map = {}
        header_aliases = {
            "question_type": ["题型", "type"],
            "content": ["题干", "content"],
            "option_a": ["选项A", "选项a"],
            "option_b": ["选项B", "选项b"],
            "option_c": ["选项C", "选项c"],
            "option_d": ["选项D", "选项d"],
            "option_e": ["选项E", "选项e"],
            "correct_answer": ["正确答案", "answer"],
            "score": ["分值", "score"],
            "difficulty": ["难度", "difficulty"],
            "knowledge_point": ["知识点", "knowledge_point"],
            "explanation": ["解析", "explanation"],
        }

        for key, aliases in header_aliases.items():
            for i, h in enumerate(headers):
                if h in aliases:
                    col_map[key] = i
                    break

        if "content" not in col_map:
            raise ValueError("未找到“题干”列，请检查Excel模板是否正确")
        if "question_type" not in col_map:
            raise ValueError("未找到“题型”列，请检查Excel模板是否正确")
        if "correct_answer" not in col_map:
            raise ValueError("未找到“正确答案”列，请检查Excel模板是否正确")

        created_questions = []
        errors = []
        skipped = 0

        for row_idx, row in enumerate(rows[1:], start=2):
            # Skip empty rows
            if row is None or all(c is None or str(c).strip() == "" for c in row):
                skipped += 1
                continue

            def get_cell(key):
                idx = col_map.get(key)
                if idx is None or idx >= len(row):
                    return None
                val = row[idx]
                return str(val).strip() if val is not None else ""

            q_type_str = get_cell("question_type")
            q_content = get_cell("content")
            if not q_content:
                skipped += 1
                continue

            q_type = type_map.get(q_type_str)
            if not q_type:
                errors.append(f"第{row_idx}行: 未知题型“{q_type_str}”")
                continue

            # Build options for choice questions
            options = None
            correct_answer = None
            answer_raw = get_cell("correct_answer") or ""

            if q_type in (QuestionType.single_choice, QuestionType.multiple_choice):
                opt_texts = []
                for letter in "ABCDE":
                    txt = get_cell(f"option_{letter.lower()}")
                    if txt:
                        opt_texts.append((letter, txt))
                if not opt_texts:
                    errors.append(f"第{row_idx}行: 选择题缺少选项")
                    continue
                options = [{"key": k, "text": t} for k, t in opt_texts]

                if q_type == QuestionType.single_choice:
                    correct_answer = answer_raw.upper().strip()
                else:
                    # Multiple choice: split by comma
                    parts = [p.strip().upper() for p in answer_raw.split(",") if p.strip()]
                    correct_answer = parts

            elif q_type == QuestionType.true_false:
                tf = answer_raw.strip()
                if tf in ("正确", "对", "true", "T", "Y"):
                    correct_answer = "true"
                elif tf in ("错误", "错", "false", "F", "N"):
                    correct_answer = "false"
                else:
                    errors.append(f"第{row_idx}行: 判断题答案“{tf}”无法识别")
                    continue

            elif q_type == QuestionType.fill_blank:
                # Multiple blanks separated by semicolons
                blanks = [b.strip() for b in answer_raw.split(";") if b.strip()]
                correct_answer = blanks if len(blanks) > 1 else answer_raw

            else:  # short_answer
                correct_answer = answer_raw

            # Parse score
            score_str = get_cell("score") or "1"
            try:
                score_val = float(score_str)
            except ValueError:
                score_val = 1.0

            # Parse difficulty
            diff_str = get_cell("difficulty") or "1"
            try:
                diff_val = int(float(diff_str))
            except ValueError:
                diff_val = 1

            is_obj = q_type in (QuestionType.single_choice, QuestionType.multiple_choice,
                                 QuestionType.true_false, QuestionType.fill_blank)

            q = Question(
                question_type=q_type, content=q_content,
                options=options, correct_answer=correct_answer,
                explanation=get_cell("explanation") or None,
                difficulty=diff_val,
                knowledge_point=get_cell("knowledge_point") or None,
                score=score_val, is_objective=is_obj,
                created_by=creator_id, question_bank_id=bank_id,
            )
            db.add(q)
            created_questions.append(q)

        db.flush()
        wb.close()

        return created_questions, errors, skipped
