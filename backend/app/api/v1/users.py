"""User management API endpoints (UM-03, UM-04, UM-05)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm, RoleCode
from app.core.rbac import require_permission
from app.database import get_db
from app.models.org import Organization
from app.models.role import DataScope
from app.models.user import User, UserStatus
from app.schemas.common import PageMeta, PageResponse
from app.schemas.user import (
    UserCreateRequest,
    UserGroupFilter,
    UserResponse,
    UserUpdateRequest,
)
from pydantic import BaseModel

from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

def _load_user_roles(db: Session, user_ids: list) -> dict:
    """Batch load role codes for multiple users."""
    from app.models.role import Role, UserRole
    from sqlalchemy import select as _select
    stmt = (
        _select(UserRole.user_id, Role.code)
        .join(Role, UserRole.role_id == Role.id)
        .where(UserRole.user_id.in_(user_ids))
    )
    result = {}
    for uid, code in db.execute(stmt).all():
        result.setdefault(str(uid), []).append(code)
    return result


def _load_department_names(db: Session, department_ids: list) -> dict:
    """Batch load organization names by their IDs."""
    ids = [d for d in department_ids if d]
    if not ids:
        return {}
    stmt = select(Organization.id, Organization.name).where(Organization.id.in_(ids))
    return {str(oid): name for oid, name in db.execute(stmt).all()}


def _user_response_with_roles(db: Session, user: User) -> UserResponse:
    """Build UserResponse with roles populated."""
    resp = UserResponse.model_validate(user)
    roles_map = _load_user_roles(db, [str(user.id)])
    resp.roles = roles_map.get(str(user.id), [])
    if user.department_id:
        dept_names = _load_department_names(db, [user.department_id])
        resp.department_name = dept_names.get(str(user.department_id))
    return resp




# --- Personal Center (UM-05) ---

@router.get("/me/profile", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's full profile (UM-05 personal center)."""
    return current_user


@router.put("/me/profile", response_model=UserResponse)
def update_my_profile(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's own profile."""
    updated = UserService.update_user(db, current_user, body)
    db.commit()
    return updated


# --- User CRUD (UM-03) ---

@router.get("", response_model=PageResponse[UserResponse])
def list_users(
    department_id: uuid.UUID | None = Query(None),
    job_level: str | None = Query(None),
    position: str | None = Query(None),
    user_status: str | None = Query(None, alias="status"),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    requester: User = Depends(require_permission(Perm.USER_READ)),
    db: Session = Depends(get_db),
):
    """List users with optional grouping filters (UM-04 user grouping)."""
    filt = UserGroupFilter(
        department_id=department_id,
        job_level=job_level,
        position=position,
        status=user_status,
        keyword=keyword,
    )
    users, total = UserService.list_users(db, requester, filt, page, page_size)
    roles_map = _load_user_roles(db, [str(u.id) for u in users])
    dept_names = _load_department_names(db, [str(u.department_id) for u in users if u.department_id])
    items = []
    for u in users:
        resp = UserResponse.model_validate(u)
        resp.roles = roles_map.get(str(u.id), [])
        resp.department_name = dept_names.get(str(u.department_id)) if u.department_id else None
        items.append(resp)
    return PageResponse(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    requester: User = Depends(require_permission(Perm.USER_READ)),
    db: Session = Depends(get_db),
):
    """Get a specific user by ID."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_response_with_roles(db, user)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreateRequest,
    requester: User = Depends(require_permission(Perm.USER_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a new user manually (UM-03)."""
    try:
        user = UserService.create_user(db, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if body.role_code:
        from app.core.seed import assign_role
        from app.models.role import DataScope
        try:
            scope = DataScope(body.data_scope)
        except ValueError:
            scope = DataScope.self
        assign_role(db, user, body.role_code, scope)
    db.commit()
    return _user_response_with_roles(db, user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    body: UserUpdateRequest,
    requester: User = Depends(require_permission(Perm.USER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update a user's information."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated = UserService.update_user(db, user, body)
    db.commit()
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: str,
    requester: User = Depends(require_permission(Perm.USER_DELETE)),
    db: Session = Depends(get_db),
):
    """Deactivate a user (soft delete, UM-03 绂昏亴鍋滅敤)."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    UserService.deactivate_user(db, user)
    db.commit()


# --- Role Assignment ---

class RoleAssignBody(BaseModel):
    role_code: str
    data_scope: DataScope = DataScope.self


@router.post("/{user_id}/roles", response_model=UserResponse)
def assign_role_to_user(
    user_id: str,
    body: RoleAssignBody,
    requester: User = Depends(require_permission(Perm.USER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Assign a role with data scope to a user."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    UserService.assign_user_role(db, user, body.role_code, body.data_scope)
    db.commit()
    return _user_response_with_roles(db, user)
