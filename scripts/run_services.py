"""Start services together, reserve fixed ports, and stop complete process groups.
Only localhost listeners; configuration is inherited from start.sh.
"""
import errno,os,signal,socket,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def check_ports(ports=(8000,5173)):
    for port in ports:
        with socket.socket() as sock:
            # Match the servers: reuse recently closed TCP connections, never an active listener.
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            try:sock.bind(('127.0.0.1',port))
            except OSError as exc:
                if exc.errno==errno.EADDRINUSE:
                    print(f'Port {port} is already in use. Stop the other SmartPath terminal with Control+C before starting again.',flush=True)
                else:
                    print(f'Cannot check port {port}: {exc.strerror} (errno {exc.errno}).',flush=True)
                return False
    return True

def main():
    if not check_ports():return 1
    logs=ROOT/'logs';logs.mkdir(exist_ok=True)
    python=str(ROOT/'.venv/bin/python')
    specifications=[('backend',[python,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],ROOT/'backend'),
       ('frontend',['npm','run','dev','--','--host','127.0.0.1','--port','5173','--strictPort'],ROOT/'frontend'),
       ('reminders',[python,str(ROOT/'scripts/reminder_worker.py')],ROOT)]
    children=[];handles=[]
    def stop(signum=None,frame=None):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    try:
        for name,cmd,cwd in specifications:
            log=(logs/(name+'.log')).open('a',buffering=1);handles.append(log)
            log.write('\n--- SmartPath service start ---\n')
            children.append((name,subprocess.Popen(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)))
        print('SmartPath is starting: http://127.0.0.1:5173\nLeave this terminal open. Check /api/health before live AI.\nStaff token stays in .env. Logs: logs/. Stop with Control+C.',flush=True)
        while True:
            for name,child in children:
                if child.poll() is not None:
                    print(f'{name.capitalize()} stopped (exit {child.returncode}). Read logs/{name}.log.',flush=True)
                    return 1
            time.sleep(.5)
    except KeyboardInterrupt:
        print('\nStopping SmartPath services...',flush=True)
        return 0
    finally:
        for _,child in children:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        deadline=time.monotonic()+5
        for _,child in children:
            try:child.wait(timeout=max(.1,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait()
        for handle in handles:handle.close()
if __name__=='__main__':sys.exit(main())
