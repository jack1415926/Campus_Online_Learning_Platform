"""Schemas for media assets (DM-01)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.media import MediaType


class MediaAssetResponse(BaseModel):
    id: str
    name: str
    media_type: MediaType
    storage_key: str
    file_url: str | None = None
    file_size: int | None = None
    mime_type: str | None = None
    duration: int | None = None
    resolution: str | None = None
    category_id: str | None = None
    description: str | None = None
    uploaded_by: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaAssetUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    category_id: str | None = None


class MediaAssetListFilter(BaseModel):
    media_type: MediaType | None = None
    category_id: str | None = None
    keyword: str | None = None

# --- Media Category ---


class MediaCategoryBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None


class MediaCategoryCreate(MediaCategoryBase):
    pass


class MediaCategoryUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None


class MediaCategoryResponse(MediaCategoryBase):
    id: str
    created_by: str | None = None
    created_at: datetime
    asset_count: int = 0
    model_config = {"from_attributes": True}
