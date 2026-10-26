"""Question Bank model for categorizing questions."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class QuestionBank(Base, UUIDPrimaryKey, TimestampMixin):
    """A question bank category (e.g. market knowledge, after-sales knowledge)."""

    __tablename__ = "question_banks"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
