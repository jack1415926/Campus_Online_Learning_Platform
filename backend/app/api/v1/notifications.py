"""Notification API (NTF-01 through NTF-04)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import PageMeta, PageResponse
from app.schemas.notification import MarkReadRequest, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


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
