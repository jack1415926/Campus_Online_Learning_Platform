"""User management service: CRUD, grouping, and profile operations."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.core.rbac import get_data_scope_filter, load_user_data_scope
from app.core.security import hash_password
from app.core.seed import assign_role
from app.models.org import Organization
from app.models.role import DataScope, UserRole
from app.models.user import User, UserStatus
from app.schemas.user import UserCreateRequest, UserGroupFilter, UserUpdateRequest


class UserService:
    """Business logic for user management (UM-03, UM-04, UM-05)."""

    @staticmethod
    def list_users(
        db: Session,
        requester: User,
        filt: UserGroupFilter | None = None,
        page: int = 1,
        page_size: int = 20,
        review_status: str | None = None,
    ) -> tuple[list[User], int]:
        """List users with data-scope filtering and optional grouping filters."""
        scope_filter = get_data_scope_filter(db, requester)

        stmt = select(User)
        if review_status:
            stmt = stmt.where(User.teacher_review_status == review_status)

        # Apply data scope
        if "user_id" in scope_filter:
            stmt = stmt.where(User.id == scope_filter["user_id"])
        elif "department_ids" in scope_filter:
            stmt = stmt.where(User.department_id.in_(scope_filter["department_ids"]))

        # Apply user-provided filters (UM-04 user grouping)
        if filt:
            if filt.department_id:
                stmt = stmt.where(User.department_id == filt.department_id)
            if filt.job_level:
                stmt = stmt.where(User.job_level == filt.job_level)
            if filt.position:
                stmt = stmt.where(User.position == filt.position)
            if filt.status:
                stmt = stmt.where(User.status == UserStatus(filt.status))
            if filt.keyword:
                kw = f"%{filt.keyword}%"
                stmt = stmt.where(
                    or_(
                        User.full_name.ilike(kw),
                        User.username.ilike(kw),
                        User.employee_id.ilike(kw),
                    )
                )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(User.created_at.desc())
        result = db.execute(stmt)
        users = list(result.scalars().all())

        return users, total

    @staticmethod
    def get_user(db: Session, user_id: str) -> User | None:
        """Get a single user by ID."""
        result = db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.role_assignments))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def create_user(
        db: Session, body: UserCreateRequest
    ) -> User:
        """Admin-created user (UM-03 manual creation)."""
        # Check uniqueness
        existing = db.execute(
            select(User).where(
                (User.username == body.username) | (User.email == body.email)
            )
        )
        if existing.scalars().first():
            raise ValueError("Username or email already exists")

        # Resolve department: use provided department_id, or find/create by name
        department_id = body.department_id
        if not department_id and body.department_name:
            dept = db.execute(
                select(Organization).where(Organization.name == body.department_name)
            ).scalar_one_or_none()
            if not dept:
                dept = Organization(name=body.department_name, status="active")
                db.add(dept)
                db.flush()
            department_id = str(dept.id)

        user = User(
            username=body.username,
            email=body.email,
            password_hash=hash_password(body.password),
            full_name=body.full_name,
            employee_id=body.employee_id,
            phone=body.phone,
            department_id=department_id,
            job_level=body.job_level,
            position=body.position,
            custom_fields=body.custom_fields,
            status=UserStatus.active,
        )
        db.add(user)
        db.flush()
        return user

    @staticmethod
    def update_user(
        db: Session, user: User, body: UserUpdateRequest
    ) -> User:
        """Update user fields."""
        update_data = body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        db.flush()
        return user

    @staticmethod
    def deactivate_user(db: Session, user: User) -> User:
        """Soft-delete: set status to inactive (UM-03 绂昏亴鍋滅敤)."""
        user.status = UserStatus.inactive
        db.flush()
        return user

    @staticmethod
    def assign_user_role(
        db: Session,
        user: User,
        role_code: str,
        data_scope: DataScope = DataScope.self,
    ) -> None:
        """Assign a role with data scope to a user."""
        assign_role(db, user, role_code, data_scope)
