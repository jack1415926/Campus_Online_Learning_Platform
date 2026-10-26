"""Course ownership, membership and file access shared by campus endpoints."""

from fastapi import HTTPException
from sqlalchemy import select

from app.models.course import Course, CourseStatus, Chapter
from app.models.learning import CourseAssignment, AssignmentType
from app.models.media import MediaAsset
from app.models.role import Role, UserRole


def roles_for(db, user):
    if not hasattr(user, "_campus_roles"):
        user._campus_roles = set(db.execute(
            select(Role.code).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
        ).scalars()) & {"student", "teacher", "admin"}
    return user._campus_roles


def require_admin(db, user):
    if "admin" not in roles_for(db, user):
        raise HTTPException(403, "仅管理员可执行此操作")


def enrolled_ids(db, user):
    if not hasattr(user, "_enrolled_ids"):
        user._enrolled_ids = set(db.execute(select(CourseAssignment.course_id).where(
            CourseAssignment.assignment_type == AssignmentType.user, CourseAssignment.target_id == str(user.id)
        )).scalars())
    return user._enrolled_ids


def can_manage(db, user, course):
    roles = roles_for(db, user)
    return "admin" in roles or ("teacher" in roles and str(course.created_by) == str(user.id))


def get_course(db, user, course_id, *, manage=False, edit=False, learn=False):
    course = db.scalar(select(Course).where(Course.id == course_id).with_for_update().execution_options(populate_existing=True)) if edit else db.get(Course, course_id)
    if course is None:
        raise HTTPException(404, "课程不存在")
    manager = can_manage(db, user, course)
    if manage and not manager:
        raise HTTPException(403, "只能管理本人课程")
    if edit and course.status != CourseStatus.draft:
        raise HTTPException(409, "仅草稿课程可编辑；已发布教学内容已冻结")
    if not manager:
        if course.status == CourseStatus.archived:
            if str(course.id) not in enrolled_ids(db, user):
                raise HTTPException(403, "课程已归档")
        elif course.status != CourseStatus.published:
            raise HTTPException(403, "课程尚未发布")
    if learn and not manager and ("student" not in roles_for(db, user) or str(course.id) not in enrolled_ids(db, user)):
        raise HTTPException(403, "请先加入课程")
    return course


def require_asset_owner(db, user, asset):
    if "admin" not in roles_for(db, user) and (
        "teacher" not in roles_for(db, user) or str(asset.uploaded_by) != str(user.id)
    ):
        raise HTTPException(403, "只能管理本人上传的资料")


def readable_asset(db, user, asset):
    if "admin" in roles_for(db, user):
        return
    if "teacher" in roles_for(db, user) and str(asset.uploaded_by) == str(user.id):
        return
    courses = db.execute(select(Course).join(Chapter, Chapter.course_id == Course.id).where(
        Chapter.content_ref_id == str(asset.id), Course.status.in_([CourseStatus.published, CourseStatus.archived])
    )).scalars().all()
    memberships = enrolled_ids(db, user)
    if not any(can_manage(db, user, c) or ("student" in roles_for(db, user) and str(c.id) in memberships) for c in courses):
        covers = db.scalar(select(Course.id).where(Course.cover_image_url == asset.file_url, Course.status == CourseStatus.published).limit(1))
        if asset.media_type.value == "image" and covers and roles_for(db, user):
            return
        raise HTTPException(403, "无权查看此课程资料")
