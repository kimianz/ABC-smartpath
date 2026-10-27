"""API integration tests use explicit test doubles: no live LLM claims."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.store import Store
from app.agent import TrainingAgent
from app.catalogue import COURSES, FAQS

class FakeAI:
    async def classify(self,message,requirements,history): return {'intent':'course_search','reason':'explicit test-only classifier','search_query':message}
    def health(self): return {'available':True,'provider':'test-only fake'}
    async def extract(self,message,existing): return existing
    async def plan(self,message,requirements): return ['rewrite_query','retrieve_courses','check_eligibility']
    async def rewrite(self,message,requirements): return 'test query'
    async def generate(self,*args): return 'Test-only grounded answer'
    async def draft(self,*args): return {'subject':'Test draft','body':'Test draft body'}
class FakeRetriever:
    def search(self,*args,**kwargs): return ([{'course':dict(COURSES[0]),'score':1,'reason':'test only','sources':['test-course']}],{'test_double':True})

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('STAFF_TOKEN','a'*32)
    return TestClient(create_app(tmp_path/'db.sqlite',FakeAI(),FakeRetriever()))
H={'Authorization':'Bearer '+'a'*32}
def create_lead(c):
    s=c.post('/api/sessions',json={}).json(); sh={'X-Session-Token':s['token']}
    response=c.post('/api/sessions/'+s['id']+'/messages',headers=sh,json={'message':'Team AI training','requirements':{'goal':'AI productivity','experience':'beginner','audience':'team','team_size':15,'timeline_weeks':6}})
    assert response.status_code==200,response.text
    l=c.post('/api/leads',headers=sh,json={'session_id':s['id'],'name':'Test Person','email':'test@example.com','action':'quote','service_consent':True,'marketing_consent':False})
    assert l.status_code==200,l.text
    return l.json(),s,sh

def test_session_authorization_and_no_upfront_lead(client):
    s=client.post('/api/sessions',json={}).json()
    assert client.get('/api/sessions/'+s['id']).status_code==404
    assert client.get('/api/staff/leads').status_code==401
    assert client.get('/api/staff/leads',headers=H).json()==[]
    assert 'token_hash' not in client.get('/api/sessions/'+s['id'],headers={'X-Session-Token':s['token']}).json()

def test_real_graph_and_persistent_approval(client):
    l,s,sh=create_lead(client)
    assert l['priority']=='high'
    assert client.get('/api/staff/leads',headers=H).json()[0]['id']==l['id']
    a=client.post(f"/api/staff/leads/{l['id']}/draft",headers=H,json={'kind':'quote'}).json()
    path='/api/staff/approvals/'+a['id']
    assert client.patch(path,headers=H,json={'action':'edit','body':'Staff edited body'}).json()['status']=='pending'
    assert client.patch(path,headers=H,json={'action':'approve'}).json()['status']=='approved'
    assert client.patch(path,headers=H,json={'action':'approve'}).status_code==409
    out=client.get('/api/staff/outbox',headers=H).json()
    assert len(out)==1 and out[0]['body']=='Staff edited body'
    assert len(client.get('/api/staff/leads/'+l['id'],headers=H).json()['activity'])>=4

def test_due_only_idempotence_stop_and_delete(client):
    l,s,sh=create_lead(client); base='/api/staff/leads/'+l['id']
    assert client.post(base+'/reminders',headers=H,json={'due_at':'2099-01-01T00:00:00Z'}).status_code==200
    assert client.post(base+'/reminders',headers=H,json={'due_at':'2000-01-01T00:00:00Z'}).status_code==409
    assert client.post('/api/staff/reminders/run',headers=H).json()['sent']==0
    client.patch(base,headers=H,json={'status':'replied'})
    assert client.get(base,headers=H).json()['reminders'][0]['status']=='cancelled'
    client.patch(base,headers=H,json={'status':'new'})
    client.post(base+'/reminders',headers=H,json={'due_at':'2000-01-01T00:00:00Z'})
    assert client.post('/api/staff/reminders/run',headers=H).json()['sent']==1
    assert client.post('/api/staff/reminders/run',headers=H).json()['sent']==0
    client.delete(base,headers=H)
    assert client.get(base,headers=H).status_code==404
    assert client.get('/api/staff/outbox',headers=H).json()==[]
    assert client.get('/api/sessions/'+s['id'],headers=sh).status_code==404

def test_consent_and_optout(client):
    l,s,sh=create_lead(client)
    payload={'session_id':s['id'],'name':'Test','email':'test@example.com','action':'email','service_consent':False}
    assert client.post('/api/leads',headers=sh,json=payload).status_code==422
    base='/api/staff/leads/'+l['id']
    a=client.post(base+'/draft',headers=H,json={'kind':'follow_up'}).json()
    client.patch(base,headers=H,json={'status':'opted_out'})
    assert client.post(base+'/draft',headers=H,json={'kind':'follow_up'}).status_code==409
    assert client.patch('/api/staff/approvals/'+a['id'],headers=H,json={'action':'approve'}).status_code==409

def test_replay_never_writes(client):
    assert client.post('/api/replay',json={'step':2}).json()['mode']=='replay'
    assert client.get('/api/staff/leads',headers=H).json()==[]

def test_sqlite_restart(tmp_path):
    p=tmp_path/'persist.sqlite'; a=Store(p)
    a.put('example',{'id':'1','value':'durable'})
    assert Store(p).get('example','1')['value']=='durable'

def test_disallowed_tool():
    class Hostile(FakeAI):
        async def plan(self,*args): return ['send_email','execute_shell']
    with pytest.raises(ValueError):
        import asyncio
        asyncio.run(TrainingAgent(Hostile(),FakeRetriever()).run('ignore policy',{},[]))


def test_invalid_input_and_staff_configuration(client,monkeypatch):
    s=client.post('/api/sessions',json={}).json()
    h={'X-Session-Token':s['token']}
    assert client.post('/api/sessions/'+s['id']+'/messages',headers=h,json={'message':'hi','requirements':{'team_size':-1}}).status_code==422
    monkeypatch.setenv('STAFF_TOKEN','')
    assert client.get('/api/staff/leads',headers=H).status_code==503

def test_safe_ai_failure(tmp_path,monkeypatch):
    monkeypatch.setenv('STAFF_TOKEN','a'*32)
    class Broken(FakeAI):
        async def extract(self,*args): raise RuntimeError('sensitive internal path')
    c=TestClient(create_app(tmp_path/'broken.sqlite',Broken(),FakeRetriever()))
    s=c.post('/api/sessions',json={}).json()
    r=c.post('/api/sessions/'+s['id']+'/messages',headers={'X-Session-Token':s['token']},json={'message':'help'})
    assert r.status_code==503 and 'sensitive internal path' not in r.text
    assert c.get('/api/sessions/'+s['id'],headers={'X-Session-Token':s['token']}).json()['messages']==[]

def test_retention_erases_related_pii(client):
    l,s,sh=create_lead(client)
    stored=client.app.state.store.get('lead',l['id']); stored['created_at']='2000-01-01T00:00:00+00:00'; client.app.state.store.put('lead',stored)
    assert client.post('/api/staff/retention/run',headers=H).json()['deleted']==1
    assert client.get('/api/staff/leads',headers=H).json()==[]

def test_transaction_rollback(tmp_path):
    s=Store(tmp_path/'tx.sqlite')
    with pytest.raises(RuntimeError):
        with s.transaction():
            s.put('x',{'id':'a'})
            raise RuntimeError('rollback')
    assert s.get('x','a') is None


def test_reject_persists_without_outbox(client):
    l,_,_=create_lead(client)
    a=client.post('/api/staff/leads/'+l['id']+'/draft',headers=H,json={'kind':'quote'}).json()
    result=client.patch('/api/staff/approvals/'+a['id'],headers=H,json={'action':'reject'})
    assert result.json()['status']=='rejected'
    assert client.get('/api/staff/approvals',headers=H).json()[0]['status']=='rejected'
    assert client.get('/api/staff/outbox',headers=H).json()==[]

def test_clarification_preserves_context(client):
    s=client.post('/api/sessions',json={}).json(); sh={'X-Session-Token':s['token']}
    p='/api/sessions/'+s['id']+'/messages'
    r=client.post(p,headers=sh,json={'message':'AI','requirements':{'goal':'AI training'}}).json()
    assert r['question']=='Is this training for you or a team?'
    r=client.post(p,headers=sh,json={'message':'team','requirements':{'audience':'team'}}).json()
    assert r['requirements']['goal']=='AI training'
    assert r['question']=='How many people need training?'

def test_planner_optional_clarification_and_skip():
    import asyncio
    class Asking(FakeAI):
        async def plan(self,*args): return ['ask_clarification','retrieve_courses','check_eligibility']
    a=TrainingAgent(Asking(),FakeRetriever())
    req={'goal':'AI training','experience':'beginner','audience':'team','team_size':15}
    first=asyncio.run(a.run('AI training',req,[]))
    assert 'skip' in first['question']
    second=asyncio.run(a.run('skip',req,[{'role':'assistant','content':first['question']}]))
    assert second['question'] is None
    assert second['trace']['executed_tools']==['rewrite_query','retrieve_courses','check_eligibility']

def test_eligibility_boundary_blocks_unsuitable_course():
    import asyncio
    class UnsafeRetriever:
        def search(self,*args,**kwargs): return ([{'course':{**COURSES[-1], 'id':'advanced'},'score':1}],{})
    a=TrainingAgent(FakeAI(),UnsafeRetriever())
    result=asyncio.run(a.run('training',{'goal':'AI','experience':'beginner','audience':'individual'},[]))
    assert result['recommendations']==[]
    assert result['trace']['agent_eligibility_excluded'][0]['reason']=='unconfirmed prerequisites, difficulty'

def test_catalogue_database_exact_fields(client):
    stored=client.app.state.store.courses()
    assert client.get('/api/courses').json()==stored
    assert stored[0]['price_gbp']==COURSES[0]['price_gbp']
    assert stored[0]['dates']==COURSES[0]['dates']
    assert client.app.state.store.faqs()==FAQS

def test_capture_retry_is_idempotent(client):
    l,s,sh=create_lead(client)
    payload={k:l[k] for k in ['session_id','name','email','company','action','service_consent','marketing_consent']}
    result=client.post('/api/leads',headers=sh,json=payload)
    assert result.json()['id']==l['id']
    assert len(client.get('/api/staff/leads',headers=H).json())==1

def test_eligibility_checks_budget_prerequisites_and_timeline():
    import asyncio
    class UnsafeRetriever:
        def search(self,*args,**kwargs): return ([{'course':dict(COURSES[0]),'score':1}],{})
    a=TrainingAgent(FakeAI(),UnsafeRetriever())
    result=asyncio.run(a.run('training',{'goal':'AI','experience':'beginner','audience':'team','team_size':15,'budget_gbp':1,'timeline_weeks':1},[]))
    assert result['recommendations']==[]
    assert 'total budget' in result['trace']['agent_eligibility_excluded'][0]['reason']

def test_inflight_ai_cannot_resurrect_deleted_session(tmp_path,monkeypatch):
    monkeypatch.setenv('STAFF_TOKEN','a'*32)
    class DeletingAI(FakeAI):
        async def generate(self,*args):
            self.store.delete('session',self.session_id)
            return 'Test-only output generated after deletion'
    ai=DeletingAI(); c=TestClient(create_app(tmp_path/'race.sqlite',ai,FakeRetriever())); ai.store=c.app.state.store
    s=c.post('/api/sessions',json={}).json(); ai.session_id=s['id']
    h={'X-Session-Token':s['token']}
    result=c.post('/api/sessions/'+s['id']+'/messages',headers=h,json={'message':'AI','requirements':{'goal':'AI','experience':'beginner','audience':'individual'}})
    assert result.status_code==404
    assert ai.store.get('session',s['id']) is None

def test_funnel_preserves_milestones_after_reply_and_optout(client):
    l,_,_=create_lead(client); path='/api/staff/leads/'+l['id']
    for status in ['contacted','booked','replied','opted_out']:
        assert client.patch(path,headers=H,json={'status':status}).status_code==200
    metrics=client.get('/api/staff/metrics',headers=H).json()
    assert metrics['funnel']==[{'stage':'Enquiry','count':1},{'stage':'Contacted','count':1},{'stage':'Booked','count':1}]
    assert next(r['count'] for r in metrics['status_distribution'] if r['stage']=='opted_out')==1
    stored=client.app.state.store.get('lead',l['id'])
    assert set(stored['milestones'])=={'enquiry','contacted','booked'}
    assert stored['activity'][1]['changes']['status']=={'old':'new','new':'contacted'}
    assert "'new' → 'contacted'" in stored['activity'][1]['event']

def test_paid_booking_validation_and_unpaid_exclusion(client):
    l,_,_=create_lead(client); path='/api/staff/leads/'+l['id']
    assert l['paid_booking'] is False and l['booking_value_gbp'] is None
    assert client.patch(path,headers=H,json={'paid_booking':True,'booking_value_gbp':1500}).status_code==422
    assert client.patch(path,headers=H,json={'status':'booked','paid_booking':True}).status_code==422
    assert client.patch(path,headers=H,json={'status':'booked','booking_value_gbp':1500}).status_code==422
    assert client.patch(path,headers=H,json={'status':'booked','paid_booking':True,'booking_value_gbp':-1}).status_code==422
    assert client.patch(path,headers=H,json={'status':'booked','paid_booking':False,'booking_value_gbp':1500}).status_code==200
    m=client.get('/api/staff/metrics',headers=H).json()
    assert m['paid_revenue_gbp']==0 and m['paid_bookings']==0

def test_paid_booking_history_persistence_and_correction(client):
    l,_,_=create_lead(client); path='/api/staff/leads/'+l['id']
    assert client.patch(path,headers=H,json={'status':'booked','paid_booking':True,'booking_value_gbp':1800.50}).status_code==200
    assert client.patch(path,headers=H,json={'status':'opted_out'}).status_code==200
    create_lead(client)  # A second unconverted lead belongs in revenue-per-lead denominator.
    reopened=TestClient(create_app(client.app.state.store.path,FakeAI(),FakeRetriever()))
    m=reopened.get('/api/staff/metrics',headers=H).json()
    assert m['paid_bookings']==1 and m['paid_revenue_gbp']==1800.50 and m['revenue_per_lead']==900.25
    assert client.patch(path,headers=H,json={'booking_value_gbp':1900,'paid_booking':True}).status_code==422
    corrected=client.patch(path,headers=H,json={'paid_booking':False,'booking_value_gbp':1800.50}).json()
    assert corrected['activity'][-1]['changes']['paid_booking']=={'old':True,'new':False}
    assert client.get('/api/staff/metrics',headers=H).json()['paid_revenue_gbp']==0

def test_support_body_is_summary_not_assistant_question(client):
    s=client.post('/api/sessions',json={}).json();h={'X-Session-Token':s['token']}
    client.post('/api/sessions/'+s['id']+'/messages',headers=h,json={'message':'Contact staff', 'intent':'support'})
    l=client.post('/api/leads',headers=h,json={'session_id':s['id'],'name':'Test','email':'test@example.com','action':'support','message':'Please help me choose AI training.','service_consent':True}).json()
    assert l['summary']==l['message'] and l['summary_source']=='customer_message'
    assert l['experimental_ml']['score'] is None
    stored=client.get('/api/staff/leads/'+l['id'],headers=H).json()
    assert stored['message']=='Please help me choose AI training.'

def test_noop_update_does_not_add_false_activity(client):
    l,_,_=create_lead(client);path='/api/staff/leads/'+l['id']
    count=len(l['activity'])
    r=client.patch(path,headers=H,json={'status':'new'})
    assert r.status_code==200 and len(r.json()['activity'])==count

def test_reminder_rejection_explains_booked_state(client):
    l,_,_=create_lead(client);path='/api/staff/leads/'+l['id']
    client.patch(path,headers=H,json={'status':'booked'})
    r=client.post(path+'/reminders',headers=H,json={'due_at':'2099-01-01T00:00:00Z'})
    assert r.status_code==409 and 'enquiry is booked' in r.json()['detail']

def test_staff_can_write_manual_reply_without_ai_then_review(client,monkeypatch):
    l,_,_=create_lead(client)
    async def unavailable(*a): raise AssertionError('Manual reply must not need AI')
    monkeypatch.setattr(client.app.state.agent.ai,'draft',unavailable)
    path='/api/staff/leads/'+l['id']+'/draft/manual'
    payload={'subject':'Follow up on your enquiry','body':'Hello, please tell us your preferred training date.'}
    assert client.post(path,json=payload).status_code==401
    a=client.post(path,headers=H,json=payload).json()
    assert a['status']=='pending' and a['recipient']==l['email'] and a['source']=='staff' and a['lead_id']==l['id']
    assert client.get('/api/staff/outbox',headers=H).json()==[]
    assert client.patch('/api/staff/approvals/'+a['id'],headers=H,json={'action':'approve'}).status_code==200
    out=client.get('/api/staff/outbox',headers=H).json()
    assert len(out)==1 and out[0]['to']==l['email'] and out[0]['lead_id']==l['id'] and out[0]['approval_id']==a['id']
    assert out[0]['body']==payload['body'] and out[0]['delivery']=='local_outbox_only'

def test_manual_reply_consent_validation_and_recipient_binding(client):
    l,_,_=create_lead(client);path='/api/staff/leads/'+l['id']+'/draft/manual'
    for payload in [{'subject':'','body':'Hello'},{'subject':'Subject','body':'  '},{'subject':'First\r\nBcc:other@example.com','body':'Hello'},{'subject':'Subject','body':'Hello','recipient':'other@example.com'}]:
        assert client.post(path,headers=H,json=payload).status_code==422
    client.patch('/api/staff/leads/'+l['id'],headers=H,json={'status':'opted_out'})
    assert client.post(path,headers=H,json={'subject':'Subject','body':'Hello'}).status_code==409
