"""Authentication provider abstraction."""

import abc

from sqlalchemy.orm import Session

from app.models.user import User


class AuthResult:
    def __init__(self, user: User, provider: str):
        self.user = user
        self.provider = provider


class AuthenticationProvider(abc.ABC):
    @property
    @abc.abstractmethod
    def provider_name(self) -> str: ...

    @abc.abstractmethod
    def authenticate(self, db: Session, **kwargs) -> AuthResult: ...

    @abc.abstractmethod
    def register(self, db: Session, **kwargs) -> AuthResult: ...


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)