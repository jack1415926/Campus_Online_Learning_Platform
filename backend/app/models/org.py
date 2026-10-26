"""Organization (department) model with self-referential tree structure."""

import uuid

from sqlalchemy import CHAR, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Organization(Base, UUIDPrimaryKey, TimestampMixin):
    """Department / organization node in a self-referential tree."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )
    level: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")

    parent: Mapped["Organization | None"] = relationship(
        "Organization",
        remote_side="Organization.id",
        back_populates="children",
    )
    children: Mapped[list["Organization"]] = relationship(
        "Organization",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="department")