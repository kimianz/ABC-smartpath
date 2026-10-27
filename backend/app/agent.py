"""One bounded LangGraph agent: intent-aware read tools; writes stay in validated APIs."""
import asyncio
import re
from collections import Counter
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .schemas import Requirements
from .rag import eligible
from .catalogue import COURSES

ALLOWED_TOOLS={'rewrite_query','retrieve_courses','check_eligibility','ask_clarification'}
SPECS={
 'goal':{'label':'What would you like to learn? For example, using AI at work, building websites or working with data.','type':'text','choices':[],'optional':False},
 'audience':{'label':'Is this training for you or a team?','type':'choice','choices':['individual','team'],'optional':False},
 'team_size':{'label':'How many people need training?','type':'number','choices':[],'optional':False},
 'experience':{'label':'What is the current experience level: beginner, intermediate or advanced?','type':'choice','choices':['beginner','intermediate','advanced'],'optional':False},
 'format':{'label':'Do you prefer online, classroom or blended training? You can skip this.','type':'choice','choices':['online','classroom','blended','any'],'optional':True},
 'timeline_weeks':{'label':'Within how many weeks would you like to train? You can skip this.','type':'number','choices':[],'optional':True}}
VAGUE={'idk',"i don't know",'i dont know','not sure','unsure','hello','hi','help','something','training','courses','i need help','i need training'}
def vague(value): return not value or value.lower().strip(' .!?') in VAGUE

class AgentState(TypedDict,total=False):
    message:str
    requirements:dict
    history:list
    plan:list[str]
    completed:list[str]
    query:str
    recommendations:list
    trace:dict
    question:str|None
    question_spec:dict|None
    answer:str
    intent:str
    requested_intent:str|None
    response_kind:str
    support_requested:bool
    guided_value:object
    guided_field:str|None
    skipped_fields:list[str]
    resolved_goal:str|None

