"""Seed builtin roles, permissions, and role-permission mappings."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import BUILTIN_ROLE_PERMISSIONS, Perm
from app.models.role import DataScope, Permission, Role, UserRole
from app.models.user import User

logger = logging.getLogger(__name__)

PERMISSION_NAMES = {
    Perm.USER_READ: ("View users", "user"),
    Perm.USER_CREATE: ("Create users", "user"),
    Perm.USER_UPDATE: ("Update users", "user"),
    Perm.USER_DELETE: ("Delete users", "user"),
    Perm.COURSE_READ: ("View courses", "course"),
    Perm.COURSE_CREATE: ("Create courses", "course"),
    Perm.COURSE_UPDATE: ("Update courses", "course"),
    Perm.COURSE_DELETE: ("Delete courses", "course"),
    Perm.COURSE_PUBLISH: ("Publish/unpublish courses", "course"),
    Perm.LEARNING_READ: ("View learning records", "learning"),
    Perm.LEARNING_ASSIGN: ("Assign courses", "learning"),
    Perm.LEARNING_MANAGE: ("Manage learning plans", "learning"),
    Perm.EXAM_READ: ("View exams", "exam"),
    Perm.EXAM_CREATE: ("Create exams", "exam"),
    Perm.EXAM_GRADE: ("Grade exams", "exam"),
    Perm.REPORT_READ: ("View reports", "report"),
    Perm.REPORT_EXPORT: ("Export reports", "report"),
    Perm.SYSTEM_CONFIG: ("System configuration", "system"),
    Perm.SYSTEM_AUDIT: ("View audit logs", "system"),
}

ROLE_NAMES = {
    "student": "学生",
    "teacher": "教师",
    "admin": "管理员",
}

ROLE_DESCRIPTIONS = {
    "student": "浏览课程、加入学习和个人资料",
    "teacher": "管理本人课程、提交审核",
    "admin": "审核与平台管理",
}


def seed_rbac(db: Session) -> None:
    """Idempotently seed all builtin permissions and roles."""
    existing_perms = {p.code: p for p in db.execute(select(Permission)).scalars().all()}

    for code, (name, module) in PERMISSION_NAMES.items():
        if code not in existing_perms:
            perm = Permission(code=code, name=name, module=module)
            db.add(perm)
            existing_perms[code] = perm

    db.flush()

    existing_roles = {
        r.code: r
        for r in db.execute(
            select(Role).where(Role.is_builtin == True).options(selectinload(Role.permissions))
        ).scalars().all()
    }

    for role_code, perm_codes in BUILTIN_ROLE_PERMISSIONS.items():
        if role_code not in existing_roles:
            role = Role(
                code=role_code,
                name=ROLE_NAMES.get(role_code, role_code),
                description=ROLE_DESCRIPTIONS.get(role_code, ""),
                is_builtin=True,
            )
            db.add(role)
            db.flush()
            db.refresh(role, ["permissions"])
            existing_roles[role_code] = role

        role = existing_roles[role_code]
        role.name = ROLE_NAMES[role_code]
        role.description = ROLE_DESCRIPTIONS[role_code]
        desired_perms = [existing_perms[c] for c in perm_codes if c in existing_perms]
        current_perm_codes = {p.code for p in role.permissions}
        if current_perm_codes != set(perm_codes):
            role.permissions = desired_perms

    db.flush()
    # Migration b1c2d3e4f5a6 deliberately keeps a legacy role that still binds users or grants
    # permissions, so translate those bindings here instead of silently dropping their access.
    for old_code, new_code in {"learner": "student", "manager": "student", "author": "teacher", "sysadmin": "admin"}.items():
        old_role = existing_roles.get(old_code)
        if old_role is None:
            continue
        for binding in db.execute(select(UserRole).where(UserRole.role_id == old_role.id)).scalars().all():
            user = db.get(User, binding.user_id)
            assign_role(db, user, new_code, DataScope.company if new_code == "admin" else DataScope.self)
            user.requested_role = new_code
            if new_code == "teacher":
                user.teacher_review_status = "approved"
            db.delete(binding)
        old_role.permissions = []
    db.flush()
    logger.info("Campus RBAC seed complete")


def assign_role(db: Session, user: User, role_code: str, data_scope: DataScope = DataScope.self) -> None:
    """Assign a builtin role to a user with a data scope."""
    role = db.execute(select(Role).where(Role.code == role_code)).scalar_one_or_none()
    if not role:
        raise ValueError(f"Role '{role_code}' not found")

    existing = db.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    ).scalar_one_or_none()

    if existing:
        existing.data_scope = data_scope
    else:
        db.add(UserRole(user_id=user.id, role_id=role.id, data_scope=data_scope))

    db.flush()
