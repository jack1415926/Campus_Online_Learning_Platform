"""Exam service (EX-01 through EX-07)."""

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.exam import Exam, ExamRecord, ExamStatus, Question, QuestionType
from app.schemas.exam import (
    QuestionBankCreate, QuestionBankUpdate,
    QuestionCreate, QuestionImportItem,
)
from app.models.question_bank import QuestionBank


class QuestionService:

    @staticmethod
    def list_questions(db: Session, question_type=None, knowledge_point=None, page=1, page_size=20, question_bank_id=None, creator_id=None):
        stmt = select(Question)
        if creator_id is not None:
            stmt = stmt.where(Question.created_by == creator_id)
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
    def delete_exam(db: Session, exam: Exam):
        db.delete(exam)
        db.flush()




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
    def list_banks(db: Session, creator_id=None):
        stmt = select(QuestionBank).order_by(QuestionBank.created_at.desc())
        if creator_id is not None:
            stmt = stmt.where(QuestionBank.created_by == creator_id)
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
