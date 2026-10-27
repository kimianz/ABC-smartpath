"""Cloud entry point, kept separate from the original local application."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
import httpx
from fastapi.responses import JSONResponse
from .hosting import PublicBoundary, WebsiteFiles, validate_environment

validate_environment()
from .main import app

log = logging.getLogger(__name__)
ready = False

async def prepare_search():
    global ready
    try:
        await asyncio.to_thread(app.state.agent.retriever._load)
        ready = True
    except Exception:
        log.error('Retrieval model warm-up failed; readiness remains unavailable')

async def reminders():
    while True:
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://internal') as c:
                response = await c.post('/api/staff/reminders/run', headers={'Authorization': 'Bearer '+os.environ['STAFF_TOKEN']})
                if response.status_code != 200:
                    log.warning('Reminder processing returned status %s', response.status_code)
        except Exception:
            log.warning('Reminder processing temporarily unavailable')
        await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(_):
    warm = asyncio.create_task(prepare_search())
    worker = asyncio.create_task(reminders())
    try:
        yield
    finally:
        for task in (warm, worker):
            task.cancel()
        for task in (warm, worker):
            with suppress(asyncio.CancelledError):
                await task

app.router.lifespan_context = lifespan
app.add_middleware(PublicBoundary, store=app.state.store)

@app.get('/api/ready')
async def readiness():
    health = await app.state.agent.ai.health()
    ok = ready and health.get('available', False)
    return JSONResponse({'ready': ok, 'search_ready': ready, 'ai_available': health.get('available', False)}, status_code=200 if ok else 503)

@app.get('/api/site-info')
def site_info():
    return {'environment': 'public_demo', 'notice': 'Interview demonstration. Courses and prices are sample inventory. Use made-up contact details. No payment is taken and no email is sent automatically.', 'ai_provider': 'Ollama Cloud'}

static = Path(os.getenv('STATIC_DIR', '/app/static'))
if not (static/'index.html').is_file():
    raise RuntimeError('Built website assets are missing')
app.mount('/', WebsiteFiles(directory=static, html=True), name='website')
