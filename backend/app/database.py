"""SQLAlchemy database engine and session management.

Uses synchronous PyMySQL driver with SQLAlchemy sync engine.
FastAPI handles async via threadpool automatically.
This is more stable on Windows than async aiomysql.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Convert async URL to sync URL
sync_url = settings.database_url.replace("+aiomysql", "")

engine = create_engine(
    sync_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(
    engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()