"""Bounded stage-4 HTTP/MySQL regression; keeps random local QA fixtures."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import uuid

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:20081"
checks = []
requests = 0


def call(client, method, path, expected=200, **kwargs):
    global requests
    response = client.request(method, path, **kwargs)
    requests += 1
    assert response.status_code == expected, f"{method} {path}: {response.status_code}, expected {expected}: {response.text[:200]}"
    return response


def main():
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from app.config import settings
    from app.database import SessionLocal
    from app.models.homework import HomeworkSubmission
    from app.models.learning import LearningRecord
    from app.models.notification import Notification
    from sqlalchemy import select, func, text
    from sqlalchemy.engine import make_url
    url = make_url(settings.database_url)
    assert (url.host, url.port, url.database, url.username) == ("127.0.0.1", 3309, "campus_learning", "campus_app")
    accounts = json.loads((ROOT / ".runtime/stage3-accounts.json").read_text(encoding="utf-8"))
    clients = {}
    for key in ("teacher", "teacher2", "student", "student2", "admin"):
        client = httpx.Client(base_url=BASE, trust_env=False, timeout=20)
        credentials = {k: accounts[key][k] for k in ("username", "password")}
        token = call(client, "POST", "/api/v1/auth/login", json=credentials).json()["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        clients[key] = client
    t, other, s, s2, admin = [clients[k] for k in ("teacher", "teacher2", "student", "student2", "admin")]
    prefix = "p4_" + uuid.uuid4().hex[:8]
    course = call(t, "POST", "/api/v1/courses", 201, json={"title": prefix+"_学习与作业", "chapters":[{"title": "第一章", "content_type": "text", "text_content": "阶段四第一章"}, {"title": "第二章", "content_type": "text", "text_content": "阶段四第二章"}]}).json()
    cid = course["id"]
    root = f"/api/v1/courses/{cid}/homeworks"
    body = {"title": "基础作业", "description": "请提交学习小结", "due_at": (datetime.now(timezone.utc)+timedelta(days=3)).isoformat(), "max_score": 100, "grading_notes": "按完整性评分", "is_required": True}
    call(other, "POST", root, 403, json=body)
    call(s, "GET", root, 403)
    h = call(t, "POST", root, 201, json=body).json()
    hid = h["id"]
    assert h["due_at"].endswith("Z") or h["due_at"].endswith("+00:00")
    call(t, "PUT", root+"/"+hid, json={**body, "grading_notes": "允许0分，未批改与0分分开"})
    temp = call(t, "POST", root, 201, json={**body, "title": "临时草稿作业"}).json()["id"]
    call(t, "DELETE", root+"/"+temp, 204)
    ui = call(t, "POST", root, 201, json={**body, "title": "页面验收作业"}).json()["id"]
    overdue = call(t, "POST", root, 201, json={**body, "title": "已截止作业", "due_at": (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()}).json()["id"]
    call(t, "POST", root, 422, json={**body, "due_at": "2026-12-31T23:00:00"})
    for action, client in (("submit_review", t), ("publish", admin)):
        call(client, "POST", f"/api/v1/courses/{cid}/publish", json={"action": action})
    call(s, "GET", root, 403)
    for student in (s, s2):
        call(student, "POST", f"/api/v1/courses/{cid}/join")
    call(s, "GET", root)
    call(other, "GET", root, 403)
    call(t, "PUT", root+"/"+hid, 409, json=body)
    call(t, "DELETE", root+"/"+hid, 409)
    checks.append("草稿作业CRUD、归属与成员范围、发布冻结、截止时间时区校验")

    first, second = [ch["id"] for ch in course["chapters"]]
    def progress(chapter, **values):
        return {"course_id": cid, "chapter_id": chapter, **values}
    call(s, "POST", "/api/v1/learning/progress", json=progress(first, progress_percent=100, learning_seconds=10))
    p = call(s, "GET", f"/api/v1/learning/progress/{cid}").json()
    assert p["overall_percent"] == 50 and not p["is_complete"]
    with SessionLocal() as db:
        assert not db.scalar(select(Notification.id).where(Notification.event_key == f"learning:{cid}:{accounts['student']['id']}"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: call(s, "POST", "/api/v1/learning/progress", json=progress(second, progress_percent=100, learning_seconds=8)), range(4)))
    p = call(s, "GET", f"/api/v1/learning/progress/{cid}").json()
    assert p["overall_percent"] == 100 and p["completed_chapters"] == 2 and p["is_complete"] and p["total_learning_seconds"] == 18
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Notification).where(Notification.event_key == f"learning:{cid}:{accounts['student']['id']}")) == 1
        assert db.scalar(select(func.count()).select_from(LearningRecord).where(LearningRecord.course_id == cid, LearningRecord.user_id == accounts["student"]["id"])) == 2
    call(s, "POST", "/api/v1/learning/progress", 422, json=progress(first, progress_percent=101))
    call(s, "POST", "/api/v1/learning/progress", 422, json=progress(first, learning_seconds=-1))
    call(s, "POST", "/api/v1/learning/progress", 422, json=progress(first, resume_position={"video_time": -1}))
    call(s2, "POST", "/api/v1/learning/progress", json=progress(first, progress_percent=0, resume_position={"video_time": 12.5}))
    assert call(s2, "GET", f"/api/v1/learning/resume/{cid}").json()["resume_position"]["video_time"] == 12.5
    with SessionLocal() as db:
        # A historical record for a removed chapter must not inflate progress or win resume selection.
        db.add(LearningRecord(user_id=accounts["student"]["id"], course_id=cid, chapter_id=str(uuid.uuid4()), progress_percent=100, status="completed", learning_seconds=99, last_accessed_at="2099-01-01T00:00:00+00:00"))
        db.commit()
    assert call(s, "GET", f"/api/v1/learning/progress/{cid}").json()["overall_percent"] == 100
    assert call(s, "GET", f"/api/v1/learning/resume/{cid}").json()["chapter_id"] in (first, second)
    checks.append("两章50%与100%、完成通知一次、并发重复完成唯一、续播位置持久化、非法进度拒绝")

    submission_url = root+f"/{hid}/submission"
    call(s, "PUT", submission_url, 422, data={"text": " "})
    with ThreadPoolExecutor(max_workers=4) as pool:
        submitted = list(pool.map(lambda _: call(s, "PUT", submission_url, data={"text": "并发首次提交"}).json()["id"], range(4)))
    assert len(set(submitted)) == 1
    call(t, "PUT", submission_url, 403, data={"text": "教师不能作答"})
    call(s, "PUT", root+f"/{overdue}/submission", 409, data={"text": "迟交"})
    call(s, "PUT", submission_url, 422, files={"file": ("fake.pdf", b"bad", "application/pdf")})
    call(s, "PUT", submission_url, 413, files={"file": ("large.pdf", b"%PDF-"+b"x"*(20*1024*1024), "application/pdf")})
    pdf = b"%PDF-1.4\n% stage 4 attachment\n%%EOF\n"
    submission = call(s, "PUT", submission_url, data={"text": "<script>plain text only</script>"}, files={"file": ("answer.pdf", pdf, "application/pdf")}).json()
    sid = submission["id"]
    attachment = root+f"/{hid}/submissions/{sid}/attachment"
    assert call(s, "GET", attachment).content == pdf
    assert call(t, "GET", attachment).content == pdf
    call(s2, "GET", attachment, 403)
    call(other, "GET", attachment, 403)
    with httpx.Client(base_url=BASE, trust_env=False) as anonymous:
        call(anonymous, "GET", attachment, 401)
    assert call(s, "PUT", submission_url, data={"text": "截止前修改，保留原附件"}).json()["id"] == sid
    assert call(s, "PUT", submission_url, data={"text": "删除附件", "remove_attachment": "true"}).json()["attachment_name"] is None
    call(s, "GET", attachment, 404)
    call(s, "PUT", submission_url, data={"text": "正式提交"}, files={"file": ("final.pdf", pdf, "application/pdf")})
    call(s2, "PUT", submission_url, data={"text": "第二名学生的提交"})
    checks.append("文字/单附件提交修改删除、超限与伪格式拒绝、附件仅本人和任课教师读取")

    call(s, "GET", root+f"/{hid}/submissions", 403)
    listed = call(t, "GET", root+f"/{hid}/submissions").json()
    assert listed["meta"]["total"] == 2 and all(x["score"] is None and x["graded_at"] is None for x in listed["items"])
    grade_url = root+f"/{hid}/submissions/{sid}/grade"
    call(other, "POST", grade_url, 403, json={"score": 10})
    call(s, "POST", grade_url, 403, json={"score": 10})
    call(t, "POST", grade_url, 422, json={"score": -1})
    call(t, "POST", grade_url, 422, json={"score": 101})
    for _ in range(2):
        graded = call(t, "POST", grade_url, json={"score": 0, "feedback": "已批改，得分为零"}).json()
        assert graded["score"] == 0 and graded["graded_at"]
    call(s, "PUT", submission_url, 409, data={"text": "批改后改交"})
    student_view = call(s, "GET", root).json()["items"]
    assert next(x for x in student_view if x["id"] == hid)["submission"]["score"] == 0
    roster = call(t, "GET", f"/api/v1/learning/courses/{cid}/students").json()
    assert roster["meta"]["total"] == 2
    assert {x["overall_percent"] for x in roster["items"]} == {0, 100}
    call(s, "GET", f"/api/v1/learning/courses/{cid}/students", 403)
    call(other, "GET", f"/api/v1/learning/courses/{cid}/students", 403)
    with SessionLocal() as db:
        persisted = db.get(HomeworkSubmission, sid)
        assert persisted.score == 0 and persisted.graded_at and persisted.feedback == "已批改，得分为零"
        notices = db.scalars(select(Notification).where(Notification.user_id == accounts["student"]["id"], Notification.title == "作业已批改")).all()
        assert sum(n.extra_data.get("homework_id") == hid for n in notices) == 1
        mysql = db.scalar(text("SELECT VERSION()"))
    checks.append("两学生提交、零分已批与未批区分、评分范围、重复批改通知去重、新会话持久化、教师学生表")

    archived = call(t, "POST", "/api/v1/courses", 201, json={"title": prefix+"_归档", "chapters":[{"title":"章节","content_type":"text","text_content":"历史"}]}).json()["id"]
    ah = call(t,"POST",f"/api/v1/courses/{archived}/homeworks",201,json=body).json()["id"]
    for action,client in (("submit_review",t),("publish",admin)):
        call(client,"POST",f"/api/v1/courses/{archived}/publish",json={"action":action})
    call(s,"POST",f"/api/v1/courses/{archived}/join")
    call(s,"PUT",f"/api/v1/courses/{archived}/homeworks/{ah}/submission",data={"text":"归档前提交"})
    call(admin,"POST",f"/api/v1/courses/{archived}/publish",json={"action":"archive"})
    call(s,"GET",f"/api/v1/courses/{archived}/homeworks")
    call(s,"PUT",f"/api/v1/courses/{archived}/homeworks/{ah}/submission",403,data={"text":"归档后修改"})
    checks.append("归档保留作业历史并停止新提交")
    summary = {"tested_at":datetime.now(timezone.utc).isoformat(),"mysql":mysql,"course_id":cid,"homework_id":hid,"ui_homework_id":ui,"http_requests":requests,"checks":checks,"scope":"Stage 4; exams remain stage 5"}
    (ROOT/".runtime/stage4-results.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"groups_passed":len(checks),"http_requests":requests,"results":".runtime/stage4-results.json"}))
    for client in clients.values():
        client.close()


if __name__ == "__main__":
    main()
