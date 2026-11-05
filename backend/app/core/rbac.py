"""RBAC enforcement: permission checking."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.role import Permission, Role, UserRole, role_permissions
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
