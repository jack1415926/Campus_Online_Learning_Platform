"""Schemas for reports and analytics (RPT-01 through RPT-08)."""

from pydantic import BaseModel


class PersonalReport(BaseModel):
    """RPT-01: personal learning report."""
    user_id: str
    user_name: str = ""
    total_courses: int = 0
    completed_courses: int = 0
    total_learning_seconds: int = 0
    completion_rate: float = 0.0
    exam_count: int = 0
    exam_average_score: float = 0.0
    certificates: list = []


class DepartmentReport(BaseModel):
    """RPT-02: department/team report."""
    department_id: str
    department_name: str = ""
    member_count: int = 0
    average_learning_seconds: int = 0
    completion_rate: float = 0.0
    overdue_count: int = 0


class CourseReport(BaseModel):
    """RPT-03: course report."""
    course_id: str
    course_title: str = ""
    enrolled_count: int = 0
    completed_count: int = 0
    completion_rate: float = 0.0
    average_score: float = 0.0
    average_rating: float = 0.0


class TrainingPlanReport(BaseModel):
    """RPT-04: training plan report."""
    plan_id: str
    plan_name: str = ""
    total_courses: int = 0
    overall_progress: float = 0.0
    enrolled_count: int = 0
    completed_count: int = 0


class ComplianceReport(BaseModel):
    """RPT-08: compliance audit report."""
    period_start: str = ""
    period_end: str = ""
    total_users: int = 0
    total_records: int = 0
    total_exams: int = 0
    records: list = []
