"""Only settings and local assets; does not repeat earlier business regressions."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import sys
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy import select
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.database import SessionLocal
    from app.models.platform import PlatformSettings
    from app.models.certificate import Certificate
    url = make_url(settings.database_url)
    assert (url.host, url.port, url.database, url.username) == ("127.0.0.1", 3309, "campus_learning", "campus_app")
    accounts = json.loads((ROOT / ".runtime/stage3-accounts.json").read_text(encoding="utf-8"))
    count = 0
    def call(client, method, path, expected=200, **kwargs):
        nonlocal count
        r = client.request(method, path, **kwargs)
        count += 1
        assert r.status_code == expected, f"{method} {path}: {r.status_code}: {r.text[:150]}"
        return r
    with httpx.Client(base_url="http://127.0.0.1:20081", trust_env=False, timeout=20) as public, httpx.Client(base_url="http://127.0.0.1:20081", trust_env=False, timeout=20) as admin, httpx.Client(base_url="http://127.0.0.1:20081", trust_env=False, timeout=20) as student:
        for role, client in (("admin", admin), ("student", student)):
            a = accounts[role]
            token = call(client, "POST", "/api/v1/auth/login", json={k: a[k] for k in ("username", "password")}).json()["access_token"]
            client.headers["Authorization"] = "Bearer " + token
            state = {"cookies": [], "origins": [{"origin": "http://127.0.0.1:20081", "localStorage": [{"name": "lms_token", "value": token}]}]}
            (ROOT / f".runtime/stage7-{role}-state.json").write_text(json.dumps(state), encoding="utf-8")
        path = "/api/v1/platform-settings"
        original = call(public, "GET", path).json()
        call(public, "PUT", path, 401, json=original)
        call(student, "PUT", path, 403, json=original)
        call(admin, "PUT", path, 422, json={**original, "platform_name": " "})
        with SessionLocal() as db:
            existing = {c.id: c.platform_name for c in db.scalars(select(Certificate))}
        try:
            modified = {"platform_name": "校园实验周平台", "registration_open": False}
            assert call(admin, "PUT", path, json=modified).json() == modified
            assert call(public, "GET", path).json() == modified
            with SessionLocal() as db:
                row = db.get(PlatformSettings, 1)
                assert row.platform_name == modified["platform_name"] and not row.registration_open
                assert {c.id: c.platform_name for c in db.scalars(select(Certificate))} == existing
            prefix = "p7s_" + uuid.uuid4().hex[:8]
            registration = {"username": prefix, "full_name": "设置检查学生", "email": prefix+"@example.com", "password": secrets.token_urlsafe(18), "role": "student"}
            call(public, "POST", "/api/v1/auth/register", 403, json=registration)
            call(admin, "PUT", path, json={**modified, "registration_open": True})
            call(public, "POST", "/api/v1/auth/register", 201, json=registration)
        finally:
            call(admin, "PUT", path, json=original)
        index = call(public, "GET", "/").text
        assert "https://unpkg.com" not in index
        assets = ["vue-3.5.13/vue.global.prod.js", "element-plus-2.9.1/index.full.min.js", "element-plus-2.9.1/index.css", "icons-vue-2.3.1/index.iife.min.js", "pdfjs-2.16.105/pdf.min.js", "pdfjs-2.16.105/pdf.worker.min.js"]
        for name in assets:
            r = call(public, "GET", "/static/vendor/"+name)
            assert r.content == (ROOT / "backend/static/vendor" / name).read_bytes()
        assert 'workerSrc = "/static/vendor/' in (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
    summary = {"tested_at": datetime.now(timezone(timedelta(hours=8))).isoformat(), "http_requests": count,
        "checks": ["管理员写权限及两个设置持久化", "注册关闭后端拒绝、重开可注册、测试结束恢复设置", "已有证书平台名称快照保持", "六项前端资源由本地HTTP提供及本地PDF worker"], "scope": "Remaining stage 7 settings and resources only"}
    (ROOT / ".runtime/stage7-maintenance-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"groups_passed": len(summary["checks"]), "http_requests": count}))


if __name__ == "__main__":
    main()
