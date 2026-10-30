"""Real HTTP/MySQL regression for blank short answers; keeps isolated QA data."""
from datetime import datetime, timedelta, timezone
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
    from sqlalchemy import func, select
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.database import SessionLocal
    from app.models.exam import ExamRecord
    from app.models.notification import Notification

    url = make_url(settings.database_url)
    assert (url.host, url.port, url.database, url.username) == ("127.0.0.1", 3309, "campus_learning", "campus_app")
    accounts = json.loads((ROOT / ".runtime/stage3-accounts.json").read_text(encoding="utf-8"))
    clients = []
    requests = 0

    def call(client, method, path, expected=200, **kwargs):
        nonlocal requests
        response = client.request(method, "/api/v1" + path, **kwargs)
        requests += 1
        assert response.status_code == expected, (method, path, response.status_code, response.text[:200])
        return response.json() if response.content else None

    try:
        for role in ("teacher", "student", "admin"):
            client = httpx.Client(base_url="http://127.0.0.1:20081", trust_env=False, timeout=20)
            clients.append(client)
            token = call(client, "POST", "/auth/login", json={k: accounts[role][k] for k in ("username", "password")})["access_token"]
            client.headers["Authorization"] = "Bearer " + token
        teacher, student, admin = clients
        prefix = "blank_" + uuid.uuid4().hex[:8]
        course = call(teacher, "POST", "/courses", 201, json={"title": prefix, "chapters": [{"title": "说明", "content_type": "text", "text_content": "空白简答题回归"}]})["id"]
        ids = [call(teacher, "POST", "/exams/questions", 201, json={"question_type": "short_answer", "content": f"{prefix}_{i}", "correct_answer": "参考答案", "score": 2})["id"] for i in range(7)]
        current = datetime.now(timezone.utc)
        exam = call(teacher, "POST", "/exams", 201, json={"title": prefix, "course_id": course, "question_ids": ids, "duration_minutes": 30, "max_attempts": 3, "pass_score": 10, "start_time": (current - timedelta(minutes=1)).isoformat(), "end_time": (current + timedelta(days=1)).isoformat()})["id"]
        for client, action in ((teacher, "submit_review"), (admin, "publish")):
            call(client, "POST", f"/courses/{course}/publish", json={"action": action})
        call(student, "POST", f"/courses/{course}/join")
        # The sixth and seventh questions are omitted; the other five cover all accepted empty forms.
        blanks = [{"question_id": qid, "answer": value} for qid, value in zip(ids, (None, "", " \t\r\n", "\u3000", []))]
        record_ids = []
        for mode in ("manual", "mixed", "expired"):
            record = call(student, "POST", f"/exams/{exam}/start")
            rid = record["id"]
            record_ids.append(rid)
            answers = blanks + ([{"question_id": ids[-1], "answer": "有内容的作答"}] if mode == "mixed" else [])
            path = f"/exams/records/{rid}"
            if mode == "expired":
                call(student, "PUT", path + "/draft", json={"answers": answers})
                with SessionLocal() as db:
                    db.get(ExamRecord, rid).deadline_at = (current - timedelta(seconds=1)).isoformat()
                    db.commit()
                # Late nonempty text must not replace the saved blank draft.
                answers = [{"question_id": ids[0], "answer": "超时新答案"}]
            result = call(student, "POST", path + "/submit", json={"answers": answers})
            assert result["max_score"] == 14 and result["total_score"] == 0
            assert all(a["graded"] and a["score"] == 0 and a["is_correct"] is False for a in result["answers"][:-1])
            if mode == "mixed":
                assert result["status"] == "submitted" and result["is_pass"] is None
                assert result["answers"][-1]["graded"] is False
                call(teacher, "POST", path + "/grade", 409, json={"answers": [{"question_id": ids[0], "score": 1}]})
                result = call(teacher, "POST", path + "/grade", json={"answers": [{"question_id": ids[-1], "score": 2, "grader_comment": "非空题人工批改"}]})
            assert result["status"] == "graded" and result["is_pass"] is (mode == "mixed")
            assert all(a["graded"] for a in result["answers"])
            retry = call(student, "POST", path + "/submit", json={"answers": []})
            assert retry == result
            call(teacher, "POST", path + "/grade", 409, json={"answers": [{"question_id": ids[0], "score": 1}]})
            with SessionLocal() as db:
                saved = db.get(ExamRecord, rid)
                assert saved.status.value == "graded" and saved.total_score == (2 if mode == "mixed" else 0)
                assert all(a["graded"] for a in saved.answers)
                assert db.scalar(select(func.count()).select_from(Notification).where(Notification.event_key == f"exam:{rid}")) == 1
        summary = {"status": "PASS", "http_requests": requests, "course_id": course, "exam_id": exam, "record_ids": record_ids, "checks": ["空值、空串、空白、全角空格、空列表及漏答自动0分", "有内容的简答题仍待人工批改", "空白题不可人工改分", "超时结算只用已保存草稿", "重复交卷、通知去重和新MySQL会话持久化"]}
        (ROOT / ".runtime/blank-short-answers-results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False))
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()
