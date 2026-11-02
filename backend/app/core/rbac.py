"""RBAC enforcement: permission checking and data-scope filtering."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.role import DataScope, Permission, Role, UserRole, role_permissions
from app.models.user import User


def load_user_permissions(db: Session, user_id: str) -> set[str]:
    stmt = (
        select(Permission.code)
        .select_from(Permission)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .join(Role, Role.id == role_permissions.c.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    return {row[0] for row in db.execute(stmt).all()}


def load_user_data_scope(db: Session, user_id: str) -> DataScope:
    stmt = select(UserRole.data_scope).where(UserRole.user_id == user_id)
    scopes = [row[0] for row in db.execute(stmt).all()]
    if DataScope.company in scopes:
        return DataScope.company
    if DataScope.department in scopes:
        return DataScope.department
    return DataScope.self


def require_permission(*required_perms: str) -> Callable:
    def _check(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_perms = load_user_permissions(db, user.id)
        if not any(p in user_perms for p in required_perms):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires permission: {', '.join(required_perms)}",
            )
        return user
    return _check


def get_data_scope_filter(db: Session, user: User) -> dict:
    scope = load_user_data_scope(db, user.id)
    if scope == DataScope.company:
        return {}
    return {"user_id": user.id}