"""Hosting tests use a mocked cloud provider, never live inference claims."""
import asyncio
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.ai import LocalAI
from app.hosting import validate_environment, PublicBoundary, WebsiteFiles
from app.store import Store


def configure(monkeypatch, tmp_path):
    for k,v in {'APP_ENV':'public_demo','AI_PROVIDER':'ollama_cloud','OLLAMA_URL':'https://ollama.com','OLLAMA_API_KEY':'test-key-not-real','OLLAMA_MODEL':'test-cloud-model','STAFF_TOKEN':'x'*32,'DATABASE_PATH':str(tmp_path/'db.sqlite3')}.items():
        monkeypatch.setenv(k,v)


def test_cloud_adapter_uses_server_authorization_and_schema_validation(monkeypatch,tmp_path):
    configure(monkeypatch,tmp_path);seen=[]
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,url,json,headers):
            seen.append((url,json,headers))
            return httpx.Response(200,json={'message':{'content':'{"query":"Python automation"}'}},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    assert asyncio.run(LocalAI().rewrite('Python',{}))=='Python automation'
    url,payload,headers=seen[0]
    assert url=='https://ollama.com/api/chat'
    assert payload['model']=='test-cloud-model'
    assert headers=={'Authorization':'Bearer test-key-not-real'}
    assert 'test-key-not-real' not in str(payload)


def test_hosted_config_fails_closed_for_missing_secret_or_wrong_url(monkeypatch,tmp_path):
    configure(monkeypatch,tmp_path);validate_environment()
    monkeypatch.setenv('OLLAMA_URL','https://evil.example')
    with pytest.raises(RuntimeError): validate_environment()
    monkeypatch.setenv('OLLAMA_URL','https://ollama.com');monkeypatch.delenv('OLLAMA_API_KEY')
    with pytest.raises(RuntimeError): validate_environment()


def fixture_app(tmp_path,per_minute=60,daily_messages=100):
    app=FastAPI()
    @app.post('/api/sessions')
    def create(): return {'ok':True}
    @app.post('/api/sessions/test/messages')
    def message(): return {'ok':True}
    @app.get('/api/test')
    def read(): return {'ok':True}
    app.add_middleware(PublicBoundary,store=Store(tmp_path/'db.sqlite3'),per_minute=per_minute,daily_messages=daily_messages)
    return app


def test_body_limit_and_api_no_cache(tmp_path):
    with TestClient(fixture_app(tmp_path)) as c:
        r=c.post('/api/sessions',content=b'x'*65537)
        assert r.status_code==413
        assert r.headers['cache-control']=='no-store'
        assert c.get('/api/test').headers['x-content-type-options']=='nosniff'


def test_rate_limit_does_not_block_browsing(tmp_path):
    with TestClient(fixture_app(tmp_path,per_minute=1)) as c:
        assert c.post('/api/sessions').status_code==200
        assert c.post('/api/sessions').status_code==429
        assert c.get('/api/test').status_code==200


def test_daily_message_budget_survives_restart_and_preserves_handoff(tmp_path):
    for iteration in range(2):
        with TestClient(fixture_app(tmp_path,daily_messages=1)) as c:
            assert c.post('/api/sessions/test/messages').status_code==(200 if iteration==0 else 429)
            assert c.post('/api/sessions').status_code==200


def test_spa_fallback_never_hides_missing_api_or_assets(tmp_path):
    (tmp_path/'index.html').write_text('<h1>SmartPath</h1>')
    app=FastAPI();app.mount('/',WebsiteFiles(directory=tmp_path,html=True))
    with TestClient(app) as c:
        assert c.get('/finder').status_code==200
        assert c.get('/api/not-real').status_code==404
        assert c.get('/missing.js').status_code==404
        assert c.get('/.env').status_code==404
