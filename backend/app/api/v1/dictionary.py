"""Dictionary management API: job levels, positions and departments.

These entities are centrally maintained here and referenced by users, learning
paths, course assignments, etc.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.dictionary import JobLevel, Position
from app.models.org import Organization
from app.models.user import User

router = APIRouter(tags=["dictionary"])


def _check_perm(db: Session, user: User):
    perms = load_user_permissions(db, user.id)
    if Perm.ORG_MANAGE not in perms and Perm.SYSTEM_CONFIG not in perms:
        raise HTTPException(403, "Requires permission: org:manage or system:config")


# ---------- Schemas ----------

class DictCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class DictUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = None
    status: str | None = None


class DictResponse(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int = 0
    status: str = "active"

    model_config = {"from_attributes": True}


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: str | None = None
    sort_order: int = 0


class OrgUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    parent_id: str | None = None
    sort_order: int | None = None
    status: str | None = None


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: str | None = None
    level: int = 1
    sort_order: int = 0
    status: str = "active"

    model_config = {"from_attributes": True}


# ---------- Generic helpers for JobLevel / Position ----------

def _list_all(db: Session, model):
    return list(db.execute(select(model).order_by(model.sort_order, model.name)).scalars().all())


def _get_by_id(db: Session, model, obj_id: str):
    return db.execute(select(model).where(model.id == obj_id)).scalar_one_or_none()


def _ensure_unique(db: Session, model, name: str, exclude_id: str | None = None):
    stmt = select(model).where(model.name == name)
    if exclude_id:
        stmt = stmt.where(model.id != exclude_id)
    if db.execute(stmt).scalar_one_or_none():
        raise HTTPException(409, f"Name already exists: {name}")


# ---------- Job Levels ----------

job_level_router = APIRouter(prefix="/job-levels", tags=["job-levels"])


@job_level_router.get("", response_model=list[DictResponse])
def list_job_levels(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _list_all(db, JobLevel)


@job_level_router.post("", response_model=DictResponse, status_code=201)
def create_job_level(body: DictCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    _ensure_unique(db, JobLevel, body.name)
    obj = JobLevel(name=body.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@job_level_router.put("/{obj_id}", response_model=DictResponse)
def update_job_level(obj_id: str, body: DictUpdate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    obj = _get_by_id(db, JobLevel, obj_id)
    if not obj:
        raise HTTPException(404, "Job level not found")
    if body.name is not None and body.name != obj.name:
        _ensure_unique(db, JobLevel, body.name, obj_id)
        obj.name = body.name
    if body.sort_order is not None:
        obj.sort_order = body.sort_order
    if body.status is not None:
        obj.status = body.status
    db.commit()
    db.refresh(obj)
    return obj


@job_level_router.delete("/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job_level(obj_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    obj = _get_by_id(db, JobLevel, obj_id)
    if not obj:
        raise HTTPException(404, "Job level not found")
    db.delete(obj)
    db.commit()


# ---------- Positions ----------

position_router = APIRouter(prefix="/positions", tags=["positions"])


@position_router.get("", response_model=list[DictResponse])
def list_positions(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _list_all(db, Position)


@position_router.post("", response_model=DictResponse, status_code=201)
def create_position(body: DictCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    _ensure_unique(db, Position, body.name)
    obj = Position(name=body.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@position_router.put("/{obj_id}", response_model=DictResponse)
def update_position(obj_id: str, body: DictUpdate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    obj = _get_by_id(db, Position, obj_id)
    if not obj:
        raise HTTPException(404, "Position not found")
    if body.name is not None and body.name != obj.name:
        _ensure_unique(db, Position, body.name, obj_id)
        obj.name = body.name
    if body.sort_order is not None:
        obj.sort_order = body.sort_order
    if body.status is not None:
        obj.status = body.status
    db.commit()
    db.refresh(obj)
    return obj


@position_router.delete("/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(obj_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    obj = _get_by_id(db, Position, obj_id)
    if not obj:
        raise HTTPException(404, "Position not found")
    db.delete(obj)
    db.commit()


# ---------- Departments (organizations) ----------

department_router = APIRouter(prefix="/departments", tags=["departments"])


@department_router.get("", response_model=list[OrgResponse])
def list_departments(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(select(Organization).order_by(Organization.sort_order, Organization.name)).scalars().all())


@department_router.post("", response_model=OrgResponse, status_code=201)
def create_department(body: OrgCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    if db.execute(select(Organization).where(Organization.name == body.name)).scalar_one_or_none():
        raise HTTPException(409, f"Department already exists: {body.name}")
    obj = Organization(name=body.name, parent_id=body.parent_id, sort_order=body.sort_order)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@department_router.put("/{obj_id}", response_model=OrgResponse)
def update_department(obj_id: str, body: OrgUpdate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    obj = _get_by_id(db, Organization, obj_id)
    if not obj:
        raise HTTPException(404, "Department not found")
    if body.name is not None and body.name != obj.name:
        if db.execute(select(Organization).where(Organization.name == body.name, Organization.id != obj_id)).scalar_one_or_none():
            raise HTTPException(409, f"Department already exists: {body.name}")
        obj.name = body.name
    if body.parent_id is not None:
        obj.parent_id = body.parent_id
    if body.sort_order is not None:
        obj.sort_order = body.sort_order
    if body.status is not None:
        obj.status = body.status
    db.commit()
    db.refresh(obj)
    return obj


@department_router.delete("/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(obj_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester)
    obj = _get_by_id(db, Organization, obj_id)
    if not obj:
        raise HTTPException(404, "Department not found")
    # Prevent deleting a department still referenced by users
    if db.execute(select(User).where(User.department_id == obj_id)).scalar_one_or_none():
        raise HTTPException(409, "Department still has users, cannot delete")
    db.delete(obj)
    db.commit()
