"""User management API endpoints."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import require_permission
from app.database import get_db
from app.models.role import UserRole
from app.models.session import Session as LoginSession, SessionStatus
from app.core.security import hash_password, verify_password
from app.core.seed import assign_role
from app.schemas.auth import ChangePasswordRequest
from app.models.user import User, UserStatus
from app.schemas.common import PageMeta, PageResponse
from app.schemas.user import (
    UserCreateRequest,
    UserGroupFilter,
    UserResponse,
    UserUpdateRequest,
)
from pydantic import BaseModel, Field, EmailStr

from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


class ProfileUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class TeacherReview(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(default="", max_length=1000)


class StatusUpdate(BaseModel):
    status: Literal["active", "inactive"]


def _set_campus_role(db, user, role_code, reviewer):
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    assign_role(db, user, role_code)
    user.requested_role = role_code
    user.teacher_review_status = "approved" if role_code == "teacher" else None
    user.teacher_review_reason = None
    user.teacher_reviewed_by = str(reviewer.id)
    user.teacher_reviewed_at = datetime.now(timezone.utc)

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


def _user_response_with_roles(db: Session, user: User) -> UserResponse:
    """Build UserResponse with roles populated."""
    resp = UserResponse.model_validate(user)
    roles_map = _load_user_roles(db, [str(user.id)])
    resp.roles = roles_map.get(str(user.id), [])
    return resp


# --- Personal Center ---

@router.get("/me/profile", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's full profile."""
    return _user_response_with_roles(db, current_user)


@router.put("/me/profile", response_model=UserResponse)
def update_my_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's own profile."""
    if not body.full_name.strip():
        raise HTTPException(422, "姓名不能为空")
    current_user.full_name = body.full_name.strip()
    current_user.email = body.email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "邮箱已被其他用户使用") from None
    return _user_response_with_roles(db, current_user)


@router.post("/me/password", status_code=204)
def change_password(body: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.password_hash or not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(400, "原密码不正确")
    current_user.password_hash = hash_password(body.new_password)
    db.execute(update(LoginSession).where(LoginSession.user_id == current_user.id).values(status=SessionStatus.revoked))
    db.commit()


# --- User CRUD ---

@router.get("", response_model=PageResponse[UserResponse])
def list_users(
    user_status: str | None = Query(None, alias="status"),
    keyword: str | None = Query(None),
    review_status: Literal["pending", "approved", "rejected"] | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    requester: User = Depends(require_permission(Perm.USER_READ)),
    db: Session = Depends(get_db),
):
    filt = UserGroupFilter(
        status=user_status,
        keyword=keyword,
    )
    users, total = UserService.list_users(db, requester, filt, page, page_size, review_status=review_status)
    roles_map = _load_user_roles(db, [str(u.id) for u in users])
    items = []
    for u in users:
        resp = UserResponse.model_validate(u)
        resp.roles = roles_map.get(str(u.id), [])
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
    """Create a new user manually."""
    try:
        user = UserService.create_user(db, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _set_campus_role(db, user, body.role_code, requester)
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
    try:
        updated = UserService.update_user(db, user, body)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "邮箱已被其他用户使用") from None
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: str,
    requester: User = Depends(require_permission(Perm.USER_DELETE)),
    db: Session = Depends(get_db),
):
    """Deactivate a user (soft delete, UM-03 停用账号)."""
    if str(requester.id) == user_id:
        raise HTTPException(400, "不能停用自己的管理员账号")
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    UserService.deactivate_user(db, user)
    db.execute(update(LoginSession).where(LoginSession.user_id == user.id).values(status=SessionStatus.revoked))
    db.commit()


# --- Role Assignment ---

class RoleAssignBody(BaseModel):
    role_code: Literal["student", "teacher", "admin"]


@router.post("/{user_id}/roles", response_model=UserResponse)
def assign_role_to_user(
    user_id: str,
    body: RoleAssignBody,
    requester: User = Depends(require_permission(Perm.USER_UPDATE)),
    db: Session = Depends(get_db),
):
    """Assign a campus role to a user."""
    user = UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(requester.id) == user_id and body.role_code != "admin":
        raise HTTPException(400, "不能移除自己的管理员角色")
    _set_campus_role(db, user, body.role_code, requester)
    db.commit()
    return _user_response_with_roles(db, user)


@router.post("/{user_id}/teacher-review", response_model=UserResponse)
def review_teacher(user_id: str, body: TeacherReview, requester: User = Depends(require_permission(Perm.USER_UPDATE)), db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.id == user_id).with_for_update()).scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "用户不存在")
    if user.requested_role != "teacher" or user.teacher_review_status not in ("pending", "rejected"):
        raise HTTPException(409, "该账号不处于待审核或驳回状态")
    if body.decision == "approve":
        _set_campus_role(db, user, "teacher", requester)
    else:
        if not body.reason.strip():
            raise HTTPException(422, "请填写驳回原因")
        user.teacher_review_status = "rejected"
        user.teacher_review_reason = body.reason.strip()
        user.teacher_reviewed_by = str(requester.id)
        user.teacher_reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return _user_response_with_roles(db, user)


@router.put("/{user_id}/status", response_model=UserResponse)
def change_status(user_id: str, body: StatusUpdate, requester: User = Depends(require_permission(Perm.USER_UPDATE)), db: Session = Depends(get_db)):
    if str(requester.id) == user_id and body.status != "active":
        raise HTTPException(400, "不能停用自己的管理员账号")
    user = UserService.get_user(db, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    user.status = UserStatus(body.status)
    if body.status != "active":
        db.execute(update(LoginSession).where(LoginSession.user_id == user.id).values(status=SessionStatus.revoked))
    db.commit()
    return _user_response_with_roles(db, user)
