from datetime import datetime
from pydantic import BaseModel


class CertificateResponse(BaseModel):
    id: str
    course_id: str
    user_id: str
    exam_record_id: str
    number: str
    student_name: str
    course_title: str
    platform_name: str
    issued_at: datetime

    model_config = {"from_attributes": True}


class CertificateStatus(BaseModel):
    enabled: bool
    eligible: bool
    reasons: list[str]
    certificate: CertificateResponse | None = None
