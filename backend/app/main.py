import asyncio
import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from .store import Store
from .schemas import Message, Capture, LeadUpdate, Draft, Decision, Reminder, Requirements, ManualDraft
from .agent import TrainingAgent
from .ai import LocalAI
from .rag import Retriever
from .catalogue import COURSES, FAQS
from . import ml

log=logging.getLogger(__name__)
def now(): return datetime.now(timezone.utc).isoformat()
def ident(): return str(uuid.uuid4())
def fail(code,detail): raise HTTPException(code,detail)
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
STOP={'booked','replied','opted_out','lost'}

def priority(r,action,recs):
    reasons=[]; points=0
    if action in {'quote','enrol','consultation'}: points+=2; reasons.append('Explicit commercial next step requested')
    if r.get('timeline_weeks',100)<=6: points+=2; reasons.append('Training needed within six weeks')
    if r.get('team_size',1)>=10: points+=2; reasons.append('Corporate cohort of at least ten people')
    if recs: points+=1; reasons.append('Eligible course recommendations available')
    return ('high' if points>=5 else 'medium' if points>=2 else 'low'),reasons

def create_app(db_path=None,ai=None,retriever=None):
    app=FastAPI(title='ABC SmartPath',version='1.0.0')
    app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Authorization','Content-Type','X-Session-Token'])
    store=Store(db_path or os.getenv('DATABASE_PATH','data/smartpath.sqlite3'))
    store.seed_catalogue(COURSES,FAQS)
    ai=ai or LocalAI(); retriever=retriever or Retriever(courses=store.courses(),faqs=store.faqs()); agent=TrainingAgent(ai,retriever)
    app.state.store=store; app.state.agent=agent
    def staff(authorization: str | None=Header(None)):
        configured=os.getenv('STAFF_TOKEN','')
        if len(configured)<24: fail(503,'Staff access is not configured: set STAFF_TOKEN to at least 24 characters')
        supplied=(authorization or '').removeprefix('Bearer ')
        if not hmac.compare_digest(supplied.encode(),configured.encode()): fail(401,'Staff authentication required')
        return True
    def session(id,token):
        s=store.get('session',id)
        if not s or not hmac.compare_digest(s.get('token_hash',''),digest(token or '')): fail(404,'Session not found')
        return s
    def lead(id):
        l=store.get('lead',id)
        if not l: fail(404,'Lead not found')
        return l
    def activity(l,event,changes=None):
        entry={'at':now(),'event':event}
        if changes: entry['changes']=changes
        l['activity'].append(entry)
        store.put('lead',l)
    def cancel(l):
        count=0
        for r in store.all('reminder'):
            if r['lead_id']==l['id'] and r['status']=='pending':
                r['status']='cancelled'; store.put('reminder',r); count+=1
        return count
    def erase(l):
        with store.transaction():
            for kind in ['reminder','approval','outbox']:
                for row in store.all(kind):
                    if row['lead_id']==l['id']: store.delete(kind,row['id'])
            store.delete('session',l['session_id']); store.delete('lead',l['id'])
            store.put('audit',{'id':ident(),'at':now(),'event':'Lead erased','lead_id':l['id']})
    @app.get('/api/health')
    async def health():
        try:
            h=ai.health()
            if asyncio.iscoroutine(h): h=await h
        except Exception: h={'available':False,'detail':'Local AI health check failed'}
        return {'status':'ok','ai':h}
    @app.get('/api/courses')
    def courses(): return store.courses()
    @app.post('/api/sessions')
    def new_session():
        token=secrets.token_urlsafe(32)
        s={'id':ident(),'token_hash':digest(token),'requirements':{},'messages':[],'recommendations':[],'created_at':now()}
        store.put('session',s)
        return {k:v for k,v in s.items() if k!='token_hash'}|{'token':token}
    @app.get('/api/sessions/{id}')
    def get_session(id:str,x_session_token:str|None=Header(None)):
        return {k:v for k,v in session(id,x_session_token).items() if k!='token_hash'}
    @app.post('/api/sessions/{id}/messages')
    async def message(id:str,body:Message,x_session_token:str|None=Header(None)):
        s=session(id,x_session_token)
        req={**s['requirements'],**(body.requirements.model_dump(exclude_none=True) if body.requirements else {})}
        try: result=await agent.run(body.message,req,s['messages'][-12:],guided_field=body.guided_field,skipped_fields=list(dict.fromkeys(s.get('skipped_fields',[])+body.skipped_fields)),intent=body.intent,guided_value=(getattr(body.requirements,body.guided_field,None) if body.requirements and body.guided_field else None))
        except Exception:
            log.exception('Training agent failed')
            fail(503,'AI guidance is temporarily unavailable. Please try again shortly or use the human-help enquiry option.')
        with store.transaction():
            current=session(id,x_session_token)
            if current['messages']!=s['messages']: fail(409,'Another message completed first; please retry')
            s['requirements']=result['requirements']
            if result.get('response_kind') in {'qualification','recommendations','no_match'}: s['recommendations']=result['recommendations']
            s['skipped_fields']=list(dict.fromkeys(s.get('skipped_fields',[])+body.skipped_fields))
            s['messages'] += [{'role':'user','content':body.message},{'role':'assistant','content':result['answer']}]
            s['messages']=s['messages'][-40:]; store.put('session',s)
        return {'session_id':id,'answer':result['answer'],'question':result.get('question'),'requirements':s['requirements'],'recommendations':result['recommendations'],'trace':result['trace'],'mode':'live','question_spec':result.get('question_spec'),'response_kind':result.get('response_kind'),'support_requested':result.get('support_requested',False),'offer_skills_challenge':result.get('offer_skills_challenge',result.get('question_spec',{}).get('key')=='experience' if result.get('question_spec') else False)}
    @app.post('/api/leads')
    def capture(body:Capture,x_session_token:str|None=Header(None)):
        s=session(body.session_id,x_session_token)
        if not body.service_consent: fail(422,'Service contact consent is required')
        if body.action in {'quote','enrol','email'} and not s['recommendations']: fail(409,'Obtain course recommendations before submitting this type of enquiry')
        with store.transaction():
            s=session(body.session_id,x_session_token)
            for existing in store.all('lead'):
                if all(existing.get(k)==v for k,v in body.model_dump().items()) and existing['requirements']==s['requirements'] and existing['recommendations']==s['recommendations']:
                    return existing
            p,reasons=priority(s['requirements'],body.action,s['recommendations'])
            l={'id':ident(),**body.model_dump(),'requirements':s['requirements'],'recommendations':s['recommendations'],'status':'new','paid_booking':False,'booking_value_gbp':None,'milestones':{'enquiry':now()},'priority':p,'priority_reasons':reasons,'experimental_ml':({'score':None,'limitations':'Not applicable to a support enquiry.'} if body.action=='support' else ml.score(s['requirements'],body.action)),'next_action':'Review enquiry and prepare response','created_at':now(),'activity':[],'summary':body.message.strip() if body.message and body.message.strip() else ('Training enquiry: '+s['requirements']['goal'] if s['requirements'].get('goal') else 'Customer requested staff assistance; no training requirements collected.'),'summary_source':'customer_message' if body.message and body.message.strip() else 'structured_requirements'}
            activity(l,'Enquiry submitted with service consent; marketing consent '+str(body.marketing_consent))
            return l
    @app.get('/api/staff/leads',dependencies=[Depends(staff)])
    def leads(): return store.all('lead')
    @app.get('/api/staff/leads/{id}',dependencies=[Depends(staff)])
    def detail(id:str):
        l=lead(id).copy()
        l['reminders']=[r for r in store.all('reminder') if r['lead_id']==id]
        l['drafts']=[r for r in store.all('approval') if r['lead_id']==id]
        return l
    @app.patch('/api/staff/leads/{id}',dependencies=[Depends(staff)])
    def update(id:str,body:LeadUpdate):
        with store.transaction():
            l=lead(id)
            updates=body.model_dump(exclude_none=True)
            resulting_status=updates.get('status',l['status'])
            resulting_value=updates.get('booking_value_gbp',l.get('booking_value_gbp'))
            # Recorded payments are historical facts. A later reply/opt-out must
            # not erase them; new confirmations and financial edits require the
            # booked state and explicit staff payment confirmation.
            value_changed='booking_value_gbp' in updates and updates['booking_value_gbp']!=l.get('booking_value_gbp')
            if value_changed and 'paid_booking' not in updates:
                fail(422,'Financial edits require explicit paid_booking confirmation')
            if updates.get('paid_booking') is True or value_changed:
                if resulting_status!='booked': fail(422,'Confirm a paid booking or edit its value while status is booked')
                if resulting_value is None: fail(422,'A booking value is required to confirm payment')
            old={k:l.get(k) for k in updates}
            old_consent={k:l.get(k) for k in ['service_consent','marketing_consent']}
            l.update(updates)
            milestones=l.setdefault('milestones',{'enquiry':l['created_at']})
            if l['status'] in {'contacted','replied','booked'}: milestones.setdefault('contacted',now())
            if l['status']=='booked': milestones.setdefault('booked',now())
            if l['status'] in STOP: cancel(l)
            if l['status']=='opted_out':
                l['service_consent']=False; l['marketing_consent']=False
                for a in store.all('approval'):
                    if a['lead_id']==id and a['status']=='pending': a['status']='rejected'; store.put('approval',a)
            changes={k:{'old':old[k],'new':l.get(k)} for k in updates if old[k]!=l.get(k)}
            for k,v in old_consent.items():
                if v!=l.get(k): changes[k]={'old':v,'new':l.get(k)}
            description='; '.join(f'{k}: {v["old"]!r} → {v["new"]!r}' for k,v in changes.items())
            if not changes: return l
            activity(l,'Staff updated '+description,changes)
            return l
    @app.delete('/api/staff/leads/{id}',dependencies=[Depends(staff)])
    def delete(id:str): erase(lead(id)); return {'deleted':True}
    @app.post('/api/staff/leads/{id}/draft',dependencies=[Depends(staff)])
    async def draft(id:str,body:Draft):
        l=lead(id)
        if not l['service_consent'] or l['status']=='opted_out': fail(409,'Contact permission withdrawn')
        try: d=await ai.draft(l,body.kind)
        except Exception: fail(503,'AI drafting temporarily unavailable')
        if not isinstance(d,dict) or not isinstance(d.get('subject'),str) or not isinstance(d.get('body'),str): fail(503,'Invalid AI draft')
        with store.transaction():
            l=lead(id)
            if not l['service_consent']: fail(409,'Contact permission withdrawn')
            a={'id':ident(),'lead_id':id,'kind':body.kind,'recipient':l['email'],'source':'ai','subject':d['subject'][:300],'body':d['body'][:10000],'status':'pending','created_at':now()}
            store.put('approval',a); activity(l,'AI draft prepared for staff review')
            return a
    @app.post('/api/staff/leads/{id}/draft/manual',dependencies=[Depends(staff)])
    def manual_draft(id:str,body:ManualDraft):
        with store.transaction():
            l=lead(id)
            if not l['service_consent'] or l['status']=='opted_out': fail(409,'Contact permission withdrawn')
            a={'id':ident(),'lead_id':id,'recipient':l['email'],'kind':body.kind,'subject':body.subject,'body':body.body,'source':'staff','status':'pending','created_at':now()}
            store.put('approval',a);activity(l,'Staff reply saved for approval')
            return a
    @app.get('/api/staff/approvals',dependencies=[Depends(staff)])
    def approvals(): return store.all('approval')
    @app.patch('/api/staff/approvals/{id}',dependencies=[Depends(staff)])
    def decision(id:str,body:Decision):
        with store.transaction():
            a=store.get('approval',id)
            if not a: fail(404,'Approval not found')
            if a['status']!='pending': fail(409,'Approval already decided')
            l=lead(a['lead_id'])
            if body.action=='edit':
                if not body.body: fail(422,'Edited body is required')
                a['body']=body.body
            elif body.action=='approve':
                if not l['service_consent'] or l['status']=='opted_out': fail(409,'Contact permission withdrawn')
                a['status']='approved'
                store.put('outbox',{'id':ident(),'lead_id':l['id'],'approval_id':a['id'],'kind':a['kind'],'to':l['email'],'subject':a['subject'],'body':a['body'],'created_at':now(),'delivery':'local_outbox_only'})
            else: a['status']='rejected'
            store.put('approval',a); activity(l,'Staff '+body.action+' draft '+id)
            return a
    @app.get('/api/staff/outbox',dependencies=[Depends(staff)])
    def outbox(): return store.all('outbox')
    @app.post('/api/staff/leads/{id}/reminders',dependencies=[Depends(staff)])
    def reminder(id:str,body:Reminder):
        try:
            due=datetime.fromisoformat(body.due_at.replace('Z','+00:00'))
            if due.tzinfo is None: raise ValueError()
            due=due.astimezone(timezone.utc)
        except ValueError: fail(422,'due_at must include timezone')
        with store.transaction():
            l=lead(id)
            if not l['service_consent']: fail(409,'Reminder unavailable: service contact permission is not active')
            if l['status'] in STOP: fail(409,'Reminder unavailable: enquiry is '+l['status'].replace('_',' ')+'. Enquiry follow-ups stop for booked, replied, opted-out or closed enquiries.')
            if any(r['lead_id']==id and r['status']=='pending' for r in store.all('reminder')): fail(409,'A reminder is already pending')
            r={'id':ident(),'lead_id':id,'due_at':due.isoformat(),'status':'pending','created_at':now()}
            store.put('reminder',r); activity(l,'Service reminder scheduled'); return r
    @app.post('/api/staff/reminders/run',dependencies=[Depends(staff)])
    def run_reminders():
        sent=cancelled=0
        with store.transaction():
            for r in store.all('reminder'):
                if r['status']!='pending': continue
                l=store.get('lead',r['lead_id'])
                if not l or not l['service_consent'] or l['status'] in STOP:
                    r['status']='cancelled'; cancelled+=1
                elif datetime.fromisoformat(r['due_at'])<=datetime.now(timezone.utc):
                    store.put('outbox',{'id':'reminder-'+r['id'],'lead_id':l['id'],'to':l['email'],'subject':'Your ABC training enquiry','body':'Thank you for your training enquiry. Reply to our team if you would like help with your next step.','created_at':now(),'delivery':'local_outbox_only'})
                    r['status']='sent'; sent+=1; activity(l,'Routine service reminder added to local outbox')
                store.put('reminder',r)
        return {'sent':sent,'cancelled':cancelled}
    @app.post('/api/staff/retention/run',dependencies=[Depends(staff)])
    def retention():
        days=max(1,int(os.getenv('RETENTION_DAYS','90'))); cutoff=datetime.now(timezone.utc)-timedelta(days=days); deleted=0
        for l in store.all('lead'):
            if datetime.fromisoformat(l['created_at'])<cutoff: erase(l); deleted+=1
        for s in store.all('session'):
            if datetime.fromisoformat(s['created_at'])<cutoff: store.delete('session',s['id'])
        return {'deleted':deleted}
    @app.get('/api/staff/metrics',dependencies=[Depends(staff)])
    def metrics():
        ls=store.all('lead')
        revenue=round(sum(l.get('booking_value_gbp') or 0 for l in ls if l.get('paid_booking') is True),2)
        return {'leads':len(ls),'booked':sum(l['status']=='booked' for l in ls),'open':sum(l['status'] not in STOP for l in ls),'high_priority':sum(l['priority']=='high' for l in ls),'outbox':len(store.all('outbox')),
            'funnel':[{'stage':label,'count':sum(bool(l.get('milestones',{}).get(key)) for l in ls)} for key,label in [('enquiry','Enquiry'),('contacted','Contacted'),('booked','Booked')]],
            'status_distribution':[{'stage':s,'count':sum(l['status']==s for l in ls)} for s in ['new','contacted','booked','replied','opted_out','lost']],
            'paid_bookings':sum(l.get('paid_booking') is True for l in ls),'paid_revenue_gbp':revenue,'revenue_per_lead':round(revenue/len(ls),2) if ls else 0,'sample_data':False}
    @app.post('/api/replay')
    def replay(body:dict|None=None):
        r={'goal':'AI training for workplace productivity','experience':'beginner','audience':'team','team_size':15,'timeline_weeks':6,'format':'online'}
        recs=[{'course':c,'score':0.9-i*.1,'reason':'Recorded illustrative corporate training scenario; validate suitability in live mode.','sources':[c['id']]} for i,c in enumerate(COURSES[:3])]
        return {'session_id':'replay-only','mode':'replay','answer':'Recorded fallback: a team of 15 needs introductory AI training within six weeks. These are illustrative catalogue recommendations, not live model output.','question':None,'requirements':r,'recommendations':recs,'trace':{'orchestrator':'deterministic replay','live_model':False},'steps':['Corporate enquiry recorded','Requirements qualified','Catalogue recommendations shown','Quote action illustrated','Staff approval illustrated'],'step':max(0,min(4,int((body or {}).get('step',0))))}
    return app

app=create_app()
