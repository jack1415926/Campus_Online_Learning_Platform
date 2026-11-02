"""Import all models so Alembic and SQLAlchemy can discover them."""

from app.models.base import Base
from app.models.platform import PlatformSettings
from app.models.certificate import Certificate
from app.models.communication import DiscussionTopic, DiscussionReply, PrivateMessage
from app.models.homework import Homework, HomeworkSubmission
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
    LearningRecord,
)

__all__ = [
    "Base", "User", "UserStatus",
    "DataScope", "Permission", "Role", "UserRole", "role_permissions",
    "Session", "SessionStatus",
    "Category", "Tag", "MediaAsset", "MediaType",
    "Chapter", "ContentType", "Course", "CourseStatus", "Difficulty", "course_tags",
    "AssignmentType", "CompletionStatus", "CourseAssignment",
    "LearningRecord",

    "Notification", "NotificationChannel", "NotificationStatus",
    "Exam", "ExamRecord", "ExamStatus", "Question", "QuestionType",
    "QuestionBank",
    "MediaCategory",
    "NotificationType",
]
from app.models.notification import (
    Notification, NotificationChannel, NotificationStatus,
    NotificationType,
)

from app.models.exam import (
    Exam, ExamRecord, ExamStatus, Question, QuestionType,
)
from app.models.question_bank import QuestionBank
from app.models.media_category import MediaCategory
