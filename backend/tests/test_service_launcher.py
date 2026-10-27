"""Regression checks for occupied ports and orphaned service groups."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('smartpath_launcher',Path(__file__).resolve().parents[2]/'scripts/run_services.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)

def test_occupied_port_prevents_any_service_spawn(monkeypatch):
    monkeypatch.setattr(launcher,'check_ports',lambda:False)
    def unexpected(*a,**kw):raise AssertionError('Do not spawn when a port is occupied')
    monkeypatch.setattr(launcher.subprocess,'Popen',unexpected)
    assert launcher.main()==1

def test_service_failure_stops_whole_process_groups(tmp_path,monkeypatch):
    killed=[];created=[]
    class Child:
        def __init__(self):self.pid=100+len(created);self.returncode=1 if not created else None;created.append(self)
        def poll(self):return self.returncode
        def wait(self,timeout=None):return 0
    monkeypatch.setattr(launcher,'ROOT',tmp_path)
    monkeypatch.setattr(launcher,'check_ports',lambda:True)
    monkeypatch.setattr(launcher.signal,'signal',lambda *a:None)
    monkeypatch.setattr(launcher.subprocess,'Popen',lambda *a,**kw:Child())
    monkeypatch.setattr(launcher.os,'killpg',lambda pid,sig:killed.append(pid))
    assert launcher.main()==1
    assert len(created)==3
    assert set(killed)=={c.pid for c in created}


def test_actual_listener_is_rejected():
    import socket
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        server.bind(('127.0.0.1',0));server.listen()
        assert launcher.check_ports((server.getsockname()[1],)) is False

def test_recently_closed_connection_does_not_block_restart():
    import socket
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        server.bind(('127.0.0.1',0));port=server.getsockname()[1];server.listen()
        with socket.create_connection(('127.0.0.1',port),timeout=2) as client:
            conn,_=server.accept();conn.settimeout(2)
            conn.shutdown(socket.SHUT_WR)
            assert client.recv(1)==b''
            client.shutdown(socket.SHUT_WR)
            conn.recv(1);conn.close()
    assert launcher.check_ports((port,)) is True
