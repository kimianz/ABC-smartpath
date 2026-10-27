"""Real local model/API end-to-end check, creates synthetic test lead. STAFF_TOKEN required."""
import httpx,json,os,time,asyncio
from pathlib import Path
from datetime import datetime,timezone,timedelta
from app.ai import LocalAI
url=os.getenv('BACKEND_URL','http://127.0.0.1:8000');staff={'Authorization':'Bearer '+os.environ['STAFF_TOKEN']}
c=httpx.Client(base_url=url,timeout=250)
def call(method,path,**kw):
 r=c.request(method,path,**kw);r.raise_for_status();return r.json()
record={'label':'Actual local Qwen/Ollama + neural retrieval + LangGraph + SQLite smoke, synthetic contact only','steps':[]}
record['health']=call('GET','/api/health');s=call('POST','/api/sessions',json={});h={'X-Session-Token':s['token']}
message='We need online AI training for 15 beginner employees within six weeks to improve workplace productivity.'
start=time.perf_counter();r=call('POST',f"/api/sessions/{s['id']}/messages",headers=h,json={'message':message})
record['first_response_seconds']=time.perf_counter()-start;record['response']=r
Path('evidence/live-smoke-attempt.json').write_text(json.dumps(record,indent=2,allow_nan=False))
assert r['mode']=='live' and r['trace']['orchestrator']=='LangGraph'
assert r['requirements']['team_size']==15 and r['requirements']['timeline_weeks']==6
assert len(r['recommendations'])==3
assert all(x['course']['id'] in ['AI101','AI102','AI103'] for x in r['recommendations'])
record['steps'].append('Real extraction, tool planning, hybrid retrieval, reranking, eligibility and grounded generation returned three AI courses')
async def rewriting():return await LocalAI().rewrite('HR staff need gen AI help at work',r['requirements'])
record['standalone_real_query_rewrite']=asyncio.run(rewriting())
body={'session_id':s['id'],'name':'Alex Demo','email':'alex@example.com','company':'Example HR Team','action':'quote','service_consent':True,'marketing_consent':False}
l=call('POST','/api/leads',json=body,headers=h)
assert l['priority']=='high' and l['experimental_ml']['label']=='EXPERIMENTAL' and l['experimental_ml']['score'] is not None
record['lead']={k:l[k] for k in ['id','name','email','priority','priority_reasons','experimental_ml']}
assert any(x['id']==l['id'] for x in call('GET','/api/staff/leads',headers=staff))
a=call('POST',f"/api/staff/leads/{l['id']}/draft",json={'kind':'quote'},headers=staff)
record['actual_ai_draft']={'subject':a['subject'],'body':a['body']}
edit=a['body']+'\n\nA member of our team will confirm dates and availability.'
e=call('PATCH',f"/api/staff/approvals/{a['id']}",json={'action':'edit','body':edit},headers=staff)
assert e['status']=='pending' and e['body']==edit
call('PATCH',f"/api/staff/approvals/{a['id']}",json={'action':'approve'},headers=staff)
assert any(x['lead_id']==l['id'] and x['body']==edit for x in call('GET','/api/staff/outbox',headers=staff))
record['steps'].append('Real lead persisted, staff retrieved it, real Qwen service draft edited and approved into local outbox')
call('POST',f"/api/staff/leads/{l['id']}/reminders",json={'due_at':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()},headers=staff)
assert call('POST','/api/staff/reminders/run',headers=staff)['sent']==1
assert call('POST','/api/staff/reminders/run',headers=staff)['sent']==0
call('POST',f"/api/staff/leads/{l['id']}/reminders",json={'due_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},headers=staff)
call('PATCH',f"/api/staff/leads/{l['id']}",json={'status':'replied'},headers=staff)
d=call('GET',f"/api/staff/leads/{l['id']}",headers=staff)
assert any(x['status']=='cancelled' for x in d['reminders'])
record['steps'].append('Due reminder outboxed once, repeated tick did not duplicate, reply status cancelled future reminder')
record['activity']=d['activity'];record['passed']=True
Path('evidence/live-smoke.json').write_text(json.dumps(record,indent=2,allow_nan=False))
print(json.dumps({'passed':True,'seconds':record['first_response_seconds'],'courses':[x['course']['id'] for x in r['recommendations']],'lead_id':l['id']},indent=2))
