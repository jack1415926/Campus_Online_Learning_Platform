"""Aggregate all v1 API routers."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.core.permissions import Perm
from app.core.rbac import require_permission
from app.core.campus_access import require_admin, roles_for

from app.api.v1.auth import router as auth_router
from app.api.v1.sso import router as sso_router
from app.api.v1.users import router as users_router
from app.api.v1.categories import router as categories_router, tag_router
from app.api.v1.media import router as media_router
from app.api.v1.courses import router as courses_router
from app.api.v1.certificates import router as certificates_router
from app.api.v1.platform import router as platform_router
from app.api.v1.communication import router as communication_router
from app.api.v1.homework import router as homework_router
from app.api.v1.learning import router as learning_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.exams import router as exams_router
from app.api.v1.reports import router as reports_router
from app.api.v1.dictionary import (
    job_level_router,
    position_router,
    department_router,
)

api_router = APIRouter()
admin_only = [Depends(require_permission(Perm.SYSTEM_CONFIG))]


def taxonomy_access(request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    if request.method != "GET":
        require_admin(db, user)


api_router.include_router(auth_router)
api_router.include_router(sso_router, dependencies=admin_only)
api_router.include_router(users_router)
api_router.include_router(categories_router, dependencies=[Depends(taxonomy_access)])
api_router.include_router(tag_router, dependencies=[Depends(taxonomy_access)])
api_router.include_router(media_router)
api_router.include_router(courses_router)
api_router.include_router(certificates_router)
api_router.include_router(platform_router)
api_router.include_router(communication_router)
api_router.include_router(homework_router)
api_router.include_router(learning_router)
api_router.include_router(notifications_router)
api_router.include_router(exams_router)
# Remaining legacy modules stay admin-only until their campus scope is implemented.
api_router.include_router(reports_router, dependencies=admin_only)
api_router.include_router(job_level_router, dependencies=admin_only)
api_router.include_router(position_router, dependencies=admin_only)
api_router.include_router(department_router, dependencies=admin_only)


@api_router.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


@api_router.get("/ready", tags=["system"])
def readiness_check(db: Session = Depends(get_db)):
    """Unlike liveness, readiness requires a reachable, migrated database."""
    try:
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        if not revision:
            raise HTTPException(503, "Database is not ready")
    except SQLAlchemyError:
        raise HTTPException(503, "Database is not ready") from None
    return {"status": "ok"}
