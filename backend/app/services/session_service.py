"""Session management: single sign-on and 2h session timeout."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DbSession

from app.models.session import Session, SessionStatus
from app.config import settings

# Session timeout: 2 hours
SESSION_TIMEOUT_MINUTES = 120


def _hash_token(token: str) -> str:
    """Hash a session token so the raw token is not stored in plaintext."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: DbSession, user_id: str, client_info: str | None = None) -> Session:
    """Create a new login session and revoke all previous active sessions.

    Single sign-on: a user may only have ONE active session. When they log
    in again (possibly from another device), all older active sessions are
    revoked, kicking the previous device out.
    """
    # Revoke all existing active sessions for this user
    db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.status == SessionStatus.active)
        .values(status=SessionStatus.revoked)
    )

    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    session = Session(
        user_id=user_id,
        token=_hash_token(raw_token),
        client_info=(client_info or "")[:500],
        status=SessionStatus.active,
        expires_at=now + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
        last_active_at=now,
    )
    db.add(session)
    db.flush()
    # Attach the raw token so auth can put it into the JWT `sid` claim
    session._raw_token = raw_token
    return session


def validate_session(db: DbSession, session_id: str | None, raw_token: str | None) -> tuple[Session | None, str | None]:
    """Validate a session.

    Returns (session, error). error is:
      - "expired"   -> session has timed out (> 2h)
      - "revoked"   -> user logged in elsewhere (异地登录)
      - "invalid"   -> session does not exist
    """
    if not session_id or not raw_token:
        return None, "invalid"
    session = db.execute(select(Session).where(Session.id == session_id)).scalar_one_or_none()
    if not session:
        return None, "invalid"
    if session.token != _hash_token(raw_token):
        return None, "invalid"

    now = datetime.now(timezone.utc)

    if session.status == SessionStatus.revoked:
        return None, "revoked"

    # Session timeout check
    if session.status == SessionStatus.expired:
        return None, "expired"
    expires_at = session.expires_at
    if expires_at is not None:
        # MySQL returns naive datetimes; treat them as UTC to compare with `now`
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            session.status = SessionStatus.expired
            db.flush()
            return None, "expired"

    # Touch last_active_at (only update timestamp, not on every request to reduce writes)
    return session, None


def touch_session(db: DbSession, session: Session) -> None:
    """Refresh the last_active_at (sliding session)."""
    session.last_active_at = datetime.now(timezone.utc)


def revoke_session(db: DbSession, session_id: str) -> None:
    db.execute(
        update(Session).where(Session.id == session_id).values(status=SessionStatus.revoked)
    )
