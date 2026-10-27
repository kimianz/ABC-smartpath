"""Explicit test doubles isolate routing; no live model claims."""
import numpy as np
from fastapi.testclient import TestClient
from app.main import create_app
from app.schemas import Requirements
from app.rag import Retriever,eligible
from app.catalogue import COURSES
from test_workflow import FakeAI,FakeRetriever
class AI(FakeAI):
    def __init__(self,intent): self.intent=intent; self.context=None
    async def classify(self,message,requirements,history): return {'intent':self.intent,'reason':'test double','search_query':message}
    async def answer_context(self,message,faqs,history): self.context=faqs; return 'Approved answer ['+faqs[0]['id']+']'
    async def general(self,message,history): return 'Test general answer'
class FAQs(FakeRetriever):
    def search(self,*a,**k): raise AssertionError('FAQ must not search courses')
    def search_faq(self,q,original_query=None): return [{'id':'FAQ-ACCESS','text':'Discuss access arrangements with staff.'}],{'sources':['FAQ-ACCESS']}
def setup(tmp_path,ai,retriever=None):
    c=TestClient(create_app(tmp_path/'r.sqlite',ai,retriever or FakeRetriever())); s=c.post('/api/sessions',json={}).json()
    return c,s,{'X-Session-Token':s['token']}
def ask(c,s,h,**body): return c.post('/api/sessions/'+s['id']+'/messages',headers=h,json=body).json()
def test_faq_independent_of_qualification(tmp_path):
    ai=AI('faq'); c,s,h=setup(tmp_path,ai,FAQs())
    r=ask(c,s,h,message='Accessible training?')
    assert r['response_kind']=='faq' and r['question_spec'] is None and r['recommendations']==[] and r['requirements']=={}
    assert r['trace']['sources']==['FAQ-ACCESS'] and ai.context[0]['text']=='Discuss access arrangements with staff.'
    assert len(c.get('/api/sessions/'+s['id'],headers=h).json()['messages'])==2

def test_explicit_support_needs_no_llm_and_capture_is_consent_aware(tmp_path):
    class Unavailable(FakeAI):
        async def classify(self,*a): raise AssertionError('No inference for explicit support')
    c,s,h=setup(tmp_path,Unavailable()); r=ask(c,s,h,message='Contact team',intent='support')
    assert r['support_requested'] and r['question'] is None
    p={'session_id':s['id'],'name':'Test','email':'test@example.com','action':'support','message':'Please discuss access','service_consent':True}
    l=c.post('/api/leads',headers=h,json=p)
    assert l.status_code==200 and l.json()['message']==p['message']
    assert c.post('/api/leads',headers=h,json=p).json()['id']==l.json()['id']
    p['service_consent']=False; assert c.post('/api/leads',headers=h,json=p).status_code==422

def test_free_text_support_and_consultation_without_recs(tmp_path):
    c,s,h=setup(tmp_path,AI('support')); r=ask(c,s,h,message='Speak to a person?')
    assert r['support_requested'] and r['trace']['intent']=='support'
    p={'session_id':s['id'],'name':'Test','email':'test@example.com','action':'consultation','service_consent':True}
    assert c.post('/api/leads',headers=h,json=p).status_code==200
    p['action']='quote'; assert c.post('/api/leads',headers=h,json=p).status_code==409

def test_vague_goal_and_typed_number_question(tmp_path):
    c,s,h=setup(tmp_path,AI('course_search')); r=ask(c,s,h,message='idk',guided_field='goal')
    assert r['question_spec']['key']=='goal' and r['question_spec']['type']=='choice' and r['question_spec']['choices'] and 'goal' not in r['requirements']
    r=ask(c,s,h,message='AI',requirements={'goal':'AI literacy','audience':'team'})
    assert r['question_spec']['key']=='team_size' and r['question_spec']['type']=='number'
    r=ask(c,s,h,message='15',guided_field='team_size')
    assert r['requirements']['team_size']==15 and r['question_spec']['key']=='experience' and r['question_spec']['type']=='choice'

def test_format_aliases():
    for alias,value in [('in-person','classroom'),('hybrid','blended'),('no preference','any')]: assert Requirements(format=alias).format==value
    assert eligible(COURSES[0],{'format':'in-person'})[0]
    assert not eligible(COURSES[0],{'format':'hybrid'})[0]
    assert eligible(COURSES[0],{'format':'any'})[0]

