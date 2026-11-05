"""Course category management API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


def _check_perm(db: Session, user: User, perm: str):
    perms = load_user_permissions(db, user.id)
    if perm not in perms:
        raise HTTPException(403, f"Requires permission: {perm}")


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cats = CategoryService.list_tree(db)
    return cats


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    body: CategoryCreate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_CREATE)
    cat = CategoryService.create(db, body, requester.id)
    db.commit()
    return cat


@router.put("/{cat_id}", response_model=CategoryResponse)
def update_category(
    cat_id: str,
    body: CategoryUpdate,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_CREATE)
    cat = (db.execute(select(Category).where(Category.id == cat_id))).scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Category not found")
    updated = CategoryService.update(db, cat, body)
    db.commit()
    return updated


@router.delete("/{cat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    cat_id: str,
    requester: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_perm(db, requester, Perm.COURSE_CREATE)
    cat = (db.execute(select(Category).where(Category.id == cat_id))).scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "Category not found")
    CategoryService.delete(db, cat)
    db.commit()
