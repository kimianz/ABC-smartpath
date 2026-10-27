"""SQLite document storage; each write transaction is serialized and durable."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock, local

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        self.lock = RLock()
        self.local = local()
        with self.connection() as c:
            c.execute('CREATE TABLE IF NOT EXISTS objects (kind TEXT NOT NULL,id TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(kind,id))')
    @contextmanager
    def transaction(self):
        with self.lock:
            if getattr(self.local, "connection", None) is not None:
                yield
                return
            c = sqlite3.connect(self.path, timeout=20)
            self.local.connection = c
            try:
                c.execute("BEGIN IMMEDIATE")
                yield
                c.commit()
            except Exception:
                c.rollback()
                raise
            finally:
                self.local.connection = None
                c.close()

    @contextmanager
    def connection(self):
        active = getattr(self.local, "connection", None)
        if active is not None:
            yield active
            return
        with self.lock:
            c=sqlite3.connect(self.path,timeout=20)
            try:
                c.execute('PRAGMA foreign_keys=ON')
                yield c
                c.commit()
            except Exception:
                c.rollback(); raise
            finally: c.close()
    def get(self,kind,id):
        with self.connection() as c:
            row=c.execute('SELECT body FROM objects WHERE kind=? AND id=?',(kind,id)).fetchone()
            return json.loads(row[0]) if row else None
    def all(self,kind):
        with self.connection() as c:
            return [json.loads(r[0]) for r in c.execute('SELECT body FROM objects WHERE kind=? ORDER BY rowid DESC',(kind,)).fetchall()]
    def put(self,kind,obj):
        with self.connection() as c:
            c.execute('INSERT INTO objects VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body',(kind,obj['id'],json.dumps(obj)))
        return obj
    def delete(self,kind,id):
        with self.connection() as c: c.execute('DELETE FROM objects WHERE kind=? AND id=?',(kind,id))

    def seed_catalogue(self,courses,faqs):
        """Persist approved fixture inventory with typed columns for exact facts.

        This prototype's read-only inventory is refreshed from its versioned
        fixture at startup; a production catalogue needs an authenticated editor.
        """
        scalar=['id','title','description','category','level','duration','price_gbp','capacity','availability']
        lists=['formats','prerequisites','required_skills','skills','audiences','dates']
        with self.transaction():
            with self.connection() as c:
                c.execute('CREATE TABLE IF NOT EXISTS courses (id TEXT PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,category TEXT NOT NULL,level TEXT NOT NULL,duration TEXT NOT NULL,price_gbp REAL,capacity INTEGER NOT NULL,availability TEXT NOT NULL,formats TEXT NOT NULL,prerequisites TEXT NOT NULL,required_skills TEXT NOT NULL,skills TEXT NOT NULL,audiences TEXT NOT NULL,dates TEXT NOT NULL)')
                c.execute('CREATE TABLE IF NOT EXISTS faqs (id TEXT PRIMARY KEY,text TEXT NOT NULL)')
                c.execute('DELETE FROM courses'); c.execute('DELETE FROM faqs')
                for course in courses:
                    values=[course[k] for k in scalar]+[json.dumps(course[k]) for k in lists]
                    c.execute('INSERT INTO courses VALUES ('+','.join('?' for _ in values)+')',values)
                c.executemany('INSERT INTO faqs VALUES (?,?)',[(f['id'],f['text']) for f in faqs])
    def courses(self):
        with self.connection() as c:
            c.row_factory=sqlite3.Row
            rows=c.execute('SELECT * FROM courses ORDER BY rowid').fetchall()
            result=[]
            for row in rows:
                obj=dict(row)
                for key in ['formats','prerequisites','required_skills','skills','audiences','dates']: obj[key]=json.loads(obj[key])
                result.append(obj)
            return result
    def faqs(self):
        with self.connection() as c:
            return [{'id':r[0],'text':r[1]} for r in c.execute('SELECT id,text FROM faqs ORDER BY rowid')]