def test_no_match_exact_format_reasons(tmp_path):
    class Filtered(FakeRetriever):
        def search(self,q,r,advanced=True): return [],{'eligible_exclusions':{c['id']:eligible(c,r)[1] for c in COURSES if not eligible(c,r)[0]}}
    c,s,h=setup(tmp_path,AI('course_search'),Filtered())
    r=ask(c,s,h,message='Hybrid AI',requirements={'goal':'AI','audience':'team','team_size':15,'experience':'beginner','format':'hybrid'})
    assert r['response_kind']=='no_match' and r['question_spec'] is None and r['question'] is None
    assert r['requirements']['format']=='blended' and r['trace']['exclusion_counts']['format']==len(COURSES)
    assert 'delivery format' in r['answer'] and r['support_requested'] and 'enquiry form' in r['answer']

def test_faq_hybrid_filters_irrelevant_facts():
    class Encoder:
        def encode(self,docs,**k): return np.ones((len(docs),3))
    class Ranker:
        def predict(self,pairs): return np.asarray([5 if 'Accessibility' in text else -10 for q,text in pairs])
    faqs=[{'id':'A','text':'Accessibility arrangements discussed with staff.'},{'id':'B','text':'Payment processing details.'}]
    hits,trace=Retriever(encoder=Encoder(),reranker=Ranker(),faqs=faqs).search_faq('accessible learning')
    assert [f['id'] for f in hits]==['A'] and trace['sources']==['A']
    assert 'dense' in trace['pipeline'] and 'cross-encoder' in trace['pipeline']

def test_guided_structured_value_wins_over_legacy_labelled_message(tmp_path):
    c,s,h=setup(tmp_path,AI('course_search'))
    r=ask(c,s,h,message='Do you prefer online, classroom or blended training? classroom',guided_field='format',requirements={'goal':'AI','audience':'team','team_size':15,'experience':'beginner','format':'in-person'})
    assert r['requirements']['format']=='classroom' and r['response_kind']=='recommendations'
    r=ask(c,s,h,message='How many people need training? 12',guided_field='team_size',requirements={'team_size':12})
    assert r['requirements']['team_size']==12

def test_greeting_and_general_do_not_force_qualification(tmp_path):
    for intent in ['greeting','general']:
        c,s,h=setup(tmp_path,AI(intent)); r=ask(c,s,h,message='Hello' if intent=='greeting' else 'What is programming?')
        assert r['response_kind']=='general' and r['question_spec'] is None and r['requirements']=={}

def test_faq_no_evidence_does_not_invent_answer(tmp_path):
    class Empty(FAQs):
        def search_faq(self,q,original_query=None): return [],{'sources':[]}
    ai=AI('faq'); c,s,h=setup(tmp_path,ai,Empty()); r=ask(c,s,h,message='Who is the principal?')
    assert ai.context is None and r['trace']['sources']==[]
    assert 'do not have approved information' in r['answer'] and r['question'] is None

def test_optional_skips_persist_across_session_requests(tmp_path):
    class Asking(AI):
        async def plan(self,*a): return ['ask_clarification','retrieve_courses','check_eligibility']
    c,s,h=setup(tmp_path,Asking('course_search'))
    req={'goal':'AI','audience':'team','team_size':15,'experience':'beginner'}
    first=ask(c,s,h,message='AI training',requirements=req)
    assert first['question_spec']['key']=='format' and first['question_spec']['optional']
    second=ask(c,s,h,message='skip',guided_field='format',skipped_fields=['format'])
    assert second['question_spec'] is None
    assert c.get('/api/sessions/'+s['id'],headers=h).json()['skipped_fields']==['format']

def test_faq_does_not_erase_prior_course_selection(tmp_path):
    ai=AI('course_search')
    class Both(FAQs):
        def search(self,*a,**k): return FakeRetriever().search(*a,**k)
    c,s,h=setup(tmp_path,ai,Both())
    r=ask(c,s,h,message='AI training',requirements={'goal':'AI','audience':'team','team_size':15,'experience':'beginner'})
    assert r['recommendations']
    ai.intent='faq'; r=ask(c,s,h,message='What about accessibility?')
    assert r['recommendations']==[]
    assert c.get('/api/sessions/'+s['id'],headers=h).json()['recommendations']

