from datetime import datetime, timezone

from pydantic import AwareDatetime, BaseModel, Field, field_validator


class HomeworkWrite(BaseModel):
    model_config = {"extra": "forbid"}
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=20000)
    due_at: AwareDatetime
    max_score: float = Field(gt=0, le=10000, allow_inf_nan=False)
    grading_notes: str = Field(default="", max_length=5000)
    is_required: bool = True

    @field_validator("title", "description")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("标题和要求不能为空")
        return value.strip()


class GradeWrite(BaseModel):
    model_config = {"extra": "forbid"}
    score: float = Field(ge=0, allow_inf_nan=False)
    feedback: str = Field(default="", max_length=5000)


class SubmissionResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    user_id: str
    homework_id: str
    text: str
    attachment_name: str | None
    submitted_at: datetime
    score: float | None
    feedback: str | None
    graded_at: datetime | None
    full_name: str | None = None

    @field_validator("submitted_at", "graded_at")
    @classmethod
    def utc_timestamp(cls, value):
        return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


class HomeworkResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    course_id: str
    title: str
    description: str
    due_at: datetime
    max_score: float
    grading_notes: str
    is_required: bool
    submission: SubmissionResponse | None = None

    @field_validator("due_at")
    @classmethod
    def utc_timestamp(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