class TrainingAgent:
    def __init__(self,ai,retriever):
        self.ai,self.retriever=ai,retriever
        graph=StateGraph(AgentState)
        for name in ['classify','support','faq','general','extract','plan','clarify','rewrite','retrieve','eligibility','generate']:
            graph.add_node(name,getattr(self,name))
        graph.add_edge(START,'classify')
        graph.add_conditional_edges('classify',self.intent_route,{k:k for k in ['support','faq','general','clarify','extract']})
        graph.add_edge('extract','plan')
        routes={k:k for k in ['clarify','rewrite','retrieve','eligibility','generate']}
        for node in ['plan','rewrite','retrieve','eligibility']: graph.add_conditional_edges(node,self.route,routes)
        for node in ['generate','clarify','support','faq','general']: graph.add_edge(node,END)
        self.graph=graph.compile()
    async def classify(self,s):
        explicit_support=bool(re.search(r'\b(?:connect|speak|talk|chat|contact|put)\b.{0,45}\b(?:human|person|advis[eo]r|staff|support team|customer service)\b',s['message'],re.I))
        if s.get('requested_intent')=='support' or explicit_support: result={'intent':'support','reason':'Explicit contact-staff action'}
        elif s.get('guided_field')=='goal':
            answer=str(s.get('guided_value') if s.get('guided_value') is not None else s['message'])
            if vague(answer): result={'intent':'clarification','reason':'Unknown training subject; a useful topic is needed'}
            else:
                known={k:v for k,v in s['requirements'].items() if k!='goal'}
                result=await self.ai.classify(answer,known,s['history'])
            if result['intent']=='greeting': result['intent']='clarification'
            elif result['intent']=='general':
                result['intent']='course_search' if result.get('training_goal') else 'clarification'
                result['reason']='Resolve the learning need entered in the training-goal field'
        elif s.get('guided_field'):
            result={'intent':'course_search','reason':'Explicit guided training answer'}
        else: result=await self.ai.classify(s['message'],s['requirements'],s['history'])
        if result['intent'] not in {'course_search','faq','support','general','greeting','clarification'}: raise ValueError('Invalid intent')
        resolved_goal=result.get('training_goal')
        if s.get('guided_field')=='goal' and result['intent'] in {'clarification','general'} and not resolved_goal:
            # Preserve named catalogue subjects despite uncertain phrasing.
            terms={c['category'] for c in COURSES}|{skill for c in COURSES for skill in c['skills']}
            named=sorted((term for term in terms if re.search(r'\b'+re.escape(term)+r'\b',s['message'],re.I)),key=len,reverse=True)
            if named:
                resolved_goal=named[0]+' training'
                result['intent']='course_search'
                result['reason']='Explicit catalogue subject retained despite uncertain phrasing'
        if resolved_goal and not vague(resolved_goal) and result['intent']=='clarification':
            result['intent']='course_search'
        requirements=dict(s['requirements'])
        original_goal=requirements.get('goal')
        uncertain=bool(original_goal and re.search(r"\b(?:idk|don'?t know|do not know|not sure|unsure)\b",original_goal,re.I))
        if result['intent']=='course_search' and original_goal and not vague(original_goal) and not uncertain:
            # Normalisation must not erase a subject explicitly supplied by the customer.
            resolved_goal=original_goal
        if resolved_goal and result['intent']=='course_search': requirements['goal']=resolved_goal
        if s.get('guided_field')=='goal' and result['intent']!='course_search': requirements.pop('goal',None)
        return {'requirements':requirements,'intent':result['intent'],'query':result.get('search_query') or s['message'],'recommendations':[],
            'completed':[],'question':None,'question_spec':None,'support_requested':False,
            'resolved_goal':resolved_goal,'trace':{'orchestrator':'LangGraph','intent':result['intent'],'routing_reason':result.get('reason',''),'executed_tools':[]}}
    def intent_route(self,s):
        return {'course_search':'extract','faq':'faq','support':'support','general':'general','greeting':'general','clarification':'clarify'}[s['intent']]
    async def support(self,s):
        return {'answer':'I can pass your enquiry to the ABC team. Use the contact form to describe what you need and give permission for a service reply. No training questionnaire is required.','response_kind':'support','support_requested':True}
    async def faq(self,s):
        hits,trace=await asyncio.to_thread(self.retriever.search_faq,s['query'],original_query=s['message'])
        answer=await self.ai.answer_context(s['message'],hits,s['history']) if hits else 'I do not have approved information that answers that question. You can contact the ABC team for a service reply.'
        return {'answer':answer,'response_kind':'faq','trace':{**s['trace'],**trace,'approved_faqs':hits,'executed_tools':['retrieve_approved_faqs']}}
    async def general(self,s):
        answer='Hello! I can help you find training, answer questions about ABC, or contact the team. What would you like help with?' if s['intent']=='greeting' else await self.ai.general(s['message'],s['history'])
        return {'answer':answer,'response_kind':'general'}
    async def extract(self,s):
        message=s['message']
        if s.get('guided_field'): message=f"Answer to training field {s['guided_field']}: {s.get('guided_value') if s.get('guided_value') is not None else message}"
        extracted=await self.ai.extract(message,s['requirements'])
        clean=Requirements.model_validate(extracted).model_dump(exclude_none=True)
        merged={**s['requirements'],**clean}
        if vague(merged.get('goal')): merged.pop('goal',None)
        # Explicit guided values win over generative interpretation.
        key=s.get('guided_field')
        if key and key not in s.get('skipped_fields',[]):
            value=s.get('guided_value') if s.get('guided_value') is not None else s['message'].strip()
            if key=='goal' and s.get('resolved_goal'): value=s['resolved_goal']
            if key in {'team_size','timeline_weeks','budget_gbp'}:
                try: value=float(value) if key=='budget_gbp' else int(value)
                except ValueError: value=None
            if value is not None and not (key=='goal' and vague(value)):
                validated=Requirements.model_validate({key:value}).model_dump(exclude_none=True)
                merged.update(validated)
        return {'requirements':merged}
    async def plan(self,s):
        plan=await self.ai.plan(s['message'],s['requirements'])
        if not isinstance(plan,list) or len(plan)>4 or any(p not in ALLOWED_TOOLS for p in plan): raise ValueError('Model requested an unavailable tool')
        return {'plan':list(dict.fromkeys(plan)),'trace':{**s['trace'],'allowed_tools':sorted(ALLOWED_TOOLS),'plan':plan}}
    def clarification_key(self,s,optional=False):
        r=s['requirements']
        if vague(r.get('goal')): return 'goal'
        if not r.get('audience'): return 'audience'
        if r.get('audience')=='team' and not r.get('team_size'): return 'team_size'
        if not r.get('experience'): return 'experience'
        if r.get('audience')=='individual' and r.get('team_size',1)>1: return 'audience'
        if optional:
            for key in ['format','timeline_weeks']:
                if not r.get(key) and key not in s.get('skipped_fields',[]): return key
        return None
    def route(self,s):
        if self.clarification_key(s): return 'clarify'
        done=s['completed']
        if 'ask_clarification' in s['plan'] and not done:
            key=self.clarification_key(s,True)
            skipped=any(word in s['message'].lower() for word in ['skip','no preference','any format','flexible'])
            asked=key and any(m.get('role')=='assistant' and m.get('content')==SPECS[key]['label'] for m in s['history'])
            if key and not skipped and not asked: return 'clarify'
        if ('rewrite_query' in s['plan'] or len(s['message'])>80 or s.get('history')) and 'rewrite_query' not in done: return 'rewrite'
        if 'retrieve_courses' not in done: return 'retrieve'
        if 'check_eligibility' not in done: return 'eligibility'
        return 'generate'
    def executed(self,s,tool):
        done=s['completed']+[tool]
        return {'completed':done,'trace':{**s['trace'],'executed_tools':done}}
    async def clarify(self,s):
        key='goal' if s['intent']=='clarification' else self.clarification_key(s,True)
        if key=='goal' and any(m.get('role')=='assistant' for m in s['history']):
            return {'answer':"I'm not quite sure what you need yet. Our team can help—please share a little more in the enquiry form.",
                'question':None,'question_spec':None,'recommendations':[],'response_kind':'support','support_requested':True,
                **self.executed(s,'offer_staff_help')}
        spec={'key':key,**SPECS[key]}
        answer=spec['label']
        if key=='experience': answer+=' Not sure? You can try the optional 6-minute skills challenge for automated feedback and a suggested starting point. It is demonstration guidance, not an expert assessment.'
        if key=='goal':
            # The live provider generates contextual guidance; test doubles can
            # exercise the graph using the documented plain-language default.
            if hasattr(self.ai,'clarify'):
                help_text=await self.ai.clarify(s['message'],s['requirements'],s['history'],key,[],getattr(self.retriever,'courses',[]))
                answer=help_text['question']
                choices=[x.strip()[:120] for x in help_text.get('choices',[]) if isinstance(x,str) and x.strip()][:3]
            else:
                choices=['Using AI at work','Building websites','Working with data']
                if any(m.get('role')=='assistant' for m in s['history']):
                    answer='I mean: what would you like to learn to do? You can choose an example below, or ask a human for help.'
            previous=[m['content'].strip().lower() for m in s['history'] if m.get('role')=='assistant']
            repeated=any(answer.strip().lower()==old or old.startswith(answer.strip().lower()) for old in previous)
            confused=bool(re.search(r"\b(?:don'?t understand|do not understand|what+t*|confused|what do you mean)\b",s['message'],re.I))
            if repeated or confused or len(answer.split())>35 or not re.search(r'\b(?:learn|learning|skills?|study|studying)\b',answer,re.I):
                context=' '.join([s['message']]+[m.get('content','') for m in s['history'] if m.get('role')=='user']).lower()
                if 'website' in context:
                    options=[
                        'Are you looking for training to learn coding for a website, or to use AI with your existing website?',
                        'I mean what you want to learn to do. For your website, choose coding skills or using AI to help customers.',
                        'No technical terms needed. Choose the skill you want help learning, or ask a human adviser.'
                    ]
                    answer=options[min(len(previous),2)]
                    choices=['Learn coding basics','Use AI with customers']
                else:
                    answer=('Choose something you would like to learn: using AI at work, Python programming or Excel spreadsheets.' if not previous else
                            'You do not need to know a course name. Pick a skill below, or use Ask a human for help.')
                    choices=['Using AI at work','Python programming','Excel spreadsheets']
            spec={**spec,'label':answer,'choices':choices,'type':'choice' if choices else 'text'}
            if sum(1 for m in s['history'] if m.get('role')=='assistant')>=2:
                answer+=' You can also use Ask a human for help.'
        return {'question':spec['label'],'question_spec':spec,'answer':answer,'recommendations':[],'response_kind':'qualification',**self.executed(s,'ask_clarification')}
    async def rewrite(self,s):
        return {'query':await self.ai.rewrite(s['message'],s['requirements']),**self.executed(s,'rewrite_query')}
    async def retrieve(self,s):
        recs,trace=await asyncio.to_thread(self.retriever.search,s.get('query',s['message']),s['requirements'],advanced=True)
        result=self.executed(s,'retrieve_courses'); result['trace'].update(trace); result['trace']['query']=s.get('query',s['message'])
        return {'recommendations':recs[:3],**result}
    async def eligibility(self,s):
        accepted=[]; removed=[]
        for item in s['recommendations']:
            c=item.get('course',{}); reason=None
            required={'id','title','level','formats','capacity','required_skills','audiences','price_gbp','dates'}
            if not required.issubset(c): reason='invalid catalogue record'
            else:
                ok,reasons=eligible(c,s['requirements'])
                if not ok: reason=', '.join(reasons)
            if reason: removed.append({'course_id':c.get('id'),'reason':reason})
            else: accepted.append(item)
        result=self.executed(s,'check_eligibility'); result['trace']['agent_eligibility_excluded']=removed
        return {'recommendations':accepted,**result}
    async def generate(self,s):
        if not s['recommendations']:
            exclusions=s['trace'].get('eligible_exclusions',{})
            counts=Counter(reason for reasons in exclusions.values() for reason in reasons)
            if not counts:
                for row in s['trace'].get('agent_eligibility_excluded',[]): counts.update(row['reason'].split(', '))
            labels={'format':'delivery format','total budget':'total budget','timeline':'requested timeframe','difficulty':'experience level','unconfirmed prerequisites':'unconfirmed required skills','cohort capacity':'group size','audience':'learner audience','no future dates':'available future dates'}
            details='; '.join(f"{n} candidate{'s' if n!=1 else ''}: {labels.get(reason,reason)}" for reason,n in sorted(counts.items()))
            constraints=', '.join(labels.get(reason,reason) for reason in sorted(counts)[:3])
            answer='I could not find a suitable course'+(' matching your '+constraints if constraints else ' for these needs')+'. Our team can help you explore alternatives—please use the enquiry form.'
            return {'answer':answer,'question':None,'question_spec':None,'response_kind':'no_match','support_requested':True,'trace':{**s['trace'],'exclusion_counts':dict(counts)}}
        answer=await self.ai.generate(s['message'],s['requirements'],s['recommendations'],s['history'])
        return {'answer':answer,'question':None,'question_spec':None,'response_kind':'recommendations'}
    async def run(self,message,requirements,history,guided_field=None,skipped_fields=None,intent=None,guided_value=None):
        unsure=bool(re.search(r"\b(?:not sure|unsure|don'?t know|do not know|idk|how do i know|what is my|what's my)\b",message,re.I))
        level_context=guided_field=='experience' or bool(re.search(r'\b(?:level|experience|beginner|intermediate|advanced)\b',message,re.I))
        explicit_human=bool(re.search(r'\b(?:human|staff|adviser|advisor|person|support)\b',message,re.I))
        if unsure and level_context and intent!='support' and not explicit_human:
            spec={'key':'experience',**SPECS['experience']}
            return {'requirements':requirements,'answer':'Not sure of your level? Try the optional 6-minute skills challenge for automated feedback and a suggested starting point, or tell me which level feels closest. The sample questions are awaiting subject-expert review.',
                    'recommendations':[],'question':spec['label'],'question_spec':spec,'response_kind':'qualification','offer_skills_challenge':True,'support_requested':False,
                    'trace':{'orchestrator':'LangGraph entry routing','executed_tools':['offer_skills_challenge'],'intent':'level_guidance'}}
        return await asyncio.wait_for(self.graph.ainvoke({'message':message,'requirements':requirements,'history':history,
            'guided_value':guided_value,'guided_field':guided_field,'skipped_fields':skipped_fields or [],'requested_intent':intent},config={'recursion_limit':18}),timeout=240)