def test_course_information_uses_exact_facts_without_eligibility(tmp_path):
    class Encoder:
        def encode(self,docs,**k): return np.ones((len(docs),3))
    class Ranker:
        def predict(self,pairs): return np.asarray([8 if 'Python Foundations.' in text else -10 for q,text in pairs])
    ai=AI('faq'); c,s,h=setup(tmp_path,ai,Retriever(encoder=Encoder(),reranker=Ranker()))
    r=ask(c,s,h,message='How much is Python Foundations?')
    assert r['response_kind']=='faq' and r['question'] is None and r['requirements']=={}
    assert ai.context[0]['id']=='PY101' and ai.context[0]['source_type']=='course'
    course=next(x for x in COURSES if x['id']=='PY101')
    assert ai.context[0]['facts']['price_gbp']==course['price_gbp']
    assert ai.context[0]['facts']['prerequisites']==course['prerequisites']
    assert r['trace']['sources']==['PY101']

def test_guided_full_vague_phrase_uses_classifier_and_clears_unvalidated_goal(tmp_path):
    class Clarifying(AI):
        async def classify(self,message,requirements,history):
            assert message=='hi idk what i want' and 'goal' not in requirements
            return {'intent':'clarification','reason':'test-only unknown subject'}
    c,s,h=setup(tmp_path,Clarifying('clarification'))
    r=ask(c,s,h,message='hi idk what i want',guided_field='goal',requirements={'goal':'hi idk what i want'})
    assert 'goal' not in r['requirements'] and r['question_spec']['key']=='goal' and r['response_kind']=='qualification'


def test_named_course_lookup_survives_negative_reranker_score():
    class Encoder:
        def encode(self,docs,**k): return np.ones((len(docs),3))
    class NegativeRanker:
        def predict(self,pairs): return np.full(len(pairs),-9.0)
    r=Retriever(encoder=Encoder(),reranker=NegativeRanker())
    for query in ['How much does Python Foundations cost?','What equipment for PY101?']:
        hits,trace=r.search_faq(query)
        assert len(hits)==1 and hits[0]['id']=='PY101' and hits[0]['exact_entity_lookup']
        course=next(c for c in COURSES if c['id']=='PY101')
        assert hits[0]['facts']['price_gbp']==course['price_gbp']
        assert trace['exact_course_lookups']==['PY101']
    hits,trace=r.search_faq('Python price',original_query='How much is Python Foundations?')
    assert hits[0]['id']=='PY101'
    hits,trace=r.search_faq('An unrelated unknown question')
    assert hits==[] and trace['exact_course_lookups']==[]

def test_faq_answer_references_only_supplied_sources_and_is_bounded(monkeypatch):
    import asyncio
    from app.ai import LocalAI
    ai=LocalAI()
    async def fake(instruction,payload,schema):
        assert 'at most 100 words' in instruction
        return {'answer':'A factual sentence about the supplied record. '*40+' [INVENTED]'}
    monkeypatch.setattr(ai,'_structured',fake)
    answer=asyncio.run(ai.answer_context('Cost?', [{'id':'PY101','facts':{'price_gbp':895}}],[]))
    assert len(answer.split())<=100 and '[PY101]' in answer and '[INVENTED]' not in answer

def test_explicit_training_subject_blocks_unrelated_high_reranker_score():
    class Encoder:
        def encode(self,docs,**k): return np.ones((len(docs),3))
    class AdversarialRanker:
        def predict(self,pairs):
            # Simulates a neural ranking error caused by generic team language.
            return np.asarray([9 if 'Category: Leadership' in text else -3 for q,text in pairs])
    subset=[c for c in COURSES if c['id'] in {'AI101','AI102','AI103','LD101'}]
    recs,trace=Retriever(courses=subset,encoder=Encoder(),reranker=AdversarialRanker()).search(
        'Beginner AI productivity training for teams online in 6 weeks',
        {'goal':'AI workplace productivity','audience':'team','team_size':15,'experience':'beginner','format':'online','timeline_weeks':6})
    assert {r['course']['id'] for r in recs}=={'AI101','AI102','AI103'}
    assert 'LD101' in trace['subject_exclusions'] and 'ai' in trace['explicit_subject_terms']

def test_named_course_context_excludes_other_high_scoring_courses():
    class Encoder:
        def encode(self,docs,**k): return np.ones((len(docs),3))
    class PositiveRanker:
        def predict(self,pairs): return np.full(len(pairs),9.0)
    r=Retriever(encoder=Encoder(),reranker=PositiveRanker())
    hits,trace=r.search_faq('How much does Python Foundations cost?')
    assert [h['id'] for h in hits]==['PY101']
    hits,trace=r.search_faq('What is the refund policy for Python Foundations?')
    assert hits[0]['id']=='PY101' and all(h['source_type']=='faq' for h in hits[1:])


