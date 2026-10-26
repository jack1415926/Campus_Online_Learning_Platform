"""Media asset library service (DM-01)."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.media import MediaAsset, MediaType
from app.models.media_category import MediaCategory
from app.schemas.media import MediaAssetListFilter, MediaAssetUpdate, MediaCategoryCreate, MediaCategoryUpdate


class MediaService:

    @staticmethod
    def list_assets(
        db: Session,
        filt: MediaAssetListFilter | None = None,
        page: int = 1,
        page_size: int = 20,
        uploaded_by: str | None = None,
    ) -> tuple[list[MediaAsset], int]:
        stmt = select(MediaAsset)
        if uploaded_by is not None:
            stmt = stmt.where(MediaAsset.uploaded_by == uploaded_by)
        if filt:
            if filt.media_type:
                stmt = stmt.where(MediaAsset.media_type == filt.media_type)
            if filt.category_id:
                stmt = stmt.where(MediaAsset.category_id == filt.category_id)
            if filt.keyword:
                kw = f"%{filt.keyword}%"
                stmt = stmt.where(MediaAsset.name.ilike(kw))
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (db.execute(count_stmt)).scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        stmt = stmt.order_by(MediaAsset.created_at.desc())
        result = db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    def get_asset(db: Session, asset_id: str) -> MediaAsset | None:
        return (
            db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
        ).scalar_one_or_none()

    @staticmethod
    def create_asset(
        db: Session,
        name: str,
        media_type: MediaType,
        storage_key: str,
        file_url: str | None = None,
        file_size: int | None = None,
        mime_type: str | None = None,
        duration: int | None = None,
        resolution: str | None = None,
        category_id: str | None = None,
        description: str | None = None,
        uploaded_by: str | None = None,
    ) -> MediaAsset:
        asset = MediaAsset(
            name=name,
            media_type=media_type,
            storage_key=storage_key,
            file_url=file_url,
            file_size=file_size,
            mime_type=mime_type,
            duration=duration,
            resolution=resolution,
            category_id=category_id,
            description=description,
            uploaded_by=uploaded_by,
        )
        db.add(asset)
        db.flush()
        return asset

    @staticmethod
    def update_asset(
        db: Session, asset: MediaAsset, body: MediaAssetUpdate
    ) -> MediaAsset:
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(asset, k, v)
        db.flush()
        return asset

    @staticmethod
    def delete_asset(db: Session, asset: MediaAsset) -> None:
        db.delete(asset)
        db.flush()


class MediaCategoryService:

    @staticmethod
    def list_categories(db: Session):
        stmt = select(MediaCategory).order_by(MediaCategory.created_at.desc())
        cats = list(db.execute(stmt).scalars().all())
        result = []
        for c in cats:
            count = db.execute(
                select(func.count()).select_from(
                    select(MediaAsset).where(MediaAsset.category_id == c.id).subquery()
                )
            ).scalar() or 0
            result.append((c, count))
        return result

    @staticmethod
    def get_category(db: Session, cat_id: str):
        return db.execute(select(MediaCategory).where(MediaCategory.id == cat_id)).scalar_one_or_none()

    @staticmethod
    def create_category(db: Session, body: MediaCategoryCreate, creator_id: str):
        cat = MediaCategory(name=body.name, description=body.description, created_by=creator_id)
        db.add(cat)
        db.flush()
        return cat

    @staticmethod
    def update_category(db: Session, cat: MediaCategory, body: MediaCategoryUpdate):
        if body.name is not None:
            cat.name = body.name
        if body.description is not None:
            cat.description = body.description
        db.flush()
        return cat

    @staticmethod
    def delete_category(db: Session, cat: MediaCategory):
        db.execute(
            MediaAsset.__table__.update().where(MediaAsset.category_id == cat.id).values(category_id=None)
        )
        db.delete(cat)
        db.flush()
