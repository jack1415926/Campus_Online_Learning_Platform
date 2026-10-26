"""Aggregate all v1 API routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.sso import router as sso_router
from app.api.v1.users import router as users_router
from app.api.v1.categories import router as categories_router, tag_router
from app.api.v1.media import router as media_router
from app.api.v1.courses import router as courses_router
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
api_router.include_router(auth_router)
api_router.include_router(sso_router)
api_router.include_router(users_router)
api_router.include_router(categories_router)
api_router.include_router(tag_router)
api_router.include_router(media_router)
api_router.include_router(courses_router)
api_router.include_router(learning_router)
api_router.include_router(notifications_router)
api_router.include_router(exams_router)
api_router.include_router(reports_router)
api_router.include_router(job_level_router)
api_router.include_router(position_router)
api_router.include_router(department_router)


@api_router.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}
