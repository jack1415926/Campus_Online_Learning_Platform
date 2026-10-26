"""Shared FastAPI dependencies: database session and current user."""

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User, UserStatus
from app.services.session_service import validate_session


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_token(token)
    except JWTError:
        raise _unauthorized("Invalid or expired token")
    if payload.get("type") != "access":
        raise _unauthorized("Wrong token type")
    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Invalid token payload")

    # Session validation: single sign-on (异地登录) + 2h timeout
    session_id = payload.get("sid")
    session_token = payload.get("sess")
    session, error = validate_session(db, session_id, session_token)
    if error == "revoked":
        # User logged in elsewhere; kick this session out
        raise _unauthorized("该账号已在其他设备登录，您已被强制下线")
    if error == "expired":
        raise _unauthorized("登录会话已超时，请重新登录")
    if error == "invalid":
        raise _unauthorized("登录会话无效，请重新登录")

    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user or user.status != UserStatus.active:
        raise _unauthorized("User not found or inactive")
    user._login_session = session
    user._session_token = session_token
    return user
