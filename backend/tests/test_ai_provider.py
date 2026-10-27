import asyncio
import httpx
import pytest
from app.ai import LocalAI,AIError

def test_real_adapter_sends_local_json_and_validates(monkeypatch):
    seen=[]
    class Client:
        def __init__(self,**kw): pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,json):
            seen.append((url,json))
            return httpx.Response(200,json={'message':{'content':'{"query":"AI productivity for beginner teams"}'}},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    x=asyncio.run(LocalAI().rewrite('corporate AI',{}))
    assert x=='AI productivity for beginner teams'
    assert seen[0][0].startswith('http://127.0.0.1:11434') and seen[0][1]['format']=='json'
    assert seen[0][1]['options']['num_ctx']==4096

def test_structured_output_invalid_retries_and_fails_closed(monkeypatch):
    calls=[]
    class Client:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,json):
            calls.append(url)
            return httpx.Response(200,json={'message':{'content':'{"team_size":-5}'}},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    with pytest.raises(AIError):asyncio.run(LocalAI().extract('nonsense',{}))
    assert len(calls)==2

def test_clarification_caps_excess_choices_without_failing():
    from app.ai import Clarification
    value=Clarification.model_validate({'question':'What would you like to learn?','choices':['AI at work','Website building','Data','Leadership','Excel']})
    assert value.choices==['AI at work','Website building','Data']

def test_course_advice_is_short_separate_and_uses_only_catalogue_ids(monkeypatch):
    from app.catalogue import COURSES
    ai=LocalAI();courses=[c for c in COURSES if c['id'] in {'PY101','AI101'}]
    async def generated(instruction,payload,schema):
        return {'courses':[{'id':'PY101','reason':'Learn practical Python automation. '+'Extra wording '*40},{'id':'AI10-1','reason':'An invented ID must not appear.'},{'id':'INVENTED','reason':'A fabricated course must not appear.'}]}
    monkeypatch.setattr(ai,'_structured',generated)
    result=asyncio.run(ai.generate('Python and AI productivity',{},[{'course':c} for c in courses],[]))
    assert result.count('• ')==2
    assert 'Python Foundations' in result and 'AI for Business Teams' in result
    assert '[PY101]' in result and '[AI101]' in result and '[AI10-1]' not in result and 'INVENTED' not in result
    assert 'course cards below' in result and '\n\n• ' in result
    for line in result.splitlines():
        if line.startswith('• '): assert len(line.split(' — ')[1].split())<=19
