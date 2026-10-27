"""Real polling scheduler. Server-side checks are atomic and idempotent.
No email provider: scheduled items enter the local outbox only.
"""
import os,time,logging
import httpx
logging.basicConfig(level=logging.INFO)
url=os.getenv('BACKEND_URL','http://127.0.0.1:8000')
while True:
    try:
        r=httpx.post(url+'/api/staff/reminders/run',headers={'Authorization':'Bearer '+os.environ['STAFF_TOKEN']},timeout=15)
        r.raise_for_status()
        logging.info('Reminder tick: %s',r.json())
    except (httpx.HTTPError,KeyError) as exc:
        logging.warning('Reminder tick failed: %s',type(exc).__name__)
    time.sleep(30)
