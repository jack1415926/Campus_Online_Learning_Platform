"""Focused real HTTP/MySQL checks for course discussion and private messages."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import uuid

import httpx

ROOT=Path(__file__).resolve().parents[1]
requests=0


def call(c,method,path,status=200,**kw):
    global requests
    r=c.request(method,path,**kw);requests+=1
    assert r.status_code==status,f'{method} {path}: {r.status_code}, expected {status}: {r.text[:160]}'
    return r


def main():
    os.chdir(ROOT/'backend');sys.path.insert(0,str(ROOT/'backend'))
    from app.config import settings
    from app.database import SessionLocal
    from app.models.communication import DiscussionTopic,DiscussionReply,PrivateMessage
    from app.models.notification import Notification
    from app.models.user import User
    from sqlalchemy import select,func,text
    from sqlalchemy.engine import make_url
    url=make_url(settings.database_url)
    assert (url.host,url.port,url.database,url.username)==('127.0.0.1',3309,'campus_learning','campus_app')
    accounts=json.loads((ROOT/'.runtime/stage3-accounts.json').read_text(encoding='utf-8'))
    clients={}
    for role in ('teacher','teacher2','student','student2','admin'):
        c=httpx.Client(base_url='http://127.0.0.1:20081',trust_env=False,timeout=20);a=accounts[role]
        token=call(c,'POST','/api/v1/auth/login',json={k:a[k] for k in ('username','password')}).json()['access_token'];c.headers['Authorization']='Bearer '+token;clients[role]=c
    t,other,s,s2,admin=[clients[k] for k in ('teacher','teacher2','student','student2','admin')]
    checks=[];prefix='p6_'+uuid.uuid4().hex[:8]
    cid=call(t,'POST','/api/v1/courses',201,json={'title':prefix+'_课程交流','chapters':[{'title':'交流说明','content_type':'text','text_content':'课程讨论和师生私信'}]}).json()['id']
    root=f'/api/v1/courses/{cid}'
    call(t,'POST',root+'/discussions',409,json={'title':'草稿','body':'不能发布'})
    for action,c in (('submit_review',t),('publish',admin)):call(c,'POST',root+'/publish',json={'action':action})
    call(s,'GET',root+'/discussions',403);call(s,'GET',root+'/private-contacts',403)
    for student in (s,s2):call(student,'POST',root+'/join')
    call(other,'GET',root+'/discussions',403)
    call(admin,'POST',root+'/discussions',403,json={'title':'管理员','body':'只做管理，不代师生发帖'})
    call(s,'POST',root+'/discussions',422,json={'title':' ','body':'内容'})
    call(s,'POST',root+'/discussions',422,json={'title':'标题','body':' '})
    topic=call(s,'POST',root+'/discussions',201,json={'title':prefix+'_待删除主题','body':'<script>window.stage6Injected=true</script>'}).json()
    tid=topic['id']
    assert datetime.fromisoformat(topic['created_at']).utcoffset()==timedelta(0)
    reply=call(s2,'POST',root+f'/discussions/{tid}/replies',201,json={'body':'第二名学生回复'}).json()
    with SessionLocal() as db:
        n=db.scalar(select(Notification).where(Notification.event_key==f"reply:{reply['id']}"));assert n and not n.is_read and n.user_id==accounts['student']['id']
    detail=call(s,'GET',root+f'/discussions/{tid}').json();assert detail['topic']['body']==topic['body'] and detail['items'][0]['body']=='第二名学生回复'
    call(s,'DELETE',root+f"/discussions/{tid}/replies/{reply['id']}",403)
    call(s2,'DELETE',root+f'/discussions/{tid}',403)
    call(s2,'DELETE',root+f"/discussions/{tid}/replies/{reply['id']}",204)
    assert not call(s,'GET',root+f'/discussions/{tid}').json()['items']
    own=call(s,'POST',root+f'/discussions/{tid}/replies',201,json={'body':'本人补充'}).json()
    with SessionLocal() as db:
        assert db.scalar(select(Notification).where(Notification.event_key==f"reply:{reply['id']}")).is_read
        assert not db.scalar(select(Notification.id).where(Notification.event_key==f"reply:{own['id']}"))
        assert db.get(DiscussionReply,reply['id']).deleted_by==accounts['student2']['id']
    call(s,'DELETE',root+f'/discussions/{tid}',204)
    call(s,'GET',root+f'/discussions/{tid}',404)
    call(t,'POST',root+f'/discussions/{tid}/replies',404,json={'body':'删除后回复'})
    assert not call(s,'GET',root+'/discussions').json()['items']
    checks.append('成员/归属/发布状态、纯文本保存、作者删除、删除主题隐藏回复、回复通知与已读')

    ui_topic=call(s,'POST',root+'/discussions',201,json={'title':prefix+'_页面讨论','body':'<script>window.stage6Injected=true</script> 这是纯文本讨论。'}).json()['id']
    tr=call(t,'POST',root+f'/discussions/{ui_topic}/replies',201,json={'body':'任课教师回复'}).json()
    call(other,'DELETE',root+f"/discussions/{ui_topic}/replies/{tr['id']}",403)
    call(t,'DELETE',root+f"/discussions/{ui_topic}/replies/{tr['id']}",204)
    admin_topic=call(s2,'POST',root+'/discussions',201,json={'title':'管理员清理检查','body':'仅测试本地软删除'}).json()['id']
    call(admin,'DELETE',root+f'/discussions/{admin_topic}',204)
    with SessionLocal() as db:
        admin_id=db.scalar(select(User.id).where(User.username==accounts['admin']['username']))
        assert db.get(DiscussionTopic,admin_topic).deleted_by==str(admin_id)
    assert call(t,'GET',root+'/discussions',params={'page':1,'page_size':1}).json()['meta']['total']==1
    checks.append('任课教师和管理员按范围管理讨论、其他教师被拦截、时间分页')

    teacher_id=accounts['teacher']['id'];student_id=accounts['student']['id']
    assert [x['id'] for x in call(s,'GET',root+'/private-contacts').json()['items']]==[teacher_id]
    assert {x['id'] for x in call(t,'GET',root+'/private-contacts').json()['items']}=={student_id,accounts['student2']['id']}
    call(admin,'GET',root+'/private-contacts',403)
    call(s,'POST',root+'/messages',403,json={'recipient_id':accounts['student2']['id'],'body':'学生不能互发'})
    call(s,'POST',root+'/messages',403,json={'recipient_id':accounts['teacher2']['id'],'body':'不能联系其他教师'})
    call(t,'POST',root+'/messages',403,json={'recipient_id':accounts['teacher2']['id'],'body':'不能联系其他教师'})
    call(s,'POST',root+'/messages',422,json={'recipient_id':teacher_id,'body':' ','sender_id':student_id})
    secret='<b>私信正文不能出现在通知中</b>'
    message=call(s,'POST',root+'/messages',201,json={'recipient_id':teacher_id,'body':secret}).json();mid=message['id'];assert message['read_at'] is None
    assert call(s,'GET',root+f'/messages/{mid}').json()['read_at'] is None
    for denied in (s2,other,admin):call(denied,'GET',root+f'/messages/{mid}',403)
    call(s2,'GET',root+'/messages',403,params={'peer_id':student_id})
    call(admin,'GET',root+'/messages',403,params={'peer_id':student_id})
    with SessionLocal() as db:
        notice=db.scalar(select(Notification).where(Notification.event_key==f'message:{mid}'));assert notice.user_id==teacher_id and secret not in notice.body and not notice.is_read
    assert next(p['unread'] for p in call(t,'GET',root+'/private-contacts').json()['items'] if p['id']==student_id)==1
    conversation=call(t,'GET',root+'/messages',params={'peer_id':student_id}).json();assert conversation['items'][0]['body']==secret and conversation['items'][0]['read_at']
    assert call(s,'GET',root+f'/messages/{mid}').json()['read_at']
    response=call(t,'POST',root+'/messages',201,json={'recipient_id':student_id,'body':'教师私信回复'}).json()
    pair=call(s,'GET',root+'/messages',params={'peer_id':teacher_id}).json()['items'];assert [m['id'] for m in pair]==[mid,response['id']]
    with SessionLocal() as db:
        assert db.get(PrivateMessage,mid).read_at
        assert db.scalar(select(Notification).where(Notification.event_key==f'message:{mid}')).is_read
        assert db.scalar(select(Notification).where(Notification.event_key==f"message:{response['id']}")).is_read
    checks.append('师生双向私信、发送者/接收者限定、管理员也不得读正文、通知不含私信正文、已读持久化')

    older=call(s,'POST',root+'/messages',201,json={'recipient_id':teacher_id,'body':'分页未读一'}).json()['id']
    newer=call(s,'POST',root+'/messages',201,json={'recipient_id':teacher_id,'body':'分页未读二'}).json()['id']
    visible=call(t,'GET',root+'/messages',params={'peer_id':student_id,'page_size':1}).json();assert visible['items'][0]['id']==newer and visible['meta']['total']==4
    with SessionLocal() as db:
        assert db.get(PrivateMessage,older).read_at is None and db.get(PrivateMessage,newer).read_at
        assert not db.scalar(select(Notification).where(Notification.event_key==f'message:{older}')).is_read
    checks.append('私信分页按发送时间排序，只标记实际返回的收件及其通知已读')

    archive=call(t,'POST','/api/v1/courses',201,json={'title':prefix+'_归档检查','chapters':[{'title':'说明','content_type':'text','text_content':'归档历史'}]}).json()['id'];ar=f'/api/v1/courses/{archive}'
    for action,c in (('submit_review',t),('publish',admin)):call(c,'POST',ar+'/publish',json={'action':action})
    at=call(t,'POST',ar+'/discussions',201,json={'title':'教师主题','body':'无成员时也保留讨论历史'}).json()['id']
    call(admin,'POST',ar+'/publish',409,json={'action':'unpublish'})
    call(s,'POST',ar+'/join')
    am=call(s,'POST',ar+'/messages',201,json={'recipient_id':teacher_id,'body':'归档前私信'}).json()['id']
    call(admin,'GET',ar+f'/discussions/{ui_topic}',404)
    call(t,'GET',ar+f'/messages/{mid}',404)
    call(admin,'POST',ar+'/publish',json={'action':'archive'})
    call(s,'GET',ar+'/discussions');call(s,'GET',ar+f'/messages/{am}')
    call(s,'POST',ar+'/discussions',409,json={'title':'归档','body':'新主题'})
    call(s,'POST',ar+f'/discussions/{at}/replies',409,json={'body':'新回复'})
    call(s,'POST',ar+'/messages',409,json={'recipient_id':teacher_id,'body':'新私信'})
    checks.append('课程ID绑定、讨论/私信历史保护、归档可读而禁止新内容')
    with SessionLocal() as db:
        mysql=db.scalar(text('SELECT VERSION()'));migration=db.scalar(text('SELECT version_num FROM alembic_version'))
    summary={'tested_at':datetime.now().astimezone().isoformat(),'course_id':cid,'topic_id':ui_topic,'http_requests':requests,'checks':checks,'mysql':mysql,'migration':migration,'scope':'Stage 6 only; no realtime/chat extensions'}
    (ROOT/'.runtime/stage6-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'groups_passed':len(checks),'http_requests':requests,'results':'.runtime/stage6-results.json'}))
    for c in clients.values():c.close()


if __name__=='__main__':main()
