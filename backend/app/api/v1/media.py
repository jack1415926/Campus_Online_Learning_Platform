"""Media asset library API (DM-01)."""

import traceback
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.media import MediaAsset, MediaType
from app.models.user import User
from app.schemas.common import PageMeta, PageResponse
from app.schemas.media import (
    MediaAssetListFilter, MediaAssetResponse, MediaAssetUpdate,
    MediaCategoryCreate, MediaCategoryResponse, MediaCategoryUpdate,
)
from app.services import storage_service
from app.services.media_service import MediaCategoryService, MediaService
from sqlalchemy import select, func

router = APIRouter(prefix="/media", tags=["media"])

MIME_MAP = {
    "video/": MediaType.video,
    "audio/": MediaType.audio,
    "image/": MediaType.image,
    "application/pdf": MediaType.document,
    "application/vnd.ms-powerpoint": MediaType.document,
    "application/vnd.openxmlformats-officedocument": MediaType.document,
    "application/msword": MediaType.document,
    "text/": MediaType.document,
}


def detect_media_type(mime: str) -> MediaType:
    for prefix, mtype in MIME_MAP.items():
        if mime.startswith(prefix):
            return mtype
    return MediaType.document



# --- Media Categories ---

@router.get("/categories", response_model=list[MediaCategoryResponse])
def list_media_categories(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    results = MediaCategoryService.list_categories(db)
    items = []
    for cat, count in results:
        item = MediaCategoryResponse.model_validate(cat)
        item.asset_count = count
        items.append(item)
    return items


@router.post("/categories", response_model=MediaCategoryResponse, status_code=201)
def create_media_category(body: MediaCategoryCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_CREATE not in perms:
        raise HTTPException(403, "Requires permission: course:create")
    cat = MediaCategoryService.create_category(db, body, requester.id)
    db.commit()
    return MediaCategoryResponse.model_validate(cat)


@router.put("/categories/{cat_id}", response_model=MediaCategoryResponse)
def update_media_category(cat_id: str, body: MediaCategoryUpdate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_CREATE not in perms:
        raise HTTPException(403, "Requires permission: course:create")
    cat = MediaCategoryService.get_category(db, cat_id)
    if not cat:
        raise HTTPException(404, "Media category not found")
    cat = MediaCategoryService.update_category(db, cat, body)
    db.commit()
    return MediaCategoryResponse.model_validate(cat)


@router.delete("/categories/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media_category(cat_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_CREATE not in perms:
        raise HTTPException(403, "Requires permission: course:create")
    cat = MediaCategoryService.get_category(db, cat_id)
    if not cat:
        raise HTTPException(404, "Media category not found")
    MediaCategoryService.delete_category(db, cat)
    db.commit()


@router.get("", response_model=PageResponse[MediaAssetResponse])
def list_media(
    media_type: MediaType | None = Query(None),
    category_id: str | None = Query(None),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filt = MediaAssetListFilter(
        media_type=media_type, category_id=category_id, keyword=keyword
    )
    assets, total = MediaService.list_assets(db, filt, page, page_size)
    return PageResponse(
        items=[MediaAssetResponse.model_validate(a) for a in assets],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{asset_id}/url")
def get_media_url(
    asset_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回素材的实时可访问 URL。

    - 本地存储: 返回 /storage/{key}
    - OSS 存储: 返回带签名的临时 URL(有效期由配置控制)
    """
    asset = MediaService.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, "Media asset not found")
    url = storage_service.get_url(asset.storage_key)
    return {"id": asset.id, "url": url}


@router.get("/{asset_id}", response_model=MediaAssetResponse)
def get_media(
    asset_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset = MediaService.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, "Media asset not found")
    return asset


@router.post("/upload", response_model=MediaAssetResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    category_id: str | None = Query(None),
    description: str | None = Query(None),
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check permission with the same session
    perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_CREATE not in perms:
        raise HTTPException(403, "Requires permission: course:create")

    try:
        mime = file.content_type or "application/octet-stream"
        media_type = detect_media_type(mime)

        ext = ""
        if file.filename and "." in file.filename:
            ext = file.filename.rsplit(".", 1)[-1]

        # Office 文档不支持在线预览，要求上传者先转成 PDF
        OFFICE_EXTS = {"doc", "docx", "ppt", "pptx"}
        if ext.lower() in OFFICE_EXTS:
            raise HTTPException(
                400,
                "Word/PPT 不支持在线预览，请先用 Office 将文件另存为 PDF 后再上传",
            )

        storage_key = f"media/{media_type.value}/{uuid.uuid4().hex}"
        if ext:
            storage_key += f".{ext}"

        # 流式上传到配置的存储后端(本地文件系统或 OSS)，避免大文件一次性载入内存
        file_size = 0
        try:
            file_size = file.size or 0
        except Exception:
            file_size = 0
        if not file_size:
            try:  # 兜底: 从底层文件对象计算大小
                f = file.file
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(0)
            except Exception:
                file_size = 0
        storage_service.upload_fileobj(storage_key, file.file, mime)

        # 生成可访问 URL 标识：
        #  - 本地: /storage/{key}
        #  - OSS:  oss://{key} (稳定标识，实际访问走 /media/{id}/url 签名接口)
        if storage_service.is_oss():
            file_url = f"oss://{storage_key}"
        else:
            file_url = f"/storage/{storage_key}"

        asset = MediaService.create_asset(
            db,
            name=file.filename or "unnamed",
            media_type=media_type,
            storage_key=storage_key,
            file_url=file_url,
            file_size=file_size,
            mime_type=mime,
            category_id=category_id,
            description=description,
            uploaded_by=requester.id,
        )
        db.commit()
        return asset
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        raise HTTPException(500, str(e))


@router.put("/{asset_id}", response_model=MediaAssetResponse)
def update_media(
    asset_id: str,
    body: MediaAssetUpdate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_CREATE not in perms:
        raise HTTPException(403, "Requires permission: course:create")
    asset = MediaService.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, "Media asset not found")
    updated = MediaService.update_asset(db, asset, body)
    db.commit()
    return updated


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    asset_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perms = load_user_permissions(db, requester.id)
    if Perm.COURSE_DELETE not in perms:
        raise HTTPException(403, "Requires permission: course:delete")
    asset = MediaService.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, "Media asset not found")
    # 从存储后端删除对象(本地文件 或 OSS)
    storage_service.delete(asset.storage_key)
    MediaService.delete_asset(db, asset)
    db.commit()