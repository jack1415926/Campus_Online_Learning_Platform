"""Focused HTTP/MySQL chapter ordering checks; keeps isolated QA fixtures."""
import json
import os
from pathlib import Path
import sys
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.database import SessionLocal
    from app.models.course import Chapter
    url = make_url(settings.database_url)
    assert (url.host, url.port, url.database, url.username) == ("127.0.0.1", 3309, "campus_learning", "campus_app")
    accounts = json.loads((ROOT / ".runtime/stage3-accounts.json").read_text(encoding="utf-8"))
    clients, requests = [], 0

    def call(client, method, path, expected=200, **kwargs):
        nonlocal requests
        response = client.request(method, "/api/v1" + path, **kwargs)
        requests += 1
        assert response.status_code == expected, (method, path, response.status_code, response.text[:200])
        return response.json() if response.content else None

    try:
        for role in ("teacher", "teacher2", "admin"):
            client = httpx.Client(base_url="http://127.0.0.1:20081", trust_env=False, timeout=20)
            clients.append(client)
            token = call(client, "POST", "/auth/login", json={k: accounts[role][k] for k in ("username", "password")})["access_token"]
            client.headers["Authorization"] = "Bearer " + token
        teacher, other, admin = clients
        prefix = "chapter_order_" + uuid.uuid4().hex[:8]
        body = {"title": prefix, "chapters": [{"title": "第一章", "content_type": "text", "text_content": "章节一", "sort_order": 10}, {"title": "第二章", "content_type": "text", "text_content": "章节二", "sort_order": 20}]}
        course = call(teacher, "POST", "/courses", 201, json=body)
        cid = course["id"]
        chapters = call(teacher, "GET", f"/courses/{cid}")["chapters"]
        second = chapters[1]["id"]
        path = f"/courses/{cid}/chapters/{second}"
        call(other, "PUT", path, 403, json={"sort_order": 5})
        for invalid in (-1, None, 1000001):
            call(teacher, "PUT", path, 422, json={"sort_order": invalid})
        call(teacher, "PUT", path, json={"sort_order": 5})
        ordered = call(teacher, "GET", f"/courses/{cid}")["chapters"]
        assert [c["title"] for c in ordered] == ["第二章", "第一章"]
        with SessionLocal() as db:
            assert db.get(Chapter, second).sort_order == 5
        for client, action in ((teacher, "submit_review"), (admin, "publish")):
            call(client, "POST", f"/courses/{cid}/publish", json={"action": action})
        call(teacher, "PUT", path, 409, json={"sort_order": 1})
        ui = call(teacher, "POST", "/courses", 201, json={**body, "title": prefix + "_页面验证"})
        summary = {"status": "PASS", "http_requests": requests, "course_id": cid, "ui_course_id": ui["id"], "checks": ["调整顺序后接口返回新顺序", "新数据库会话重读顺序", "其他教师不能调整", "非法顺序拒绝", "发布后不能调整"]}
        (ROOT / ".runtime/chapter-order-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: summary[k] for k in ("status", "http_requests", "ui_course_id")}))
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()
