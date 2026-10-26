"""FastAPI application entry point."""

import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.config import settings
from app.core.seed import seed_rbac
from app.database import SessionLocal
from app.services.deadline_reminder_service import check_and_notify

logger = logging.getLogger(__name__)

REMINDER_INTERVAL_SECONDS = 24 * 60 * 60  # run once per day


def _run_deadline_check():
    db = SessionLocal()
    try:
        check_and_notify(db)
    finally:
        db.close()


async def _deadline_reminder_loop():
    """Periodically check course-assignment deadlines and send reminders."""
    while True:
        try:
            await asyncio.to_thread(_run_deadline_check)
        except Exception:
            logger.exception("Deadline reminder loop error")
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)


async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_rbac(db)
        db.commit()
        logger.info("Database seeding completed")
    except Exception as e:
        db.rollback()
        logger.warning("Database seeding skipped: %s", e)
    finally:
        db.close()

    reminder_task = asyncio.create_task(_deadline_reminder_loop())
    logger.info("Deadline reminder loop started")
    try:
        yield
    finally:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="校园在线学习平台 API",
    lifespan=lifespan,
)

from starlette.middleware.base import BaseHTTPMiddleware

class CharsetMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        ct = response.headers.get('content-type', '')
        if ('text/html' in ct or 'javascript' in ct or 'text/css' in ct) and 'charset' not in ct:
            response.headers['content-type'] = ct + '; charset=utf-8'
        return response

app.add_middleware(CharsetMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (must be before catch-all)
app.include_router(api_router, prefix="/api/v1")

# Static files and SPA fallback
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    storage_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "storage")
    os.makedirs(storage_dir, exist_ok=True)
    app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")

    @app.get("/", response_class=FileResponse)
    async def index():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # StaticFiles owns file serving; never resolve a route as a disk path.
        return FileResponse(os.path.join(static_dir, "index.html"))
