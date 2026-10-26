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
    Perm.ORG_READ: ("View organizations", "org"),
    Perm.ORG_MANAGE: ("Manage organizations", "org"),
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
    "learner": "\u666e\u901a\u5458\u5de5",
    "manager": "\u90e8\u95e8\u7ba1\u7406\u8005",
    "admin": "\u57f9\u8bad\u7ba1\u7406\u5458",
    "author": "\u5185\u5bb9\u521b\u4f5c\u8005",
    "sysadmin": "\u7cfb\u7edf\u7ba1\u7406\u5458",
}

ROLE_DESCRIPTIONS = {
    "learner": "\u67e5\u770b\u8bfe\u7a0b\u3001\u5b66\u4e60\u3001\u8003\u8bd5\u3001\u4e2a\u4eba\u6863\u6848",
    "manager": "\u7ba1\u7406\u672c\u90e8\u95e8\u5b66\u4e60\u8fdb\u5ea6\u3001\u5206\u914d\u8bfe\u7a0b\u3001\u5ba1\u6279\u7533\u8bf7",
    "admin": "\u7ba1\u7406\u8bfe\u7a0b\u5e93\u3001\u5b66\u4e60\u8def\u5f84\u3001\u8003\u8bd5\u3001\u8bc1\u4e66\u3001\u5168\u516c\u53f8\u62a5\u8868",
    "author": "\u521b\u5efa\u548c\u7f16\u8f91\u8bfe\u7a0b\u5185\u5bb9\u3001\u63d0\u4ea4\u5ba1\u6838",
    "sysadmin": "\u7cfb\u7edf\u914d\u7f6e\u3001SSO\u3001\u65e5\u5fd7\u5ba1\u8ba1\u3001\u6743\u9650\u7ef4\u62a4",
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
        desired_perms = [existing_perms[c] for c in perm_codes if c in existing_perms]
        current_perm_codes = {p.code for p in role.permissions}
        if current_perm_codes != set(perm_codes):
            role.permissions = desired_perms

    db.flush()
    logger.info("RBAC seed complete: %d permissions, %d roles", len(existing_perms), len(existing_roles))


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