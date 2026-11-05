"""Student, teacher, administrator roles and permission assignments."""


from sqlalchemy import CHAR, Column, ForeignKey, String, Table, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKey


# Many-to-many: Role <-> Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", CHAR(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", CHAR(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base, UUIDPrimaryKey, TimestampMixin):
    """A granular permission, e.g. 'user:create', 'course:delete'."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    module: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )


class Role(Base, UUIDPrimaryKey, TimestampMixin):
    """A role bundles a set of permissions. Three builtin roles are seeded."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    user_assignments: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )


class UserRole(Base, UUIDPrimaryKey, TimestampMixin):
    """Associates a user with a campus role."""

    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("roles.id", ondelete="CASCADE"), index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="role_assignments")
    role: Mapped["Role"] = relationship("Role", back_populates="user_assignments")
