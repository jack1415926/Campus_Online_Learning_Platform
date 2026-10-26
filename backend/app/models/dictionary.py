"""Dictionary-type models: job levels and positions.

These provide centrally-managed enumerations referenced by users and learning
paths, so that job_level / position values are maintained in one place.
"""

import uuid

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class JobLevel(Base, UUIDPrimaryKey, TimestampMixin):
    """A job level (职级), e.g. 初级 / 中级 / 高级."""

    __tablename__ = "job_levels"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")


class Position(Base, UUIDPrimaryKey, TimestampMixin):
    """A job position (岗位), e.g. 软件开发工程师 / 测试工程师."""

    __tablename__ = "positions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
