"""Targeted real MySQL/HTTP checks for manual exams; keeps local QA fixtures."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import uuid

import httpx

ROOT=Path(__file__).resolve().parents[1]
requests=0
checks=[]


def call(client,method,path,expected=200,**kw):
    global requests
    r=client.request(method,path,**kw)
    requests+=1
    assert r.status_code==expected,f"{method} {path}: {r.status_code}, expected {expected}: {r.text[:200]}"
    return r


def main():
    os.chdir(ROOT/'backend');sys.path.insert(0,str(ROOT/'backend'))
    from sqlalchemy import select,func,text
    from sqlalchemy.engine import make_url
    from app.config import settings
    from app.database import SessionLocal
    from app.models.exam import ExamRecord,ExamStatus
    from app.models.notification import Notification
    url=make_url(settings.database_url)
    assert (url.host,url.port,url.database,url.username)==('127.0.0.1',3309,'campus_learning','campus_app')
    accounts=json.loads((ROOT/'.runtime/stage3-accounts.json').read_text(encoding='utf-8'))
    clients={}
    for role in ('teacher','teacher2','student','student2','admin'):
        c=httpx.Client(base_url='http://127.0.0.1:20081',trust_env=False,timeout=20)
        a=accounts[role];token=call(c,'POST','/api/v1/auth/login',json={k:a[k] for k in ('username','password')}).json()['access_token']
        c.headers['Authorization']='Bearer '+token;clients[role]=c
    t,other,s,s2,admin=[clients[k] for k in ('teacher','teacher2','student','student2','admin')]
    prefix='p5_'+uuid.uuid4().hex[:8]
    bank=call(t,'POST','/api/v1/exams/question-banks',201,json={'name':prefix+'_本人题库'}).json()['id']
    questions=[]
    options=[{'key':'A','text':'选项A'},{'key':'B','text':'选项B'},{'key':'C','text':'选项C'}]
    bodies=[]
    for kind,answer,score in (('single_choice','A',2),('multiple_choice',['A','C'],3),('true_false','false',1),('short_answer','简答参考一',4),('short_answer','简答参考二',5)):
        body={'question_type':kind,'content':prefix+'_'+kind+'_'+str(len(bodies)),'options':options if 'choice' in kind else None,'correct_answer':answer,'score':score,'question_bank_id':bank}
        questions.append(call(t,'POST','/api/v1/exams/questions',201,json=body).json());bodies.append(body)
    ids=[q['id'] for q in questions]
    call(s,'GET','/api/v1/exams/questions',403)
    call(other,'GET','/api/v1/exams/questions',403,params={'question_bank_id':bank})
    assert not any(q['id'] in ids for q in call(other,'GET','/api/v1/exams/questions').json()['items'])
    call(other,'PUT',f'/api/v1/exams/questions/{ids[0]}',403,json=bodies[0])
    call(other,'PUT',f'/api/v1/exams/question-banks/{bank}',403,json={'name':'越权'})
    call(t,'POST','/api/v1/exams/questions',422,json={**bodies[0],'options':[options[0]]})
    call(t,'POST','/api/v1/exams/questions',422,json={**bodies[0],'correct_answer':'Z'})
    call(t,'POST','/api/v1/exams/questions',422,json={**bodies[0],'question_type':'fill_blank'})
    checks.append('四题型校验、题库归属、学生不得读取答案或跨教师修改')

    cid=call(t,'POST','/api/v1/courses',201,json={'title':prefix+'_考试验收课程','chapters':[{'title':'课程说明','content_type':'text','text_content':'阶段五考试说明'}]}).json()['id']
    base={'title':prefix+'_固定试卷','course_id':cid,'question_ids':ids,'question_scores':{ids[0]:4},'duration_minutes':30,'max_attempts':2,'pass_score':60,'start_time':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),'end_time':(datetime.now(timezone.utc)+timedelta(days=3)).isoformat(),'grading_notes':'客观题自动判分，简答按要点人工批改'}
    call(other,'POST','/api/v1/exams',403,json=base)
    call(t,'POST','/api/v1/exams',422,json={**base,'question_ids':[ids[0],ids[0]]})
    call(t,'POST','/api/v1/exams',422,json={**base,'question_mode':'random'})
    e=call(t,'POST','/api/v1/exams',201,json=base).json();eid=e['id']
    call(t,'PUT',f'/api/v1/exams/{eid}',json=base)
    future=call(t,'POST','/api/v1/exams',201,json={**base,'title':prefix+'_未开放','start_time':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}).json()['id']
    deadline_exam=call(t,'POST','/api/v1/exams',201,json={**base,'title':prefix+'_截止检查','question_ids':[ids[0]],'question_scores':{},'max_attempts':1}).json()['id']
    temp=call(t,'POST','/api/v1/exams',201,json={**base,'title':prefix+'_临时草稿'}).json()['id']
    call(t,'DELETE',f'/api/v1/exams/{temp}',204)
    call(s,'POST',f'/api/v1/exams/{eid}/start',403)
    for action,c in (('submit_review',t),('publish',admin)):
        call(c,'POST',f'/api/v1/courses/{cid}/publish',json={'action':action})
    call(s,'POST',f'/api/v1/exams/{eid}/start',403)
    for student in (s,s2):call(student,'POST',f'/api/v1/courses/{cid}/join')
    call(s,'POST',f'/api/v1/exams/{future}/start',409)
    call(t,'POST',f'/api/v1/exams/{eid}/start',403)
    call(t,'PUT',f'/api/v1/exams/{eid}',409,json=base)
    call(t,'DELETE',f'/api/v1/exams/{eid}',409)
    checks.append('本人草稿手动组卷、逐题分值、开放时间/成员身份、发布后冻结')

    with ThreadPoolExecutor(max_workers=4) as pool:
        started=list(pool.map(lambda _:call(s,'POST',f'/api/v1/exams/{eid}/start').json(),range(4)))
    record=started[0];rid=record['record_id']
    assert len({r['record_id'] for r in started})==1 and len({r['deadline_at'] for r in started})==1
    assert record['max_score']==17 and record['is_pass'] is None
    assert 'correct_answer' not in json.dumps(record) and 'explanation' not in json.dumps(record)
    assert all('correct_answer' not in q for q in call(s,'GET',f'/api/v1/exams/records/{rid}').json()['questions'])
    answers=[{'question_id':ids[0],'answer':'A'},{'question_id':ids[1],'answer':['C','A']},{'question_id':ids[2],'answer':'false'},{'question_id':ids[3],'answer':'简答作答一'},{'question_id':ids[4],'answer':'简答作答二'}]
    call(s,'PUT',f'/api/v1/exams/records/{rid}/draft',json={'answers':answers})
    resumed=call(s,'POST',f'/api/v1/exams/{eid}/start').json()
    assert resumed['record_id']==rid and resumed['deadline_at']==record['deadline_at'] and resumed['answers']==answers
    call(t,'PUT',f'/api/v1/exams/questions/{ids[0]}',json={**bodies[0],'correct_answer':'B','score':50,'content':'题库已变，但固定试卷不变'})
    assert call(s,'POST',f'/api/v1/exams/{eid}/start').json()['questions'][0]['content']==bodies[0]['content']
    call(s2,'GET',f'/api/v1/exams/records/{rid}',403)
    call(other,'GET',f'/api/v1/exams/records/{rid}',403)
    call(s2,'POST',f'/api/v1/exams/records/{rid}/submit',403,json={'answers':[]})
    checks.append('并发开始只建一次、刷新保持答案和服务器截止、作答不泄答案、题库修改不改变试卷快照')

    call(s,'POST',f'/api/v1/exams/records/{rid}/submit',422,json={'answers':[answers[0],answers[0]]})
    call(s,'POST',f'/api/v1/exams/records/{rid}/submit',422,json={'answers':[{'question_id':str(uuid.uuid4()),'answer':'A'}]})
    result=call(s,'POST',f'/api/v1/exams/records/{rid}/submit',json={'answers':answers[:3]}).json()
    assert result['max_score']==17 and result['total_score']==8 and result['status']=='submitted' and result['is_pass'] is None and len(result['answers'])==5
    assert call(s,'POST',f'/api/v1/exams/records/{rid}/submit',json={'answers':[]}).json()['total_score']==8
    call(s,'PUT',f'/api/v1/exams/records/{rid}/draft',409,json={'answers':[]})
    gpath=f'/api/v1/exams/records/{rid}/grade'
    call(other,'POST',gpath,403,json={'answers':[{'question_id':ids[3],'score':0}]})
    call(s,'POST',gpath,403,json={'answers':[{'question_id':ids[3],'score':0}]})
    call(t,'POST',gpath,422,json={'answers':[{'question_id':ids[0],'score':0}]})
    call(t,'POST',gpath,422,json={'answers':[{'question_id':ids[3],'score':5}]})
    partial=call(t,'POST',gpath,json={'answers':[{'question_id':ids[3],'score':0,'grader_comment':'零分也已批改'}]}).json()
    assert partial['status']=='submitted' and partial['is_pass'] is None
    final=call(t,'POST',gpath,json={'answers':[{'question_id':ids[4],'score':5,'grader_comment':'第二题已批'}]}).json()
    assert final['status']=='graded' and final['total_score']==13 and final['is_pass'] is True
    call(t,'POST',gpath,json={'answers':[{'question_id':ids[4],'score':5,'grader_comment':'第二题已批'}]})
    visible=call(s,'GET',f'/api/v1/exams/records/{rid}').json()
    assert visible['total_score']==13 and visible['is_pass'] is True
    with SessionLocal() as db:
        persisted=db.get(ExamRecord,rid)
        assert persisted.total_score==13 and persisted.max_score==17 and persisted.is_pass
        marked={a['question_id']:a for a in persisted.answers}
        assert marked[ids[3]]['graded'] and marked[ids[3]]['score']==0 and marked[ids[3]]['grader_comment']=='零分也已批改'
        assert db.scalar(select(func.count()).select_from(Notification).where(Notification.event_key==f'exam:{rid}'))==1
        assert db.scalar(select(func.count()).select_from(ExamRecord).where(ExamRecord.exam_id==eid,ExamRecord.user_id==accounts['student']['id']))==1
    checks.append('重复/卷外答案拒绝、漏答固定满分、重复交卷幂等、部分阅卷保持待批、零分和JSON批改持久化、最终百分比与通知去重')

    second=call(s,'POST',f'/api/v1/exams/{eid}/start').json()
    assert second['record_id']!=rid and second['attempt_number']==2 and second['max_score']==17
    call(s,'POST',f"/api/v1/exams/records/{second['record_id']}/submit",json={'answers':[]})
    call(s,'POST',f'/api/v1/exams/{eid}/start',409)
    deadline=call(s2,'POST',f'/api/v1/exams/{deadline_exam}/start').json()
    drid=deadline['record_id']
    # The fixed paper still has the original A answer even after the bank edit.
    call(s2,'PUT',f'/api/v1/exams/records/{drid}/draft',json={'answers':[{'question_id':ids[0],'answer':'A'}]})
    with SessionLocal() as db:
        db.get(ExamRecord,drid).deadline_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();db.commit()
    expired=call(s2,'POST',f'/api/v1/exams/records/{drid}/submit',json={'answers':[{'question_id':ids[0],'answer':'B'}]}).json()
    assert expired['status']=='graded' and expired['total_score']==2 and expired['is_pass'] is True
    call(s2,'PUT',f'/api/v1/exams/records/{drid}/draft',409,json={'answers':[]})
    call(s2,'POST',f'/api/v1/exams/{deadline_exam}/start',409)
    call(other,'GET',f'/api/v1/exams/{eid}/records',403)
    teacher_list=call(t,'GET',f'/api/v1/exams/{eid}/records').json()
    assert teacher_list['meta']['total']==2 and any(r['id']==rid and r['total_score']==13 for r in teacher_list['items'])
    roster=call(t,'GET',f'/api/v1/learning/courses/{cid}/students').json()
    assert any(any(r['total_score']==13 for r in row['exam_results']) for row in roster['items'])
    checks.append('次数限制、截止后仅结算此前已保存答案、成绩列表与教师学生表一致')

    # A second unstarted student attempt is available for the browser test.
    draft=call(t,'POST','/api/v1/courses',201,json={'title':prefix+'_页面组卷草稿','chapters':[{'title':'说明','content_type':'text','text_content':'页面组卷'}]}).json()['id']
    summary={'tested_at':datetime.now(timezone.utc).isoformat(),'course_id':cid,'exam_id':eid,'record_id':rid,'draft_course_id':draft,'bank_id':bank,'question_ids':ids,'http_requests':requests,'checks':checks,'scope':'Stage 5 manual four-type exams only'}
    with SessionLocal() as db:
        summary['mysql']=db.scalar(text('SELECT VERSION()'));summary['migration']=db.scalar(text('SELECT version_num FROM alembic_version'))
    (ROOT/'.runtime/stage5-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'groups_passed':len(checks),'http_requests':requests,'results':'.runtime/stage5-results.json'}))
    for client in clients.values():client.close()


def check_deadline_and_archive():
    """Small follow-up for minimum close time and expired list state."""
    os.chdir(ROOT/'backend');sys.path.insert(0,str(ROOT/'backend'))
    from app.config import settings
    from sqlalchemy.engine import make_url
    url=make_url(settings.database_url)
    assert (url.host,url.port,url.database,url.username)==('127.0.0.1',3309,'campus_learning','campus_app')
    from app.database import SessionLocal
    from app.models.exam import ExamRecord
    fixture=json.loads((ROOT/'.runtime/stage5-results.json').read_text(encoding='utf-8'))
    accounts=json.loads((ROOT/'.runtime/stage3-accounts.json').read_text(encoding='utf-8'))
    clients=[]
    for role in ('teacher','student2','admin'):
        c=httpx.Client(base_url='http://127.0.0.1:20081',trust_env=False,timeout=20);a=accounts[role]
        token=call(c,'POST','/api/v1/auth/login',json={k:a[k] for k in ('username','password')}).json()['access_token'];c.headers['Authorization']='Bearer '+token;clients.append(c)
    t,s,admin=clients
    cid=call(t,'POST','/api/v1/courses',201,json={'title':'阶段五截止与归档检查_'+uuid.uuid4().hex[:6],'chapters':[{'title':'说明','content_type':'text','text_content':'边界检查'}]}).json()['id']
    end=(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()
    body={'title':'提前关闭考试','course_id':cid,'question_ids':[fixture['question_ids'][0]],'duration_minutes':60,'max_attempts':1,'pass_score':60,'start_time':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),'end_time':end}
    first=call(t,'POST','/api/v1/exams',201,json=body).json()['id']
    second=call(t,'POST','/api/v1/exams',201,json={**body,'title':'归档中断考试'}).json()['id']
    for action,c in (('submit_review',t),('publish',admin)):call(c,'POST',f'/api/v1/courses/{cid}/publish',json={'action':action})
    call(s,'POST',f'/api/v1/courses/{cid}/join')
    record=call(s,'POST',f'/api/v1/exams/{first}/start').json()
    assert record['deadline_at']==end
    draft={'answers':[{'question_id':fixture['question_ids'][0],'answer':'B'}]}
    call(s,'PUT',f"/api/v1/exams/records/{record['id']}/draft",json=draft)
    with SessionLocal() as db:db.get(ExamRecord,record['id']).deadline_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();db.commit()
    listed=call(s,'GET','/api/v1/exams/records/my',params={'exam_id':first}).json()
    assert listed[0]['status']=='graded' and listed[0]['is_pass'] is True
    active=call(s,'POST',f'/api/v1/exams/{second}/start').json()
    call(admin,'POST',f'/api/v1/courses/{cid}/publish',json={'action':'archive'})
    call(s,'POST',f'/api/v1/exams/{second}/start',403)
    call(s,'PUT',f"/api/v1/exams/records/{active['id']}/draft",409,json=draft)
    call(s,'POST',f"/api/v1/exams/records/{active['id']}/submit",409,json=draft)
    assert call(s,'GET',f"/api/v1/exams/records/{active['id']}").json()['status']=='in_progress'
    summary={'http_requests':requests,'checks':['考试关闭时间早于时长时使用较早截止','进入我的成绩时结算已过期尝试','归档停止开考、保存和交卷，保留历史'],'status':'PASS'}
    (ROOT/'.runtime/stage5-edge-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
    for c in clients:c.close()


if __name__=='__main__':
    check_deadline_and_archive() if '--edges' in sys.argv else main()
