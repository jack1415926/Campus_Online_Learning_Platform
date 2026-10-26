"""Base model with common mixins for all database entities."""

import uuid

from sqlalchemy import CHAR, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class UUIDPrimaryKey:
    """Mixin providing a UUID primary key stored as CHAR(36)."""

    id: Mapped[uuid.UUID] = mapped_column(
        CHAR(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )


class TimestampMixin:
    """Mixin providing created_at / updated_at columns."""

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )