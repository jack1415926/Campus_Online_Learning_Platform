"""Schemas for exams (EX-01 through EX-07)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.exam import ExamStatus, QuestionType


class QuestionBase(BaseModel):
    question_type: QuestionType
    content: str
    options: list | None = None
    correct_answer: str | list | None = None
    explanation: str | None = None
    difficulty: int = 1
    knowledge_point: str | None = None
    score: float = 1.0
    question_bank_id: str | None = None


class QuestionCreate(QuestionBase):
    pass


class QuestionResponse(QuestionBase):
    id: str
    is_objective: bool
    created_by: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class QuestionImportItem(BaseModel):
    """Single question for batch import (EX-02)."""
    question_type: QuestionType
    content: str
    options: list | None = None
    correct_answer: str | list | None = None
    difficulty: int = 1
    knowledge_point: str | None = None
    score: float = 1.0


class RandomRule(BaseModel):
    """Random question rule: pick `count` questions from a bank."""
    question_bank_id: str
    count: int = Field(5, ge=1)


class ExamBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    course_id: str | None = None
    question_ids: list | dict | None = None
    question_mode: str = "manual"  # "manual" | "random"
    random_rules: list[RandomRule] | None = None
    duration_minutes: int = 60
    pass_score: float = 60.0
    max_attempts: int = 10
    shuffle_questions: bool = False
    shuffle_options: bool = False
    screen_lock: bool = False
    start_time: str | None = None
    end_time: str | None = None


class ExamCreate(ExamBase):
    pass


class ExamResponse(ExamBase):
    id: str
    status: str
    created_by: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class SubmitAnswerItem(BaseModel):
    question_id: str
    answer: str | list | None = None


class SubmitExamRequest(BaseModel):
    """Submit exam answers for grading (EX-06)."""
    answers: list[SubmitAnswerItem] = []
    time_spent_seconds: int | None = None


class GradeAnswerItem(BaseModel):
    """Manual grading for subjective questions (EX-06)."""
    question_id: str
    score: float
    grader_comment: str | None = None


class GradeExamRequest(BaseModel):
    answers: list[GradeAnswerItem] = []


class ExamRecordResponse(BaseModel):
    id: str
    user_id: str
    exam_id: str
    answers: list | dict | None = None
    total_score: float
    max_score: float
    is_pass: bool | None = None
    status: ExamStatus
    started_at: str | None = None
    submitted_at: str | None = None
    attempt_number: int
    created_at: datetime
    model_config = {"from_attributes": True}


class ExamResultAnalysis(BaseModel):
    """EX-07: exam result analysis."""
    total_records: int = 0
    average_score: float = 0.0
    pass_rate: float = 0.0
    score_distribution: dict = {}  # {"0-60": 5, "60-80": 10, ...}
    question_error_rates: dict = {}  # {"question_id": 0.35, ...}

# --- Question Bank (question bank categories) ---


class QuestionBankBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None


class QuestionBankCreate(QuestionBankBase):
    pass


class QuestionBankUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None


class QuestionBankResponse(QuestionBankBase):
    id: str
    created_by: str | None = None
    created_at: datetime
    question_count: int = 0
    model_config = {"from_attributes": True}
