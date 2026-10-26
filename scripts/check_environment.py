"""Check the real local database and running app; delete only this check's row."""

import json
import os
from pathlib import Path
import sys
import uuid

import httpx
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT / "backend")
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from app.database import SessionLocal, engine
from app.models.course import Course


def main():
    url = make_url(settings.database_url)
    if (url.host, url.port, url.database, url.username) != ("127.0.0.1", 3309, "campus_learning", "campus_app"):
        raise RuntimeError("This check writes only to the local campus_learning database.")
    with engine.connect() as connection:
        version, database, user = connection.execute(text("SELECT VERSION(), DATABASE(), CURRENT_USER()")).one()
        assert version.startswith("8.4.")
        assert database == "campus_learning" and user == "campus_app@127.0.0.1"
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        try:
            connection.execute(text("SELECT COUNT(*) FROM mysql.user"))
        except OperationalError as error:
            assert error.orig.args[0] in (1044, 1142), error.orig.args[0]
        else:
            raise AssertionError("Application user unexpectedly has MySQL system-table access.")

    # Verify transaction persistence and JSON round-trip in a fresh ORM session.
    check_id = str(uuid.uuid4())
    check_title = "环境持久化检查_" + check_id
    payload = {"stage": 2, "text": "中文持久化", "chapters": [1, 2]}
    try:
        with SessionLocal() as db:
            db.add(Course(id=check_id, title=check_title, description="temporary environment check", completion_config=payload))
            db.commit()
        with SessionLocal() as db:
            course = db.execute(select(Course).where(Course.id == check_id)).scalar_one()
            assert course.title == check_title
            assert course.completion_config == payload
    finally:
        with SessionLocal() as db:
            course = db.get(Course, check_id)
            if course is not None:
                db.delete(course)
                db.commit()

    credentials = json.loads((ROOT / ".runtime/admin.json").read_text(encoding="utf-8"))
    with httpx.Client(base_url="http://127.0.0.1:20081", timeout=10, trust_env=False) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert client.get("/api/v1/ready").json() == {"status": "ok"}
        assert "校园在线学习平台" in client.get("/").text
        spec = client.get("/openapi.json").json()
        assert spec["info"]["title"] == "校园在线学习平台"
        response = client.post("/api/v1/auth/login", json=credentials)
        assert response.status_code == 200, response.status_code
        token = response.json()["access_token"]
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 200, response.status_code
        profile = response.json()
        assert profile["username"] == "campus_admin"
        assert "admin" in profile["roles"]
        assert client.get("/api/v1/auth/me").status_code == 401
        assert client.get("/api/v1/not-an-api").status_code == 404

    summary = {
        "python": sys.version.split()[0], "mysql": version,
        "database": database, "database_user": user,
        "alembic_revision": revision, "table_count": len(inspect(engine).get_table_names()),
        "cross_session_json_persistence": "PASS", "system_table_access_denied": "PASS",
        "http_readiness_and_login": "PASS", "temporary_row_cleaned": "PASS",
        "scope": "Environment checks only, not full campus business acceptance",
    }
    (ROOT / ".runtime/environment-check.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
