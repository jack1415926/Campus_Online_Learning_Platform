"""Permission code constants and builtin role definitions.

Permission codes follow the pattern: module:action
(e.g. 'user:create', 'course:delete')
"""


class Perm:
    """All permission codes used across the system."""

    # User management
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Course management
    COURSE_READ = "course:read"
    COURSE_CREATE = "course:create"
    COURSE_UPDATE = "course:update"
    COURSE_DELETE = "course:delete"
    COURSE_PUBLISH = "course:publish"

    # Learning management
    LEARNING_READ = "learning:read"

    # Exam
    EXAM_READ = "exam:read"
    EXAM_CREATE = "exam:create"
    EXAM_GRADE = "exam:grade"


    # System
    SYSTEM_CONFIG = "system:config"


class RoleCode:
    """Campus builtin role codes."""

    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


# Campus exam permissions are enforced together with course ownership/membership.
BUILTIN_ROLE_PERMISSIONS = {
    RoleCode.STUDENT: [Perm.COURSE_READ, Perm.LEARNING_READ, Perm.EXAM_READ],
    RoleCode.TEACHER: [Perm.COURSE_READ, Perm.COURSE_CREATE, Perm.COURSE_UPDATE, Perm.COURSE_DELETE, Perm.LEARNING_READ, Perm.EXAM_READ, Perm.EXAM_CREATE, Perm.EXAM_GRADE],
    RoleCode.ADMIN: [value for name, value in vars(Perm).items() if name.isupper()],
}
