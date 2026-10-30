"""Create one isolated, repeatable campus demonstration set without clearing data."""
import json
import os
from pathlib import Path
import secrets
import sys
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".runtime/demo.json"


def main():
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from sqlalchemy import select
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.database import SessionLocal
    from app.core.security import hash_password
    from app.core.seed import assign_role
    from app.models.user import User
    from app.models.course import Course, Chapter, CourseStatus
    from app.models.learning import CourseAssignment, AssignmentType
    from app.models.homework import Homework
    from app.models.exam import Exam, Question, QuestionType
    from app.models.communication import DiscussionTopic
    from app.schemas.exam import ExamCreate
    from app.services.campus_exam_service import write_exam

    url = make_url(settings.database_url)
    if (url.host, url.port, url.database, url.username) != ("127.0.0.1", 3309, "campus_learning", "campus_app"):
        raise RuntimeError("Demo initialization only supports the project's local campus database.")
    with SessionLocal() as db:
        if STATE.exists():
            state = json.loads(STATE.read_text(encoding="utf-8"))
            if (not all(db.get(User, account["id"]) for account in state["accounts"].values())
                    or not db.get(Course, state["course_id"])
                    or not db.get(Homework, state["homework_id"])
                    or not db.get(Exam, state["exam_id"])):
                raise RuntimeError("Demo manifest does not match this database; inspect it before creating another set.")
            print("Demo data already exists; no accounts, passwords or learning results were reset.")
            print("Login details: .runtime/demo.json")
            return
        usernames = {"admin": "campus_demo_admin", "teacher": "campus_demo_teacher", "student": "campus_demo_student1", "student2": "campus_demo_student2"}
        if db.scalar(select(User.id).where(User.username.in_(usernames.values())).limit(1)):
            raise RuntimeError("Reserved demo usernames already exist without a manifest; no existing users were changed.")
        current = datetime.now(timezone.utc)
        accounts, users = {}, {}
        for key, username in usernames.items():
            role = "student" if key.startswith("student") else key
            password = secrets.token_urlsafe(18)
            name = {"admin": "演示管理员", "teacher": "陈老师", "student": "林同学", "student2": "周同学"}[key]
            user = User(username=username, email=username + "@example.test", full_name=name, password_hash=hash_password(password), requested_role=role)
            db.add(user)
            db.flush()
            assign_role(db, user, role)
            users[key] = user
            accounts[key] = {"id": str(user.id), "username": username, "password": password, "name": name}
        teacher, admin = users["teacher"], users["admin"]
        teacher.teacher_review_status = "approved"
        teacher.teacher_reviewed_by = str(admin.id)
        teacher.teacher_reviewed_at = current
        course = Course(title="校园演示：计算机网络入门", description="两章学习、学习小结、四题型考核、讨论私信和结课证书。演示专用虚构数据。", instructor=teacher.full_name, created_by=str(teacher.id))
        db.add(course)
        db.flush()
        for order, title, content in (
            (10, "第一章：认识计算机网络", "计算机网络把多台设备连接起来，实现资源共享和信息交换。\n学习目标：理解主机、交换机、路由器的作用，并区分局域网和广域网。"),
            (20, "第二章：HTTP 请求与响应", "浏览器向服务端发送 HTTP 请求，服务端返回状态码和响应内容。\n200 表示成功，401 表示需要有效身份，403 表示无权访问。\n学习后完成本章，再提交学习小结并参加结课考试。"),
        ):
            db.add(Chapter(course_id=course.id, title=title, content_type="text", text_content=content, sort_order=order, estimated_minutes=10))
        homework = Homework(course_id=course.id, title="学习小结：描述一次网页访问", description="用自己的话描述浏览器访问校园平台的过程，说明请求、响应和登录身份的作用。可交文字，或附一份 PDF/DOCX/JPG/PNG 文件。", due_at=(current + timedelta(days=30)).replace(tzinfo=None), max_score=100, grading_notes="过程完整 60 分，概念准确 40 分。", is_required=True)
        db.add(homework)
        options = [{"key": "A", "text": "200"}, {"key": "B", "text": "401"}, {"key": "C", "text": "403"}]
        paper = [
            ("single_choice", "HTTP 请求成功通常使用哪个状态码？", options, "A", 20),
            ("multiple_choice", "下列哪些状态码表示本次请求不能正常获取受保护资源？", options, ["B", "C"], 20),
            ("true_false", "服务端仍应校验权限，不能只依赖隐藏网页按钮。", None, "true", 20),
            ("short_answer", "简述 HTTP 请求和响应的关系。", None, "客户端发送请求，服务端处理后返回响应。", 20),
            ("short_answer", "举例说明登录身份与操作权限的区别。", None, "登录证明身份，权限决定该身份可执行的操作。", 20),
        ]
        question_ids = []
        for kind, content, choices, answer, score in paper:
            question = Question(question_type=QuestionType(kind), content=content, options=choices, correct_answer=answer, score=score, is_objective=kind != "short_answer", created_by=str(teacher.id))
            db.add(question)
            db.flush()
            question_ids.append(str(question.id))
        exam = write_exam(db, teacher, ExamCreate(title="计算机网络入门结课考核", course_id=str(course.id), question_ids=question_ids, start_time=current-timedelta(minutes=1), end_time=current+timedelta(days=30), duration_minutes=30, max_attempts=3, pass_score=60, grading_notes="客观题自动判分；非空简答按要点人工批改，留空自动0分。"))
        course.certificate_exam_id = str(exam.id)
        course.status = CourseStatus.published
        course.reviewed_by, course.reviewed_at = str(admin.id), current
        for key in ("student", "student2"):
            db.add(CourseAssignment(course_id=course.id, assignment_type=AssignmentType.user, target_id=str(users[key].id), assigned_by=str(teacher.id)))
        db.add(DiscussionTopic(course_id=course.id, user_id=str(teacher.id), title="欢迎加入：你想了解哪些网络知识？", body="请在本主题下用文字回复；需要单独沟通时，可使用本课程的师生私信。"))
        db.flush()
        state = {"created_at": current.isoformat(), "open_until": (current+timedelta(days=30)).isoformat(), "accounts": accounts, "course_id": str(course.id), "homework_id": str(homework.id), "exam_id": str(exam.id)}
        STATE.parent.mkdir(exist_ok=True)
        # Save the credentials before committing; a failed commit removes only this new manifest.
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        try:
            db.commit()
        except Exception:
            STATE.unlink()
            raise
        print("Created: 1 administrator, 1 approved teacher, 2 students, 2 chapters, 1 homework, 1 five-question exam, discussion and certificate configuration.")
        print("Login details: .runtime/demo.json (local only; never include in a shared report).")


if __name__ == "__main__":
    main()
