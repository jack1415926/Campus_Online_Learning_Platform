"""Course discussion and participant-only private messages; no realtime service."""
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import campus_access as access
from app.database import get_db
from app.models.communication import DiscussionTopic, DiscussionReply, PrivateMessage, utc_now
from app.models.course import Course, CourseStatus
from app.models.learning import CourseAssignment, AssignmentType
from app.models.notification import Notification, NotificationType
from app.models.role import Role, UserRole
from app.models.user import User, UserStatus
from app.schemas.communication import MessageWrite, TopicWrite, PrivateMessageWrite
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/courses/{course_id}", tags=["communication"])


def _course(db, user, course_id, *, lock=False, post=False):
    if lock:
        db.scalar(select(Course).where(Course.id == course_id).with_for_update().execution_options(populate_existing=True))
    course = access.get_course(db, user, course_id, learn=True)
    if post:
        roles = access.roles_for(db, user)
        if not (("student" in roles and course_id in access.enrolled_ids(db, user)) or ("teacher" in roles and str(course.created_by) == str(user.id))):
            raise HTTPException(403, "仅课程学生和任课教师可发布内容")
        if course.status != CourseStatus.published:
            raise HTTPException(409, "仅已发布课程可发布新内容")
    return course


def _topic(db, course_id, topic_id):
    topic = db.scalar(select(DiscussionTopic).where(DiscussionTopic.id == topic_id, DiscussionTopic.course_id == course_id, DiscussionTopic.deleted_at.is_(None)).with_for_update().execution_options(populate_existing=True))
    if topic is None:
        raise HTTPException(404, "主题不存在或已删除")
    return topic


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value else None


def _post_response(post, full_name, user, db, course):
    result = {"id": str(post.id), "user_id": str(post.user_id), "full_name": full_name, "body": post.body, "created_at": _utc(post.created_at), "can_delete": str(post.user_id) == str(user.id) or access.can_manage(db, user, course)}
    if isinstance(post, DiscussionTopic):
        result["title"] = post.title
    return result


@router.get("/discussions")
def list_topics(course_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db, user, course_id)
    stmt = select(DiscussionTopic, User.full_name).join(User, User.id == DiscussionTopic.user_id).where(DiscussionTopic.course_id == course_id, DiscussionTopic.deleted_at.is_(None))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(DiscussionTopic.created_at.desc(),DiscussionTopic.id).offset((page-1)*page_size).limit(page_size))
    return {"items": [_post_response(p,n,user,db,course) for p,n in rows], "meta": {"total": total, "page": page, "page_size": page_size}}


@router.post("/discussions", status_code=201)
def create_topic(course_id: str, body: TopicWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db, user, course_id, lock=True, post=True)
    topic = DiscussionTopic(course_id=course_id, user_id=str(user.id), **body.model_dump())
    db.add(topic);db.commit()
    return _post_response(topic,user.full_name,user,db,course)


@router.get("/discussions/{topic_id}")
def get_topic(course_id: str, topic_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db,user,course_id)
    topic = _topic(db,course_id,topic_id)
    stmt = select(DiscussionReply,User.full_name).join(User,User.id==DiscussionReply.user_id).where(DiscussionReply.topic_id==topic_id,DiscussionReply.deleted_at.is_(None))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(db.execute(stmt.order_by(DiscussionReply.created_at,DiscussionReply.id).offset((page-1)*page_size).limit(page_size)))
    keys = [f"reply:{p.id}" for p,_ in rows]
    for notification in db.scalars(select(Notification).where(Notification.user_id==user.id,Notification.event_key.in_(keys))):
        notification.is_read=True
    db.commit()
    return {"topic":_post_response(topic,db.get(User,topic.user_id).full_name,user,db,course),"items":[_post_response(p,n,user,db,course) for p,n in rows],"meta":{"total":total,"page":page,"page_size":page_size}}


