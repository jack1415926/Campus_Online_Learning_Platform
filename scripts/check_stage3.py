"""Real HTTP/MySQL stage-3 regression. Creates uniquely named local QA data."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import sys
import uuid
from zipfile import ZipFile

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:20081"
checks = []
request_count = 0
accounts = {}
prefix = "p3_" + uuid.uuid4().hex[:8]


def call(client, method, path, status=200, **kwargs):
    global request_count
    response = client.request(method, path, **kwargs)
    request_count += 1
    if response.status_code != status:
        raise AssertionError(f"{method} {path.split('?')[0]}: expected {status}, got {response.status_code}")
    return response


def client_for(account):
    client = httpx.Client(base_url=BASE, timeout=20, trust_env=False)
    response = call(client, "POST", "/api/v1/auth/login", json={k: account[k] for k in ("username", "password")}).json()
    client.headers["Authorization"] = "Bearer " + response["access_token"]
    account["refresh_token"] = response["refresh_token"]
    return client


def passed(name):
    checks.append({"name": name, "status": "PASS"})


def main():
    # Explicit guard before creating users or courses.
    os.chdir(ROOT / "backend")
    sys.path.insert(0, str(ROOT / "backend"))
    from app.config import settings
    from sqlalchemy import select, func
    from sqlalchemy.engine import make_url
    from app.database import SessionLocal
    from app.models.learning import CourseAssignment
    from app.models.user import User
    from app.models.course import Course
    url = make_url(settings.database_url)
    assert (url.host, url.port, url.database, url.username) == ("127.0.0.1", 3309, "campus_learning", "campus_app")

    admin = client_for(json.loads((ROOT / ".runtime/admin.json").read_text(encoding="utf-8")))
    anonymous = httpx.Client(base_url=BASE, timeout=20, trust_env=False)
    for label, role in (("student", "student"), ("student2", "student"), ("teacher", "teacher"), ("teacher2", "teacher")):
        account = {"username": prefix + "_" + label, "password": secrets.token_urlsafe(15), "role": role, "full_name": "阶段三_" + label}
        account["email"] = account["username"] + "@example.com"
        call(anonymous, "POST", "/api/v1/auth/register", status=201, json=account)
        accounts[label] = account
    student, student2, teacher, teacher2 = [client_for(accounts[k]) for k in ("student", "student2", "teacher", "teacher2")]
    for label, client in (("student", student), ("student2", student2), ("teacher", teacher), ("teacher2", teacher2)):
        accounts[label]["id"] = call(client, "GET", "/api/v1/auth/me").json()["id"]
    registration = {k: accounts["student"][k] for k in ("username", "email", "password", "full_name", "role")}
    call(anonymous, "POST", "/api/v1/auth/register", status=422, json={**registration, "role": "admin"})
    call(anonymous, "POST", "/api/v1/auth/register", status=409, json={k: accounts["student"][k] for k in ("username", "email", "password", "full_name", "role")})
    call(student, "POST", "/api/v1/users/"+accounts["student"]["id"]+"/roles", status=403, json={"role_code":"admin"})
    call(student, "PUT", "/api/v1/users/me/profile", status=422, json={"full_name":"学生", "email":accounts["student"]["email"], "custom_fields":{"role":"admin"}})
    call(teacher, "POST", "/api/v1/courses", status=403, json={"title":"未审核教师建课"})
    call(teacher, "POST", "/api/v1/exams", status=403, json={"title":"未审核教师建考核"})
    passed("注册、重复账号、公开注册不得提权、待审教师不得建课或考核")

    profile = {"full_name": "校园学生资料更新", "email": prefix + "_updated@example.com"}
    call(student, "PUT", "/api/v1/users/me/profile", status=422, json={**profile, "email": "invalid"})
    call(student, "PUT", "/api/v1/users/me/profile", status=409, json={**profile, "email": accounts["student2"]["email"]})
    call(student, "PUT", "/api/v1/users/me/profile", json=profile)
    assert all(call(student, "GET", "/api/v1/users/me/profile").json()[k] == v for k, v in profile.items())
    with SessionLocal() as db:
        persisted = db.get(User, accounts["student"]["id"])
        assert (persisted.full_name, persisted.email) == (profile["full_name"], profile["email"])
        assert persisted.password_hash != accounts["student"]["password"]
    from app.core.security import create_access_token, decode_token
    claims = decode_token(student.headers["Authorization"].removeprefix("Bearer "))
    expired = create_access_token(claims["sub"], session_id=claims["sid"], session_token=claims["sess"],
        extra_claims={"exp": datetime.now(timezone.utc) - timedelta(minutes=1)})
    call(anonymous, "GET", "/api/v1/auth/me", status=401, headers={"Authorization": "Bearer " + expired})
    passed("个人资料格式与唯一性校验、更新持久化、密码摘要、过期凭据拒绝")

    t2 = accounts["teacher2"]["id"]
    call(admin, "POST", f"/api/v1/users/{t2}/teacher-review", status=422, json={"decision":"reject"})
    call(admin, "POST", f"/api/v1/users/{t2}/teacher-review", json={"decision":"reject", "reason":"请补充教师信息"})
    assert call(teacher2, "GET", "/api/v1/auth/me").json()["teacher_review_reason"] == "请补充教师信息"
    for label in ("teacher", "teacher2"):
        call(admin, "POST", f"/api/v1/users/{accounts[label]['id']}/teacher-review", json={"decision":"approve"})
    assert call(teacher, "GET", "/api/v1/auth/me").json()["roles"] == ["teacher"]
    filtered = call(admin, "GET", "/api/v1/users", params={"keyword": prefix, "review_status": "approved"}).json()["items"]
    assert {u["id"] for u in filtered} == {accounts[k]["id"] for k in ("teacher", "teacher2")}
    passed("教师审核驳回原因、重新通过、已有登录立即取得教师权限")

    course = call(teacher, "POST", "/api/v1/courses", status=201, json={"title":prefix+"_校园课程", "description":"阶段三课程权限验收"}).json()
    cid = course["id"]
    call(teacher, "POST", f"/api/v1/courses/{cid}/publish", status=400, json={"action":"submit_review"})
    chapter = call(teacher, "POST", f"/api/v1/courses/{cid}/chapters", status=201, json={"title":"第一章", "content_type":"text", "text_content":"仅加入后可见的课程内容"}).json()
    call(teacher2, "PUT", f"/api/v1/courses/{cid}", status=403, json={"title":"越权修改"})
    call(teacher2, "PUT", f"/api/v1/courses/{cid}/chapters/{chapter['id']}", status=403, json={"title":"越权修改"})
    call(teacher2, "DELETE", f"/api/v1/courses/{cid}", status=403)
    call(student, "POST", "/api/v1/courses", status=403, json={"title":"学生建课"})
    passed("教师本人草稿管理、空课不能审核、其他教师和学生不能修改")

    pdf = b"%PDF-1.4\n% Campus stage 3 attachment access check\n%%EOF\n"
    asset = call(teacher, "POST", "/api/v1/media/upload", status=201, files={"file":("stage3.pdf",pdf,"application/pdf")}).json()
    aid = asset["id"]
    call(teacher2, "GET", f"/api/v1/media/{aid}/url", status=403)
    call(teacher2, "PUT", f"/api/v1/media/{aid}", status=403, json={"name":"非法改名"})
    call(teacher2, "POST", "/api/v1/courses", status=403, json={"title":"盗用资料", "chapters":[{"title":"盗用", "content_type":"document", "content_ref_id":aid}]})
    call(student, "GET", "/api/v1/media", status=403)
    call(teacher, "POST", "/api/v1/media/upload", status=422, files={"file":("fake.pdf",b"<script>bad</script>","application/pdf")})
    call(teacher, "POST", f"/api/v1/courses/{cid}/chapters", status=201, json={"title":"课程资料", "content_type":"document", "content_ref_id":aid,"sort_order":1})
    call(teacher, "POST", f"/api/v1/courses/{cid}/chapters", status=422, json={"title":"错误视频资料", "content_type":"video", "content_ref_id":aid})
    call(teacher, "PUT", f"/api/v1/courses/{cid}/chapters/{chapter['id']}", status=422, json={"content_ref_id":aid})
    call(teacher, "DELETE", f"/api/v1/media/{aid}", status=409)
    passed("资料仅本人管理、不可盗用附件、扩展名校验、引用资料不可删除")

    document = BytesIO()
    with ZipFile(document, "w") as archive_file:
        archive_file.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        archive_file.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
    docx = document.getvalue()
    word = call(teacher, "POST", "/api/v1/media/upload", status=201, files={"file":("stage3.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}).json()
    word_chapter = call(teacher, "POST", f"/api/v1/courses/{cid}/chapters", status=201,
        json={"title":"Word课程资料", "content_type":"document", "content_ref_id":word["id"], "sort_order":2}).json()
    call(teacher, "PUT", f"/api/v1/courses/{cid}/chapters/{word_chapter['id']}", status=422, json={"content_type":"video"})

    call(teacher, "POST", f"/api/v1/courses/{cid}/publish", json={"action":"submit_review"})
    call(teacher, "PUT", f"/api/v1/courses/{cid}/chapters/{chapter['id']}", status=409, json={"title":"审核中修改"})
    call(student, "GET", f"/api/v1/courses/{cid}", status=403)
    call(teacher, "POST", f"/api/v1/courses/{cid}/publish", status=403, json={"action":"publish"})
    call(admin, "POST", f"/api/v1/courses/{cid}/publish", json={"action":"reject","reason":"请完善课程描述"})
    assert call(teacher, "GET", f"/api/v1/courses/{cid}").json()["review_reason"] == "请完善课程描述"
    call(teacher, "PUT", f"/api/v1/courses/{cid}", json={"description":"已完善的校园课程说明"})
    call(teacher, "POST", f"/api/v1/courses/{cid}/publish", json={"action":"submit_review"})
    call(admin, "POST", f"/api/v1/courses/{cid}/publish", json={"action":"publish"})
    passed("课程提交、教师不能自发布、管理员驳回与重新审核发布")
    own_courses = call(teacher2, "GET", "/api/v1/courses", params={"managed": "true", "keyword": prefix}).json()["items"]
    assert not own_courses
    assert not call(teacher2, "GET", f"/api/v1/courses/{cid}").json()["can_manage"]

    preview = call(student,"GET",f"/api/v1/courses/{cid}").json()
    assert not preview["can_learn"] and all(ch["text_content"] is None and ch["content_ref_id"] is None for ch in preview["chapters"])
    assert cid in [c["id"] for c in call(student,"GET","/api/v1/courses",params={"keyword":prefix}).json()["items"]]
    call(student,"GET",f"/api/v1/media/{aid}/url",status=403)
    call(anonymous,"GET",asset["file_url"],status=404)
    passed("学生可检索公开课程简介、大纲，未加入不能读正文或资料，旧静态地址关闭")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: call(student,"POST",f"/api/v1/courses/{cid}/join"),range(4)))
    full = call(student,"GET",f"/api/v1/courses/{cid}").json()
    assert full["can_learn"] and full["chapters"][0]["text_content"] == "仅加入后可见的课程内容"
    assert any(a["course_title"] == course["title"] for a in call(student,"GET","/api/v1/learning/my-assignments").json())
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(CourseAssignment).where(CourseAssignment.course_id==cid,CourseAssignment.target_id==accounts["student"]["id"])) == 1
        persisted=db.get(User,accounts["teacher"]["id"])
        assert persisted.teacher_review_status == "approved" and persisted.teacher_reviewed_by
        assert db.get(Course,cid).status.value == "published"
    passed("并发重复加入唯一、新会话读取审核和发布状态、我的课程显示名称")

    ticket=call(student,"GET",f"/api/v1/media/{aid}/url").json()["url"]
    assert call(anonymous,"GET",ticket).content == pdf
    assert call(anonymous,"GET",ticket,status=206,headers={"Range":"bytes=0-4"}).content == b"%PDF-"
    call(student2,"GET",f"/api/v1/media/{aid}/url",status=403)
    call(anonymous,"GET",f"/api/v1/media/{aid}/content",status=401)
    other=call(teacher2,"POST","/api/v1/media/upload",status=201,files={"file":("other.pdf",pdf,"application/pdf")}).json()
    call(anonymous,"GET",ticket.replace(aid,other["id"]),status=403)
    call(anonymous,"GET","/api/v1/auth/me",status=401,headers={"Authorization":"Bearer "+ticket.split("ticket=")[1]})
    passed("课程附件签名链接、Range读取、不可换资源ID或充当登录令牌")
    word_ticket = call(student, "GET", f"/api/v1/media/{word['id']}/url").json()["url"]
    assert call(anonymous, "GET", word_ticket).content == docx
    call(student2, "GET", f"/api/v1/media/{word['id']}/url", status=403)
    passed("DOCX上传关联与成员下载，章节和资料类型一致")

    call(teacher,"PUT",f"/api/v1/courses/{cid}",status=409,json={"title":"修改已发布内容"})
    call(teacher,"POST",f"/api/v1/courses/{cid}/chapters",status=409,json={"title":"新章","content_type":"text","text_content":"冻结"})
    call(admin,"POST",f"/api/v1/courses/{cid}/publish",status=409,json={"action":"unpublish"})
    call(student,"PUT",f"/api/v1/courses/{cid}",status=403,json={"title":"越权修改"})
    passed("发布内容冻结，已有成员不能退回草稿，学生不能编辑课程")

    archive=call(teacher,"POST","/api/v1/courses",status=201,json={"title":prefix+"_归档检查","chapters":[{"title":"历史章节","content_type":"text","text_content":"归档历史"}]}).json()["id"]
    for action,client in (("submit_review",teacher),("publish",admin)):
        call(client,"POST",f"/api/v1/courses/{archive}/publish",json={"action":action})
    call(student,"POST",f"/api/v1/courses/{archive}/join")
    call(admin,"POST",f"/api/v1/courses/{archive}/publish",json={"action":"archive"})
    assert call(student,"GET",f"/api/v1/courses/{archive}").json()["chapters"][0]["text_content"]=="归档历史"
    call(student2,"GET",f"/api/v1/courses/{archive}",status=403)
    call(student2,"POST",f"/api/v1/courses/{archive}/join",status=409)
    call(student,"POST","/api/v1/learning/progress",status=403,json={"course_id":archive,"progress_percent":100})
    passed("归档保留成员历史，停止新加入和学习写入")

    s2=accounts["student2"]["id"]
    call(admin,"PUT",f"/api/v1/users/{s2}/status",json={"status":"inactive"})
    call(student2,"GET","/api/v1/auth/me",status=401)
    call(anonymous,"POST","/api/v1/auth/refresh",status=401,json={"refresh_token":accounts["student2"]["refresh_token"]})
    call(anonymous,"POST","/api/v1/auth/login",status=403,json={k:accounts["student2"][k] for k in ("username","password")})
    call(admin,"PUT",f"/api/v1/users/{s2}/status",json={"status":"active"})
    call(anonymous,"POST","/api/v1/auth/refresh",status=401,json={"refresh_token":accounts["student2"]["refresh_token"]})
    student2=client_for(accounts["student2"])
    passed("停用即时失效、启用后旧会话不得复活")

    call(student2,"POST","/api/v1/users/me/password",status=400,json={"old_password":"wrong","new_password":"ReplacementPassword"})
    replacement=secrets.token_urlsafe(18)
    old_refresh=accounts["student2"]["refresh_token"]
    call(student2,"POST","/api/v1/users/me/password",status=204,json={"old_password":accounts["student2"]["password"],"new_password":replacement})
    call(student2,"GET","/api/v1/auth/me",status=401)
    call(anonymous,"POST","/api/v1/auth/refresh",status=401,json={"refresh_token":old_refresh})
    accounts["student2"]["password"]=replacement
    student2=client_for(accounts["student2"])
    call(student2,"POST","/api/v1/auth/logout",status=204)
    call(anonymous,"POST","/api/v1/auth/refresh",status=401,json={"refresh_token":accounts["student2"]["refresh_token"]})
    call(student2,"GET","/api/v1/auth/me",status=401)
    passed("修改密码与退出撤销会话，刷新令牌不能绕过撤销")

    # Separate random QA administrator for browser tests; never expose real admin credentials.
    accounts["admin"]={"username":prefix+"_admin", "password":secrets.token_urlsafe(18),"full_name":"阶段三测试管理员","email":prefix+"_admin@example.com","role_code":"admin"}
    call(admin,"POST","/api/v1/users",status=201,json=accounts["admin"])
    with SessionLocal() as db:
        from sqlalchemy import text
        database_version = db.scalar(text("SELECT VERSION()"))
        migration = db.scalar(text("SELECT version_num FROM alembic_version"))
    summary={"tested_at":datetime.now(timezone.utc).isoformat(),"python":sys.version.split()[0],"mysql":database_version,"migration":migration,"prefix":prefix,"course_id":cid,"course_title":course["title"],"asset_id":aid,"word_asset_id":word["id"],"http_requests":request_count,"checks":checks,"scope":"Stage 3 only; no full learning/exam acceptance"}
    private_accounts={k:{a:b for a,b in v.items() if a in ("username","password","id")} for k,v in accounts.items()}
    (ROOT/".runtime/stage3-accounts.json").write_text(json.dumps(private_accounts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/".runtime/stage3-results.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"groups_passed":len(checks),"http_requests":request_count,"course_id":cid,"results":".runtime/stage3-results.json"},ensure_ascii=False))


if __name__=="__main__":
    main()
