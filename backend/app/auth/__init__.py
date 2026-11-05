"""Authentication provider package."""

from app.auth.base import AuthError, AuthResult, AuthenticationProvider
from app.auth.local import LocalAuthProvider

# Username/password authentication.
default_provider = LocalAuthProvider()

__all__ = [
    "AuthError",
    "AuthResult",
    "AuthenticationProvider",
    "LocalAuthProvider",
    "default_provider",
]
