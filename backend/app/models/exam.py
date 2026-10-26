"""Exam, Question, and ExamRecord models (EX-01 through EX-07)."""

import enum

from sqlalchemy import (
    CHAR, Boolean, Enum, Float, ForeignKey, Integer, JSON,
    String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class QuestionType(str, enum.Enum):
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    fill_blank = "fill_blank"
    short_answer = "short_answer"


class ExamStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"


class Question(Base, UUIDPrimaryKey, TimestampMixin):
    """A question in the question bank (EX-01)."""

    __tablename__ = "questions"

    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"), index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Options for choice questions: [{"key":"A","text":"..."},...]
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Correct answer: "A" for single, ["A","C"] for multiple, "true" for T/F, ["ans1","ans2"] for fill
    correct_answer: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=1)  # 1-5
    knowledge_point: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    score: Mapped[float] = mapped_column(Float, default=1.0)  # points
    # For auto-grading: is this an objective question?
    is_objective: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    question_bank_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class Exam(Base, UUIDPrimaryKey, TimestampMixin):
    """An exam linked to a course or standalone (EX-03)."""

    __tablename__ = "exams"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    course_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # Question IDs for this exam
    question_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. ["q1","q2","q3"] for manual;
    #      {"strategy":"random","rules":[{"question_bank_id":"xxx","count":20},...]} for random per-bank (EX-04)
    question_mode: Mapped[str] = mapped_column(String(20), default="manual")  # "manual" | "random"
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    pass_score: Mapped[float] = mapped_column(Float, default=60.0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=10)
    # EX-05 partial: anti-cheat settings
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=False)
    screen_lock: Mapped[bool] = mapped_column(Boolean, default=False)
    start_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ExamRecord(Base, UUIDPrimaryKey, TimestampMixin):
    """A user's exam attempt with answers and score (EX-06, EX-07)."""

    __tablename__ = "exam_records"

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    exam_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    # Answers: [{"question_id":"...","answer":"A","score":2.0,"is_correct":true,"grader_comment":null}]
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Option shuffle map per question for this attempt: {question_id: {display_key: original_key}}
    shuffle_map: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_pass: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus, name="exam_record_status"), default=ExamStatus.not_started
    )
    started_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    submitted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    graded_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    graded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    # EX-07: result analysis data
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
