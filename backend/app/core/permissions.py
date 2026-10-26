"""Permission code constants and builtin role definitions.

Permission codes follow the pattern: module:action
(e.g. 'user:create', 'course:delete', 'report:export')
"""


class Perm:
    """All permission codes used across the system."""

    # User management
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Organization
    ORG_READ = "org:read"
    ORG_MANAGE = "org:manage"

    # Course management
    COURSE_READ = "course:read"
    COURSE_CREATE = "course:create"
    COURSE_UPDATE = "course:update"
    COURSE_DELETE = "course:delete"
    COURSE_PUBLISH = "course:publish"

    # Learning management
    LEARNING_READ = "learning:read"
    LEARNING_ASSIGN = "learning:assign"
    LEARNING_MANAGE = "learning:manage"

    # Exam
    EXAM_READ = "exam:read"
    EXAM_CREATE = "exam:create"
    EXAM_GRADE = "exam:grade"

    # Reports
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"

    # System
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"


class RoleCode:
    """Builtin role codes."""

    LEARNER = "learner"
    MANAGER = "manager"
    ADMIN = "admin"
    AUTHOR = "author"
    SYSADMIN = "sysadmin"


# Builtin role -> default permissions mapping (used for seeding)
BUILTIN_ROLE_PERMISSIONS: dict[str, list[str]] = {
    RoleCode.LEARNER: [
        Perm.COURSE_READ,
        Perm.LEARNING_READ,
        Perm.EXAM_READ,
        Perm.REPORT_READ,
    ],
    RoleCode.MANAGER: [
        Perm.USER_READ,
        Perm.COURSE_READ,
        Perm.LEARNING_READ,
        Perm.LEARNING_ASSIGN,
        Perm.EXAM_READ,
        Perm.REPORT_READ,
        Perm.REPORT_EXPORT,
    ],
    RoleCode.ADMIN: [
        Perm.USER_READ, Perm.USER_CREATE, Perm.USER_UPDATE, Perm.USER_DELETE,
        Perm.ORG_READ, Perm.ORG_MANAGE,
        Perm.COURSE_READ, Perm.COURSE_CREATE, Perm.COURSE_UPDATE,
        Perm.COURSE_DELETE, Perm.COURSE_PUBLISH,
        Perm.LEARNING_READ, Perm.LEARNING_ASSIGN, Perm.LEARNING_MANAGE,
        Perm.EXAM_READ, Perm.EXAM_CREATE, Perm.EXAM_GRADE,
        Perm.REPORT_READ, Perm.REPORT_EXPORT,
    ],
    RoleCode.AUTHOR: [
        Perm.COURSE_READ, Perm.COURSE_CREATE, Perm.COURSE_UPDATE,
        Perm.COURSE_PUBLISH,
    ],
    RoleCode.SYSADMIN: [
        Perm.USER_READ, Perm.USER_CREATE, Perm.USER_UPDATE, Perm.USER_DELETE,
        Perm.ORG_READ, Perm.ORG_MANAGE,
        Perm.SYSTEM_CONFIG, Perm.SYSTEM_AUDIT,
        Perm.REPORT_READ, Perm.REPORT_EXPORT,
    ],
}