@router.post("/discussions/{topic_id}/replies", status_code=201)
def reply_topic(course_id: str, topic_id: str, body: MessageWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db,user,course_id,lock=True,post=True)
    topic = _topic(db,course_id,topic_id)
    reply = DiscussionReply(topic_id=topic_id,user_id=str(user.id),body=body.body)
    db.add(reply);db.flush()
    if str(topic.user_id) != str(user.id):
        notification = NotificationService.notify_user(db,topic.user_id,NotificationType.system,"讨论主题收到回复","你的课程讨论主题收到一条回复，请到课程内查看。",extra_data={"course_id":course_id,"topic_id":topic_id})
        notification.event_key = f"reply:{reply.id}"
    db.commit()
    return _post_response(reply,user.full_name,user,db,course)


@router.delete("/discussions/{topic_id}", status_code=204)
def delete_topic(course_id: str, topic_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db,user,course_id,lock=True)
    topic = _topic(db,course_id,topic_id)
    if str(topic.user_id) != str(user.id) and not access.can_manage(db,user,course):
        raise HTTPException(403,"只能删除本人或本人管理课程的内容")
    topic.deleted_at,topic.deleted_by = utc_now(),str(user.id)
    db.commit()


@router.delete("/discussions/{topic_id}/replies/{reply_id}", status_code=204)
def delete_reply(course_id: str, topic_id: str, reply_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _course(db,user,course_id,lock=True)
    _topic(db,course_id,topic_id)
    reply = db.scalar(select(DiscussionReply).where(DiscussionReply.id==reply_id,DiscussionReply.topic_id==topic_id,DiscussionReply.deleted_at.is_(None)).with_for_update())
    if reply is None:
        raise HTTPException(404,"回复不存在或已删除")
    if str(reply.user_id) != str(user.id) and not access.can_manage(db,user,course):
        raise HTTPException(403,"只能删除本人或本人管理课程的内容")
    reply.deleted_at,reply.deleted_by = utc_now(),str(user.id)
    db.commit()


def _private_course(db,user,course_id,*,lock=False):
    roles = access.roles_for(db,user)
    if "admin" in roles or not roles & {"student","teacher"}:
        raise HTTPException(403,"私信仅对课程内的师生参与者开放")
    return _course(db,user,course_id,lock=lock)


def _between(user_id,peer_id):
    return or_((PrivateMessage.sender_id==user_id)&(PrivateMessage.recipient_id==peer_id),(PrivateMessage.sender_id==peer_id)&(PrivateMessage.recipient_id==user_id))


def _peer(db,user,course,peer_id,*,sending=False):
    peer = db.get(User,peer_id)
    if peer is None:
        raise HTTPException(404,"课程联系人不存在")
    if str(peer.id)==str(user.id):
        raise HTTPException(403,"不能向自己发送私信")
    roles = access.roles_for(db,user)
    if "teacher" in roles and str(course.created_by)==str(user.id):
        member = db.scalar(select(CourseAssignment.id).where(CourseAssignment.course_id==course.id,CourseAssignment.assignment_type==AssignmentType.user,CourseAssignment.target_id==peer_id))
        valid = member is not None and "student" in access.roles_for(db,peer)
        history = not sending and db.scalar(select(PrivateMessage.id).where(PrivateMessage.course_id==course.id,_between(str(user.id),peer_id)).limit(1))
        if not valid and not history:
            raise HTTPException(403,"只能联系本人课程的学生")
    elif "student" in roles and peer_id==str(course.created_by):
        if sending and ("teacher" not in access.roles_for(db,peer) or "admin" in access.roles_for(db,peer)):
            raise HTTPException(403,"该课程尚无可接收私信的任课教师")
    else:
        raise HTTPException(403,"只能在本课程师生之间私信")
    if sending and (course.status!=CourseStatus.published or peer.status!=UserStatus.active):
        raise HTTPException(409,"课程已归档或对方账号不可接收私信")
    if sending and "admin" in access.roles_for(db,peer):
        raise HTTPException(403,"管理员账号不参与师生私信")
    return peer


@router.get("/private-contacts")
def private_contacts(course_id: str, page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _private_course(db,user,course_id)
    if str(course.created_by)==str(user.id) and "teacher" in access.roles_for(db,user):
        stmt = select(User).join(CourseAssignment,CourseAssignment.target_id==User.id).join(UserRole,UserRole.user_id==User.id).join(Role,Role.id==UserRole.role_id).where(CourseAssignment.course_id==course_id,CourseAssignment.assignment_type==AssignmentType.user,Role.code=="student")
    else:
        stmt = select(User).where(User.id==course.created_by)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items=[]
    for peer in db.scalars(stmt.order_by(User.full_name,User.id).offset((page-1)*page_size).limit(page_size)):
        if "student" in access.roles_for(db,user) and "teacher" not in access.roles_for(db,peer):
            continue
        unread = db.scalar(select(func.count()).select_from(PrivateMessage).where(PrivateMessage.course_id==course_id,PrivateMessage.sender_id==peer.id,PrivateMessage.recipient_id==user.id,PrivateMessage.read_at.is_(None)))
        items.append({"id":str(peer.id),"full_name":peer.full_name,"active":peer.status==UserStatus.active,"unread":unread})
    return {"items":items,"meta":{"total":total,"page":page,"page_size":page_size}}


def _message_response(message):
    return {"id":str(message.id),"sender_id":str(message.sender_id),"recipient_id":str(message.recipient_id),"body":message.body,"created_at":_utc(message.created_at),"read_at":_utc(message.read_at)}


def _mark_received(db,user,messages):
    keys=[]
    for message in messages:
        if str(message.recipient_id)==str(user.id) and message.read_at is None:
            message.read_at=utc_now()
            keys.append(f"message:{message.id}")
    if keys:
        for notification in db.scalars(select(Notification).where(Notification.user_id==user.id,Notification.event_key.in_(keys))):
            notification.is_read=True
    db.commit()


@router.get("/messages")
def conversation(course_id: str, peer_id: str, page: int = Query(1,ge=1), page_size: int = Query(20,ge=1,le=100), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _private_course(db,user,course_id)
    peer = _peer(db,user,course,peer_id)
    stmt = select(PrivateMessage).where(PrivateMessage.course_id==course_id,_between(str(user.id),peer_id))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    messages = db.scalars(stmt.order_by(PrivateMessage.created_at.desc(),PrivateMessage.id).offset((page-1)*page_size).limit(page_size)).all()
    _mark_received(db,user,messages)
    return {"peer":{"id":str(peer.id),"full_name":peer.full_name},"items":[_message_response(m) for m in reversed(messages)],"meta":{"total":total,"page":page,"page_size":page_size}}


@router.post("/messages",status_code=201)
def send_message(course_id: str, body: PrivateMessageWrite, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    course = _private_course(db,user,course_id,lock=True)
    peer = _peer(db,user,course,str(body.recipient_id),sending=True)
    message = PrivateMessage(course_id=course_id,sender_id=str(user.id),recipient_id=str(peer.id),body=body.body)
    db.add(message);db.flush()
    notification = NotificationService.notify_user(db,str(peer.id),NotificationType.system,"收到课程私信","你收到一条课程师生私信，请打开会话查看。",extra_data={"course_id":course_id,"peer_id":str(user.id)})
    notification.event_key=f"message:{message.id}"
    db.commit()
    return _message_response(message)


@router.get("/messages/{message_id}")
def get_message(course_id: str, message_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _private_course(db,user,course_id)
    message = db.scalar(select(PrivateMessage).where(PrivateMessage.id==message_id,PrivateMessage.course_id==course_id))
    if message is None:
        raise HTTPException(404,"私信不存在")
    if str(user.id) not in (str(message.sender_id),str(message.recipient_id)):
        raise HTTPException(403,"只有发送者和接收者可查看私信")
    _mark_received(db,user,[message])
    return _message_response(message)
