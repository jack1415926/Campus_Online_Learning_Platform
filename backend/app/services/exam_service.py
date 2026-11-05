"""Exam service."""


from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.exam import Exam, ExamRecord, Question, QuestionType
from app.schemas.exam import (
    QuestionBankCreate, QuestionBankUpdate,
    QuestionCreate,
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
                                         QuestionType.true_false)
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
    def delete_question(db: Session, q: Question):
        db.delete(q)
        db.flush()


class ExamService:


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
