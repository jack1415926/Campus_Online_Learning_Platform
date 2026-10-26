"""SSO authentication provider stub (reserved for Phase 8)."""

from sqlalchemy.orm import Session

from app.auth.base import AuthError, AuthResult, AuthenticationProvider


class SSOProvider(AuthenticationProvider):
    @property
    def provider_name(self) -> str:
        return "sso"

    def authenticate(self, db: Session, **kwargs) -> AuthResult:
        raise AuthError("SSO authentication is not yet available", 501)

    def register(self, db: Session, **kwargs) -> AuthResult:
        raise AuthError("SSO registration is not yet available", 501)