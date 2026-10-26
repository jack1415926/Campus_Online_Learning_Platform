"""Local authentication provider: username/password + JWT."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.base import AuthError, AuthResult, AuthenticationProvider
from app.core.security import hash_password, verify_password
from app.models.user import User, UserStatus


class LocalAuthProvider(AuthenticationProvider):
    @property
    def provider_name(self) -> str:
        return "local"

    def register(self, db: Session, *, username: str, email: str, password: str,
                 full_name: str, employee_id: str | None = None, phone: str | None = None) -> AuthResult:
        existing = db.execute(
            select(User).where((User.username == username) | (User.email == email))
        ).scalars().first()
        if existing:
            raise AuthError("Username or email already registered", 409)
        user = User(
            username=username, email=email, password_hash=hash_password(password),
            full_name=full_name, employee_id=employee_id, phone=phone,
            status=UserStatus.active,
        )
        db.add(user)
        db.flush()
        return AuthResult(user=user, provider=self.provider_name)

    def authenticate(self, db: Session, *, username: str, password: str) -> AuthResult:
        user = db.execute(
            select(User).where((User.username == username) | (User.email == username))
        ).scalar_one_or_none()
        if not user or not user.password_hash:
            raise AuthError("Invalid credentials", 401)
        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid credentials", 401)
        if user.status != UserStatus.active:
            raise AuthError(f"Account is {user.status.value}", 403)
        return AuthResult(user=user, provider=self.provider_name)
