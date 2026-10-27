"""Schemas for learning management (LM-01 through LM-09)."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator
import math

from app.models.learning import AssignmentType, CompletionStatus


class TrainingPlanBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    target_audience: dict | None = None
    start_date: str | None = None
    end_date: str | None = None
    completion_requirement: dict | None = None


class TrainingPlanCreate(TrainingPlanBase):
    course_ids: list[str] = []


class TrainingPlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_audience: dict | None = None
    start_date: str | None = None
    end_date: str | None = None
    completion_requirement: dict | None = None
    course_ids: list[str] | None = None


class TrainingPlanResponse(TrainingPlanBase):
    id: str
    status: str
    created_by: str | None = None
    created_at: datetime
    course_ids: list[str] = []
    model_config = {"from_attributes": True}


class LearningPathBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None
    target_job_level: str | None = None
    target_position: str | None = None
    deadline_days: int | None = None


class LearningPathCreate(LearningPathBase):
    course_ids: list[str] = []


class LearningPathUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target_job_level: str | None = None
    target_position: str | None = None
    deadline_days: int | None = None
    course_ids: list[str] | None = None


class LearningPathResponse(LearningPathBase):
    id: str
    status: str
    created_by: str | None = None
    created_at: datetime
    course_ids: list[str] = []
    model_config = {"from_attributes": True}


class CourseAssignmentCreate(BaseModel):
    course_id: str
    assignment_type: AssignmentType
    target_id: str
    deadline: str | None = None
    is_required: bool = True
    training_plan_id: str | None = None


class CourseAssignmentResponse(BaseModel):
    course_title: str | None = None
    id: str
    course_id: str
    assignment_type: AssignmentType
    target_id: str
    deadline: str | None = None
    is_required: bool
    training_plan_id: str | None = None
    assigned_by: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ProgressUpdateRequest(BaseModel):
    course_id: str
    chapter_id: str | None = None
    learning_seconds: int = Field(default=0, ge=0, le=86400)
    progress_percent: float = Field(default=0.0, ge=0, le=100, allow_inf_nan=False)
    resume_position: dict | None = None
    min_watch_seconds: int | None = None

    @field_validator("resume_position")
    @classmethod
    def valid_position(cls, value):
        if value and "video_time" in value:
            position = value["video_time"]
            if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position) or not 0 <= position <= 2592000:
                raise ValueError("视频播放位置无效")
        return value


class LearningRecordResponse(BaseModel):
    id: str
    user_id: str
    course_id: str
    chapter_id: str | None = None
    learning_seconds: int
    progress_percent: float
    resume_position: dict | None = None
    status: CompletionStatus
    started_at: str | None = None
    completed_at: str | None = None
    last_accessed_at: str | None = None
    model_config = {"from_attributes": True}


class ExamProgressItem(BaseModel):
    exam_id: str
    title: str = ""
    passed: bool = False
    attempts: int = 0
    max_attempts: int = 10
    remaining: int = 10


class CourseProgressResponse(BaseModel):
    course_id: str
    total_chapters: int = 0
    completed_chapters: int = 0
    overall_percent: float = 0.0
    total_learning_seconds: int = 0
    status: CompletionStatus = CompletionStatus.not_started
    is_complete: bool = False
    exam_required: bool = False
    can_take_exam: bool = False
    all_exams_passed: bool = True
    exams: list[ExamProgressItem] = []
