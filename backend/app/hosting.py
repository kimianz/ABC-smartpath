"""Public-demo hosting boundary. One process/instance, persistent SQLite disk."""
import hashlib
import os
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import urlparse
from starlette.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse


def validate_environment():
    if os.getenv('APP_ENV') != 'public_demo':
        raise RuntimeError('Hosted entry point requires APP_ENV=public_demo')
    if os.getenv('AI_PROVIDER') != 'ollama_cloud':
        raise RuntimeError('Public demo requires configured hosted AI')
    url = urlparse(os.getenv('OLLAMA_URL', 'https://ollama.com'))
    # This adapter deliberately supports the official endpoint only. No exposed
    # Mac, user-supplied endpoint, or unintended secret forwarding.
    if url.scheme != 'https' or url.netloc != 'ollama.com' or url.path not in ('', '/'):
        raise RuntimeError('Hosted AI endpoint must be https://ollama.com')
    for key in ('OLLAMA_API_KEY', 'OLLAMA_MODEL'):
        if not os.getenv(key) or os.getenv(key, '').startswith('REPLACE_'):
            raise RuntimeError('Missing hosted configuration: ' + key)
    if len(os.getenv('STAFF_TOKEN', '')) < 32:
        raise RuntimeError('Hosted staff token must have at least 32 characters')
    if not Path(os.getenv('DATABASE_PATH', '')).is_absolute():
        raise RuntimeError('Hosted database needs an absolute persistent-disk path')


class PublicBoundary:
    """Bound JSON sizes and public request volume; omit raw IPs from memory.

    Proxy-visible peer addresses may aggregate visitors, conservatively. The
    hosting layer should add network-level abuse controls for sustained use.
    A durable daily message ceiling also bounds exposure across restarts.
    """
    def __init__(self, app, store, per_minute=60, daily_messages=100):
        self.app, self.store = app, store
        self.per_minute, self.daily_messages = per_minute, daily_messages
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        path, method = scope['path'], scope['method']
        async def protected_send(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers += [(b'x-content-type-options', b'nosniff'),
                            (b'referrer-policy', b'same-origin'),
                            (b'permissions-policy', b'camera=(), microphone=(), geolocation=()')]
                if path.startswith('/api/'):
                    headers.append((b'cache-control', b'no-store'))
                message = {**message, 'headers': headers}
            await send(message)
        if method in ('POST', 'PATCH', 'DELETE') and path.startswith('/api/'):
            peer = str(scope.get('client', ('unknown',))[0])
            key = hashlib.sha256(peer.encode()).hexdigest()
            now = time.monotonic()
            with self.lock:
                for old in list(self.requests):
                    if not self.requests[old] or now-self.requests[old][-1] >= 60:
                        del self.requests[old]
                queue = self.requests[key]
                while queue and now-queue[0] >= 60:
                    queue.popleft()
                limited = len(queue) >= self.per_minute
                if not limited:
                    queue.append(now)
            if limited:
                return await JSONResponse({'detail': 'Please wait a minute before trying again.'}, 429, headers={'Retry-After': '60'})(scope, receive, protected_send)
            body = bytearray()
            while True:
                event = await receive()
                if event['type'] == 'http.disconnect':
                    return
                body.extend(event.get('body', b''))
                if len(body) > 65536:
                    return await JSONResponse({'detail': 'This request is too large.'}, 413)(scope, receive, protected_send)
                if not event.get('more_body'):
                    break
            if method == 'POST' and path.startswith('/api/sessions/') and path.endswith('/messages'):
                from datetime import datetime, timezone
                day = datetime.now(timezone.utc).date().isoformat()
                with self.store.transaction():
                    budget = self.store.get('hosting_budget', 'messages') or {'id': 'messages', 'day': day, 'count': 0}
                    if budget['day'] != day:
                        budget = {'id': 'messages', 'day': day, 'count': 0}
                    daily_limited = budget['count'] >= self.daily_messages
                    if not daily_limited:
                        budget['count'] += 1
                        self.store.put('hosting_budget', budget)
                if daily_limited:
                    return await JSONResponse({'detail': 'The demonstration has reached its daily chat limit. Course browsing, the skills challenge and human-help enquiries remain available.'}, 429)(scope, receive, protected_send)
            async def buffered_receive():
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            receive = buffered_receive
        await self.app(scope, receive, protected_send)


class WebsiteFiles(StaticFiles):
    async def get_response(self, path, scope):
        if path == 'api' or path.startswith('api/'):
            raise HTTPException(404, 'API route not found')
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            # Client-side routes only; missing JS/images must remain real 404s.
            if exc.status_code != 404 or '.' in path.rsplit('/', 1)[-1]:
                raise
            return await super().get_response('index.html', scope)
