"""Category and tag management service (CM-06)."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.category import Category, Tag
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:

    @staticmethod
    def list_tree(db: Session) -> list[Category]:
        """Get all categories as a flat list (frontend builds the tree)."""
        result = db.execute(
            select(Category).order_by(Category.sort_order, Category.name)
        )
        return list(result.scalars().all())

    @staticmethod
    def create(db: Session, body: CategoryCreate, creator_id: str) -> Category:
        level = 1
        if body.parent_id:
            parent = (
                db.execute(select(Category).where(Category.id == body.parent_id))
            ).scalar_one_or_none()
            if parent:
                level = parent.level + 1
        cat = Category(
            name=body.name,
            parent_id=body.parent_id,
            level=level,
            sort_order=body.sort_order,
            description=body.description,
        )
        db.add(cat)
        db.flush()
        return cat

    @staticmethod
    def update(db: Session, cat: Category, body: CategoryUpdate) -> Category:
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(cat, k, v)
        db.flush()
        return cat

    @staticmethod
    def delete(db: Session, cat: Category) -> None:
        db.delete(cat)
        db.flush()


class TagService:

    @staticmethod
    def list_all(db: Session) -> list[Tag]:
        result = db.execute(select(Tag).order_by(Tag.name))
        return list(result.scalars().all())

    @staticmethod
    def create(db: Session, name: str) -> Tag:
        existing = (
            db.execute(select(Tag).where(Tag.name == name))
        ).scalar_one_or_none()
        if existing:
            return existing
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
        return tag

    @staticmethod
    def delete(db: Session, tag: Tag) -> None:
        db.delete(tag)
        db.flush()