"""Schemas for exams."""

from datetime import datetime
import math

from pydantic import AwareDatetime, BaseModel, Field, model_validator

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
    model_config = {"extra": "forbid"}
    content: str = Field(min_length=1, max_length=20000)
    score: float = Field(default=1, gt=0, le=10000, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid_question(self):
        if not self.content.strip():
            raise ValueError("请填写题干，只支持单选、多选、判断和简答")
        if self.question_type in (QuestionType.single_choice, QuestionType.multiple_choice):
            options = self.options or []
            if not 2 <= len(options) <= 26 or any(not isinstance(o,dict) or not isinstance(o.get("text"),str) or not o["text"].strip() or o.get("key") not in list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for o in options):
                raise ValueError("选择题至少两个有效选项，选项标识使用A到Z")
            keys = [o["key"] for o in options]
            answers = self.correct_answer if isinstance(self.correct_answer,list) else [self.correct_answer]
            if len(set(keys)) != len(keys) or not answers or any(not isinstance(a,str) or a not in keys for a in answers) or len(set(answers)) != len(answers):
                raise ValueError("选项标识不能重复，正确答案必须属于选项")
            if self.question_type == QuestionType.single_choice and not isinstance(self.correct_answer,str):
                raise ValueError("单选题需要一个答案")
            if self.question_type == QuestionType.multiple_choice and not isinstance(self.correct_answer,list):
                raise ValueError("多选题答案需要选项列表")
        elif self.question_type == QuestionType.true_false:
            if self.correct_answer not in ("true", "false"):
                raise ValueError("判断题答案为true或false")
            self.options = None
        else:
            if not isinstance(self.correct_answer,str) or not self.correct_answer.strip():
                raise ValueError("请填写简答题参考答案")
            self.options = None
        return self


class QuestionResponse(QuestionBase):
    id: str
    is_objective: bool
    created_by: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ExamBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    course_id: str | None = None
    question_ids: list[str] | None = None
    duration_minutes: int = 60
    pass_score: float = 60.0
    max_attempts: int = 10
    start_time: str | None = None
    end_time: str | None = None
    grading_notes: str | None = None


class ExamCreate(ExamBase):
    model_config = {"extra": "forbid"}
    title: str = Field(min_length=1, max_length=255)
    course_id: str
    question_ids: list[str] = Field(min_length=1, max_length=100)
    question_scores: dict[str, float] = {}
    start_time: AwareDatetime
    end_time: AwareDatetime
    duration_minutes: int = Field(default=60, ge=1, le=300)
    max_attempts: int = Field(default=1, ge=1, le=10)
    pass_score: float = Field(default=60, ge=0, le=100, allow_inf_nan=False)
    grading_notes: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def valid_exam(self):
        if not self.title.strip() or self.end_time <= self.start_time:
            raise ValueError("标题不能为空，结束时间须晚于开始时间")
        if len(set(self.question_ids)) != len(self.question_ids):
            raise ValueError("试卷题目不能重复")
        if any(q not in self.question_ids or not math.isfinite(s) or not 0 < s <= 10000 for q,s in self.question_scores.items()):
            raise ValueError("题目分值须大于0且属于试卷")
        return self


class ExamResponse(ExamBase):
    question_scores: dict[str, float] = {}
    id: str
    status: str
    created_by: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class SubmitAnswerItem(BaseModel):
    model_config = {"extra": "forbid"}
    question_id: str
    answer: str | list | None = None


class SubmitExamRequest(BaseModel):
    """Submit exam answers for grading."""
    model_config = {"extra": "forbid"}
    answers: list[SubmitAnswerItem] = Field(default_factory=list, max_length=100)
    time_spent_seconds: int | None = None


class GradeAnswerItem(BaseModel):
    """Manual grading for subjective questions."""
    question_id: str
    model_config = {"extra": "forbid"}
    score: float = Field(ge=0, allow_inf_nan=False)
    grader_comment: str | None = Field(None, max_length=5000)


class GradeExamRequest(BaseModel):
    model_config = {"extra": "forbid"}
    answers: list[GradeAnswerItem] = Field(min_length=1, max_length=100)


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
    deadline_at: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


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
