"""Notification API (NTF-01 through NTF-04)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import load_user_permissions
from app.database import get_db
from app.models.notification import NotificationTemplate
from app.models.user import User
from app.schemas.common import PageMeta, PageResponse
from app.schemas.notification import (
    MarkReadRequest, NotificationResponse, NotificationTemplateCreate,
    NotificationTemplateResponse, SendNotificationRequest,
)
from app.services.notification_service import NotificationService, TemplateService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _check_perm(db: Session, user: User, *perms: str):
    user_perms = load_user_permissions(db, user.id)
    if not any(p in user_perms for p in perms):
        raise HTTPException(403, f"Requires: {', '.join(perms)}")


# --- User notifications (NTF-01) ---

@router.get("", response_model=PageResponse[NotificationResponse])
def list_notifications(unread_only: bool = Query(False), page: int = Query(1, ge=1),
                       page_size: int = Query(20, ge=1, le=100),
                       requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs, total = NotificationService.list_user_notifications(db, requester.id, unread_only, page, page_size)
    return PageResponse(items=notifs, meta=PageMeta(page=page, page_size=page_size, total=total))


@router.get("/unread-count")
def get_unread_count(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"count": NotificationService.get_unread_count(db, requester.id)}


@router.put("/read", status_code=status.HTTP_200_OK)
def mark_read(body: MarkReadRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = NotificationService.mark_read(db, requester.id, body.notification_ids)
    db.commit()
    return {"marked": count}


@router.put("/read-all", status_code=status.HTTP_200_OK)
def mark_all_read(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = NotificationService.mark_all_read(db, requester.id)
    db.commit()
    return {"marked": count}


# --- Send notification (NTF-04 event trigger) ---

@router.post("/send", response_model=NotificationResponse, status_code=201)
def send_notification(body: SendNotificationRequest, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_ASSIGN)
    try:
        notif = NotificationService.send(db, body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return notif


# --- Templates (NTF-03) ---

@router.get("/templates", response_model=list[NotificationTemplateResponse])
def list_templates(requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return TemplateService.list_templates(db)


@router.post("/templates", response_model=NotificationTemplateResponse, status_code=201)
def create_template(body: NotificationTemplateCreate, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    tmpl = TemplateService.create_template(
        db, body.code, body.name, body.notification_type,
        body.title_template, body.body_template, body.channels, body.trigger_mode,
    )
    tmpl.is_active = body.is_active
    db.commit()
    return tmpl


@router.delete("/templates/{tmpl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(tmpl_id: str, requester: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_perm(db, requester, Perm.LEARNING_MANAGE)
    tmpl = db.execute(select(NotificationTemplate).where(NotificationTemplate.id == tmpl_id)).scalar_one_or_none()
    if not tmpl:
        raise HTTPException(404, "Template not found")
    TemplateService.delete_template(db, tmpl)
    db.commit()