def test_guided_goal_topic_is_training_intent_even_if_classifier_says_general(tmp_path):
    class Topic(AI):
        async def classify(self,*args): return {'intent':'general','training_goal':'AI workplace productivity'}
    c,s,h=setup(tmp_path,Topic('general'))
    r=ask(c,s,h,message='AI workplace productivity',guided_field='goal',requirements={'goal':'AI workplace productivity'})
    assert r['trace']['intent']=='course_search' and r['question_spec']['key']=='audience'
    assert r['requirements']['goal']=='AI workplace productivity'

def test_guided_goal_does_not_override_faq_or_support_intent(tmp_path):
    for intent in ['faq','support']:
        c,s,h=setup(tmp_path,AI(intent),FAQs())
        r=ask(c,s,h,message='What accessibility support is available?',guided_field='goal',requirements={'goal':'What accessibility support is available?'})
        assert r['response_kind']==intent and r['question_spec'] is None and 'goal' not in r['requirements']

def test_me_is_valid_guided_audience(tmp_path):
    c,s,h=setup(tmp_path,AI('course_search'))
    for answer in ['me','myself','just me','for me']:
        r=c.post('/api/sessions/'+s['id']+'/messages',headers=h,json={'message':answer,'guided_field':'audience','requirements':{'goal':'AI','audience':answer}})
        assert r.status_code==200
        assert r.json()['requirements']['audience']=='individual'
        assert r.json()['question_spec']['key']=='experience'

def test_connect_me_to_human_bypasses_training_classifier(tmp_path):
    class Offline(AI):
        async def classify(self,*a): raise AssertionError('Explicit human request must not call the model')
    c,s,h=setup(tmp_path,Offline('course_search'))
    r=ask(c,s,h,message='connect me to a human',guided_field='goal',requirements={'goal':'connect me to a human'})
    assert r['support_requested'] and r['question_spec'] is None
    assert 'goal' not in r['requirements']

def test_uncertain_but_known_topic_survives_clarification_classification(tmp_path):
    class Topic(AI):
        async def classify(self,*a): return {'intent':'clarification','training_goal':'AI training'}
    c,s,h=setup(tmp_path,Topic('clarification'))
    r=ask(c,s,h,message='i dont know sth related to ai',guided_field='goal',requirements={'goal':'i dont know sth related to ai'})
    assert r['requirements']['goal']=='AI training'
    assert r['question_spec']['key']=='audience'

def test_confusion_uses_contextual_question_and_choices(tmp_path):
    class Helpful(AI):
        async def clarify(self,message,requirements,history,key,choices,catalogue):
            assert key=='goal'
            return {'question':'Would you like to learn to build a website?' if not history else 'I mean learning website building. Is that your aim?', 'choices':['Website building','Using AI at work']}
    c,s,h=setup(tmp_path,Helpful('clarification'))
    a=ask(c,s,h,message='my website sells courses',guided_field='goal')
    b=ask(c,s,h,message='i dont understand',guided_field='goal')
    assert a['answer']!=b['answer']
    assert b['response_kind']=='support' and b['support_requested'] and b['question_spec'] is None

def test_named_ai_subject_is_preserved_even_when_model_omits_goal(tmp_path):
    c,s,h=setup(tmp_path,AI('clarification'))
    r=ask(c,s,h,message='i dont know sth related to ai',guided_field='goal',requirements={'goal':'i dont know sth related to ai'})
    assert r['requirements']['goal']=='AI training'
    assert r['question_spec']['key']=='audience'

def test_repeated_website_clarification_is_replaced_with_learning_guidance(tmp_path):
    class Repeating(AI):
        async def clarify(self,*args):
            return {'question':'What do you want to achieve with your website?', 'choices':['Sell more','Build trust']}
    c,s,h=setup(tmp_path,Repeating('clarification'))
    a=ask(c,s,h,message='my website sells training courses',guided_field='goal')
    b=ask(c,s,h,message='i dont understand',guided_field='goal')
    c2=ask(c,s,h,message='whattt',guided_field='goal')
    assert a['response_kind']=='qualification'
    assert b['response_kind']=='support' and b['support_requested']
    assert c2['question_spec'] is None and c2['support_requested']
    assert len(b['answer'].split())<30

def test_model_normalisation_cannot_drop_an_explicit_learning_subject(tmp_path):
    class Narrow(AI):
        async def classify(self,*a): return {'intent':'course_search','training_goal':'AI workplace productivity'}
    c,s,h=setup(tmp_path,Narrow('course_search'))
    r=ask(c,s,h,message='python and ai workplace productivity',guided_field='goal',requirements={'goal':'python and ai workplace productivity'})
    assert r['requirements']['goal']=='python and ai workplace productivity'
