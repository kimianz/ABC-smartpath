from fastapi.testclient import TestClient
from app.main import create_app
from test_workflow import FakeAI,FakeRetriever
class NoAI(FakeAI):
 async def classify(self,*args):raise AssertionError('Uncertain level invitation does not need model inference')
def test_unsure_level_is_optional_and_does_not_invent_experience(tmp_path):
 c=TestClient(create_app(tmp_path/'quiz.sqlite',NoAI(),FakeRetriever()));s=c.post('/api/sessions',json={}).json();h={'X-Session-Token':s['token']}
 r=c.post('/api/sessions/'+s['id']+'/messages',headers=h,json={'message':"I don't know my level",'requirements':{'goal':'Python','audience':'individual'}})
 assert r.status_code==200
 d=r.json();assert d['offer_skills_challenge'] is True and d['question_spec']['key']=='experience'
 assert 'experience' not in d['requirements'] and d['recommendations']==[] and not d['support_requested']
 assert 'expert' in d['answer'] and '6-minute' in d['answer']
 assert len(c.get('/api/sessions/'+s['id'],headers=h).json()['messages'])==2
 assert c.post('/api/sessions/'+s['id']+'/messages',json={'message':'I am unsure of my level'}).status_code==404

def test_human_help_takes_precedence_over_level_challenge(tmp_path):
 c=TestClient(create_app(tmp_path/'support.sqlite',NoAI(),FakeRetriever()));s=c.post('/api/sessions',json={}).json()
 d=c.post('/api/sessions/'+s['id']+'/messages',headers={'X-Session-Token':s['token']},json={'message':"I don't know my level, connect me to a human"}).json()
 assert d['support_requested'] and not d['offer_skills_challenge']
