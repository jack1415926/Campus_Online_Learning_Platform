"""Course category (multi-level tree) and tag models (CM-06)."""

from sqlalchemy import CHAR, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


class Category(Base, UUIDPrimaryKey, TimestampMixin):
    """Multi-level course category tree."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(
        CHAR(36),
        ForeignKey("categories.id"),
        nullable=True,
        index=True,
    )
    level: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    courses: Mapped[list["Course"]] = relationship(
        "Course", back_populates="category"
    )


class Tag(Base, UUIDPrimaryKey, TimestampMixin):
    """Course tag for flexible labeling."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    courses: Mapped[list["Course"]] = relationship(
        "Course", secondary="course_tags", back_populates="tags"
    )