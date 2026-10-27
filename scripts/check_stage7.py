"""Focused certificate checks against the project's local MySQL and HTTP app."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[1]
requests = 0


def call(client, method, path, expected=200, **kwargs):
    global requests
    response = client.request(method, path, **kwargs)
    requests += 1
    assert response.status_code == expected, f"{method} {path}: {response.status_code}: {response.text[:200]}"
    return response.json() if response.content else None


def main():
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy import func, select, text
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.database import SessionLocal
    from app.models.certificate import Certificate

    url = make_url(settings.database_url)
    assert (url.host, url.port, url.database, url.username) == ("127.0.0.1", 3309, "campus_learning", "campus_app")
    accounts = json.loads((ROOT / ".runtime/stage3-accounts.json").read_text(encoding="utf-8"))
    clients = {}
    for role in ("teacher", "teacher2", "student", "student2", "admin"):
        client = httpx.Client(base_url="http://127.0.0.1:20081", trust_env=False, timeout=20)
        account = accounts[role]
        token = call(client, "POST", "/api/v1/auth/login", json={k: account[k] for k in ("username", "password")})["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        clients[role] = client
    t, other, s, s2, admin = [clients[r] for r in ("teacher", "teacher2", "student", "student2", "admin")]
    checks = []
    prefix = "p7_" + uuid.uuid4().hex[:8]
    course = call(t, "POST", "/api/v1/courses", 201, json={"title": prefix + "_证书演示", "chapters": [
        {"title": "第一章", "content_type": "text", "text_content": "章节一"},
        {"title": "第二章", "content_type": "text", "text_content": "章节二"}]})
    cid = course["id"]
    root = f"/api/v1/courses/{cid}"
    qids = [call(t, "POST", "/api/v1/exams/questions", 201, json={"question_type": "short_answer", "content": prefix+f"_简答{i}", "correct_answer": "要点", "score": 5})["id"] for i in range(2)]
    exam_body = {"title": prefix+"_结课考核", "course_id": cid, "question_ids": qids, "question_scores": {}, "duration_minutes": 30, "max_attempts": 2, "pass_score": 50,
        "start_time": (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(), "end_time": (datetime.now(timezone.utc)+timedelta(days=3)).isoformat()}
    eid = call(t, "POST", "/api/v1/exams", 201, json=exam_body)["id"]
    homework = call(t, "POST", root+"/homeworks", 201, json={"title": "必交作业", "description": "学习小结", "due_at": (datetime.now(timezone.utc)+timedelta(days=2)).isoformat(), "max_score": 100, "is_required": True})["id"]
    call(other, "PUT", root, 403, json={"certificate_exam_id": eid})
    call(t, "PUT", root, 422, json={"certificate_exam_id": str(uuid.uuid4())})
    call(t, "PUT", root, json={"certificate_exam_id": eid})
    call(t, "DELETE", f"/api/v1/exams/{eid}", 409)
    cross = call(t, "POST", "/api/v1/courses", 201, json={"title": prefix+"_无作业课程", "chapters": [{"title": "说明", "content_type": "text", "text_content": "无必交作业"}]})
    call(t, "PUT", f"/api/v1/courses/{cross['id']}", 422, json={"certificate_exam_id": eid})
    for action, client in (("submit_review", t), ("publish", admin)):
        call(client, "POST", root+"/publish", json={"action": action})
    call(t, "PUT", root, 409, json={"certificate_exam_id": None})
    call(s, "POST", root+"/certificate", 403)
    for client in (s, s2):
        call(client, "POST", root+"/join")
    call(t, "POST", root+"/certificate", 403)
    call(other, "GET", root+"/certificates", 403)
    call(s, "GET", root+"/certificates", 403)
    checks.append("草稿配置本课程考核、跨课程/教师拒绝、发布后冻结、学生与教师数据范围")

    def claim_denied(reason):
        state = call(s, "GET", root+"/certificate")
        assert not state["eligible"] and any(reason in r for r in state["reasons"]), state
        call(s, "POST", root+"/certificate", 409)

    claim_denied("章节")
    for chapter in course["chapters"]:
        call(s, "POST", "/api/v1/learning/progress", json={"course_id": cid, "chapter_id": chapter["id"], "progress_percent": 100})
    claim_denied("作业")
    submission = call(s, "PUT", root+f"/homeworks/{homework}/submission", data={"text": "学习小结"})["id"]
    claim_denied("作业")
    call(t, "POST", root+f"/homeworks/{homework}/submissions/{submission}/grade", json={"score": 0, "feedback": "已批改即可，不设及格线"})
    claim_denied("最终及格")
    rid = call(s, "POST", f"/api/v1/exams/{eid}/start")["record_id"]
    call(s, "POST", f"/api/v1/exams/records/{rid}/submit", json={"answers": []})
    call(t, "POST", f"/api/v1/exams/records/{rid}/grade", json={"answers": [{"question_id": q, "score": 0} for q in qids]})
    claim_denied("最终及格")
    rid = call(s, "POST", f"/api/v1/exams/{eid}/start")["record_id"]
    call(s, "POST", f"/api/v1/exams/records/{rid}/submit", json={"answers": []})
    call(t, "POST", f"/api/v1/exams/records/{rid}/grade", json={"answers": [{"question_id": qids[0], "score": 5}]})
    claim_denied("最终及格")
    grade = {"answers": [{"question_id": qids[1], "score": 0}]}
    call(t, "POST", f"/api/v1/exams/records/{rid}/grade", json=grade)
    call(t, "POST", f"/api/v1/exams/records/{rid}/grade", json=grade)
    call(t, "POST", f"/api/v1/exams/records/{rid}/grade", 409, json={"answers": [{"question_id": qids[0], "score": 0}]})
    assert call(s, "GET", root+"/certificate")["eligible"]
    checks.append("缺章节、未交/待批作业、未通过/部分阅卷不能领取；作业0分已批有效；最终成绩禁止改分")

    with ThreadPoolExecutor(max_workers=3) as pool:
        certificates = list(pool.map(lambda _: call(s, "POST", root+"/certificate"), range(3)))
    cert = certificates[0]
    assert len({c["id"] for c in certificates}) == 1
    assert call(s, "POST", root+"/certificate")["id"] == cert["id"]
    assert call(s2, "GET", root+"/certificate")["certificate"] is None
    teacher_list = call(t, "GET", root+"/certificates")
    assert teacher_list["meta"]["total"] == 1 and teacher_list["items"][0]["id"] == cert["id"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Certificate).where(Certificate.course_id == cid)) == 1
        saved = db.get(Certificate, cert["id"])
        assert saved.exam_record_id == rid and saved.course_title == course["title"] and saved.student_name == cert["student_name"]
    profile = call(s, "GET", "/api/v1/users/me/profile")
    original = profile["full_name"]
    try:
        call(s, "PUT", "/api/v1/users/me/profile", json={"full_name": "领取后改名", "email": profile["email"]})
        assert call(s, "GET", root+"/certificate")["certificate"]["student_name"] == original
    finally:
        call(s, "PUT", "/api/v1/users/me/profile", json={"full_name": original, "email": profile["email"]})
    checks.append("并发/重复领取唯一、新数据库会话持久化、姓名快照、教师颁发列表与学生隔离")

    call(admin, "POST", root+"/publish", 409, json={"action": "unpublish"})
    call(admin, "POST", root+"/publish", json={"action": "archive"})
    assert call(s, "GET", root+"/certificate")["certificate"]["id"] == cert["id"]
    assert call(s, "POST", root+"/certificate")["id"] == cert["id"]
    call(s2, "POST", root+"/certificate", 409)
    checks.append("发证课程不可退回草稿；归档保留已发证书且停止新发")

    cross_root = f"/api/v1/courses/{cross['id']}"
    # No required homework: a passing designated exam and completed chapter suffice.
    cross_exam = call(t, "POST", "/api/v1/exams", 201, json={**exam_body, "course_id": cross["id"]})["id"]
    call(t, "PUT", cross_root, json={"certificate_exam_id": cross_exam})
    for action, client in (("submit_review", t), ("publish", admin)):
        call(client, "POST", cross_root+"/publish", json={"action": action})
    call(s, "POST", cross_root+"/join")
    call(s, "POST", "/api/v1/learning/progress", json={"course_id": cross["id"], "chapter_id": cross["chapters"][0]["id"], "progress_percent": 100})
    cross_rid = call(s, "POST", f"/api/v1/exams/{cross_exam}/start")["record_id"]
    call(s, "POST", f"/api/v1/exams/records/{cross_rid}/submit", json={"answers": []})
    call(t, "POST", f"/api/v1/exams/records/{cross_rid}/grade", json={"answers": [{"question_id": q, "score": 5} for q in qids]})
    assert call(s, "GET", cross_root+"/certificate")["eligible"]
    call(s, "POST", cross_root+"/certificate")
    checks.append("无必交作业不增加作业条件")
    with SessionLocal() as db:
        mysql, migration = db.scalar(text("SELECT VERSION()")), db.scalar(text("SELECT version_num FROM alembic_version"))
    summary = {"tested_at": datetime.now(timezone(timedelta(hours=8))).isoformat(), "course_id": cid, "certificate_id": cert["id"], "http_requests": requests, "checks": checks, "mysql": mysql, "migration": migration, "scope": "Stage 7 batch 1: certificates only"}
    (ROOT / ".runtime/stage7-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"groups_passed": len(checks), "http_requests": requests, "results": ".runtime/stage7-results.json"}))
    for client in clients.values():
        client.close()


if __name__ == "__main__":
    main()
