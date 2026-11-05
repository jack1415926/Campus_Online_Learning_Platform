"""User management service: CRUD, grouping, and profile operations."""


from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.core.campus_access import require_admin
from app.core.security import hash_password
from app.models.user import User, UserStatus
from app.schemas.user import UserCreateRequest, UserGroupFilter, UserUpdateRequest


class UserService:
    """Business logic for user management."""

    @staticmethod
    def list_users(
        db: Session,
        requester: User,
        filt: UserGroupFilter | None = None,
        page: int = 1,
        page_size: int = 20,
        review_status: str | None = None,
    ) -> tuple[list[User], int]:
        """List users with optional status and name filters."""
        require_admin(db, requester)

        stmt = select(User)
        if review_status:
            stmt = stmt.where(User.teacher_review_status == review_status)

        # Apply user-provided filters
        if filt:
            if filt.status:
                stmt = stmt.where(User.status == UserStatus(filt.status))
            if filt.keyword:
                kw = f"%{filt.keyword}%"
                stmt = stmt.where(
                    or_(
                        User.full_name.ilike(kw),
                        User.username.ilike(kw),
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
        """Admin-created user."""
        # Check uniqueness
        existing = db.execute(
            select(User).where(
                (User.username == body.username) | (User.email == body.email)
            )
        )
        if existing.scalars().first():
            raise ValueError("Username or email already exists")

        user = User(
            username=body.username,
            email=body.email,
            password_hash=hash_password(body.password),
            full_name=body.full_name,
            phone=body.phone,
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
        """Soft-delete: set status to inactive."""
        user.status = UserStatus.inactive
        db.flush()
        return user
