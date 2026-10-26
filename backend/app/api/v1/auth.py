"""Authentication endpoints: register, login, refresh, me."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.auth import AuthError, default_provider
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserBrief
from app.services.session_service import create_session, validate_session

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_info(request: Request) -> str:
    """Build a short client description (IP + User-Agent) for the session."""
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")[:200]
    return f"ip={ip}; ua={ua}"[:500]


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        result = default_provider.authenticate(
            db, username=body.username, password=body.password,
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    user = result.user
    # Create a login session; revokes any previous active session (单点登录)
    sess = create_session(db, str(user.id), _client_info(request))
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, session_id=str(sess.id), session_token=getattr(sess, "_raw_token", "")),
        refresh_token=create_refresh_token(user.id, session_id=str(sess.id), session_token=getattr(sess, "_raw_token", "")),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Reuse the existing session if it's still valid, else create a new one
    old_sid = payload.get("sid")
    old_sess = payload.get("sess")
    session, _ = validate_session(db, old_sid, old_sess) if old_sid and old_sess else (None, "invalid")
    if session:
        sess = session
    else:
        sess = create_session(db, user_id, _client_info(request))
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user_id, session_id=str(sess.id), session_token=getattr(sess, "_raw_token", "")),
        refresh_token=create_refresh_token(user_id, session_id=str(sess.id), session_token=getattr(sess, "_raw_token", "")),
    )


@router.get("/me", response_model=UserBrief)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.core.rbac import load_user_permissions
    from sqlalchemy import select as _select
    from app.models.role import Role, UserRole
    perms = sorted(load_user_permissions(db, current_user.id))
    role_codes = [
        r[0] for r in db.execute(
            _select(Role.code).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
        ).all()
    ]
    return UserBrief(
        id=current_user.id, username=current_user.username, email=current_user.email,
        full_name=current_user.full_name, status=current_user.status.value if hasattr(current_user.status, 'value') else str(current_user.status),
        permissions=perms, roles=role_codes,
    )