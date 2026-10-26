"""Import all models so Alembic and SQLAlchemy can discover them."""

from app.models.base import Base
from app.models.org import Organization
from app.models.dictionary import JobLevel, Position
from app.models.user import User, UserStatus
from app.models.session import Session, SessionStatus
from app.models.role import (
    DataScope, Permission, Role, UserRole, role_permissions,
)
from app.models.category import Category, Tag
from app.models.media import MediaAsset, MediaType
from app.models.course import (
    Chapter, ContentType, Course, CourseStatus, Difficulty, course_tags,
)
from app.models.learning import (
    AssignmentType, CompletionStatus, CourseAssignment,
    LearningPath, LearningRecord, TrainingPlan,
    path_courses, plan_courses,
)

__all__ = [
    "Base", "Organization", "JobLevel", "Position", "User", "UserStatus",
    "DataScope", "Permission", "Role", "UserRole", "role_permissions",
    "Session", "SessionStatus",
    "Category", "Tag", "MediaAsset", "MediaType",
    "Chapter", "ContentType", "Course", "CourseStatus", "Difficulty", "course_tags",
    "AssignmentType", "CompletionStatus", "CourseAssignment",
    "LearningPath", "LearningRecord", "TrainingPlan",
    "path_courses", "plan_courses",
    "Notification", "NotificationChannel", "NotificationStatus",
    "Exam", "ExamRecord", "ExamStatus", "Question", "QuestionType",
    "QuestionBank",
    "MediaCategory",
    "NotificationTemplate", "NotificationType", "TriggerMode",
]
from app.models.notification import (
    Notification, NotificationChannel, NotificationStatus,
    NotificationTemplate, NotificationType, TriggerMode,
)

from app.models.exam import (
    Exam, ExamRecord, ExamStatus, Question, QuestionType,
)
from app.models.question_bank import QuestionBank
from app.models.media_category import MediaCategory
