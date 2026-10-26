"""Authentication provider package."""

from app.auth.base import AuthError, AuthResult, AuthenticationProvider
from app.auth.local import LocalAuthProvider
from app.auth.sso import SSOProvider

# Default provider for Phase 0; Phase 8 will add provider routing
default_provider = LocalAuthProvider()

__all__ = [
    "AuthError",
    "AuthResult",
    "AuthenticationProvider",
    "LocalAuthProvider",
    "SSOProvider",
    "default_provider",
]
