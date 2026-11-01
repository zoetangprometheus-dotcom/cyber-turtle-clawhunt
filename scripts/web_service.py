"""Loopback-only H5/claim service. Importing this module never starts paid work."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local/esp32'
THEMES = {'today', 'romance', 'career', 'friendship'}
ASSETS = {'index.html', 'style.css', 'app.js', 'data.js', 'history.js', 'scan.js', 'live.js'}
COOKIE = 'turtle_session'
TOKEN_RE = r'[A-Za-z0-9_-]{22}'
RID_RE = r'[0-9a-f]{32}'
GENERATION_ERROR = '生成失败，请手动重试；未自动再次调用'


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


class APIError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class Store:
    """One connection per operation; bridge and HTTP process may share this file."""
    def __init__(self, path=None, clock=time.time):
        self.path = Path(path) if path is not None else LOCAL / 'web-readings.sqlite3'
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.path.chmod(0o600)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS sessions (
                    hash TEXT PRIMARY KEY, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS readings (
                    id TEXT PRIMARY KEY, event TEXT UNIQUE NOT NULL,
                    hex TEXT NOT NULL, base TEXT, error TEXT,
                    token_hash TEXT UNIQUE NOT NULL, token_expires REAL NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0, owner_hash TEXT,
                    created REAL NOT NULL, claimed REAL);
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, reading_id TEXT NOT NULL REFERENCES readings(id),
                    kind TEXT NOT NULL, request_key TEXT NOT NULL, theme TEXT,
                    question TEXT, status TEXT NOT NULL, content TEXT, error TEXT,
                    created REAL NOT NULL, UNIQUE(reading_id, kind, request_key));
            ''')

    @contextmanager
    def connection(self, write=False):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            if write:
                db.execute('BEGIN IMMEDIATE')
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def create(self, event, hexagram):
        """Return (reading_id, one-time token), or None for an existing event."""
        canonical = {key: hexagram[key] for key in (
            'hexagram_id', 'name_zh', 'upper_trigram', 'lower_trigram', 'lines_bottom_to_top')}
        with self.connection(True) as db:
            if db.execute('SELECT 1 FROM readings WHERE event=?', (packed(event),)).fetchone():
                return None
            rid, token, now = secrets.token_hex(16), secrets.token_urlsafe(16), self.clock()
            db.execute('UPDATE readings SET revoked=1 WHERE owner_hash IS NULL')
            db.execute('''INSERT INTO readings
                (id,event,hex,token_hash,token_expires,created) VALUES (?,?,?,?,?,?)''',
                (rid, packed(event), packed(canonical), digest(token), now + 600, now))
        return rid, token

    def set_base(self, event, base):
        with self.connection(True) as db:
            changed = db.execute('UPDATE readings SET base=?,error=NULL WHERE event=? AND base IS NULL',
                                 (packed(base), packed(event))).rowcount
        return bool(changed)

    def fail(self, event, message):
        with self.connection(True) as db:
            return bool(db.execute('UPDATE readings SET error=? WHERE event=? AND base IS NULL',
                                   (str(message), packed(event))).rowcount)

    def fail_pending(self):
        """Explicit service-start recovery: never resubmit interrupted paid requests."""
        with self.connection(True) as db:
            return db.execute("UPDATE tasks SET status='failed',error=? WHERE status='pending'",
                              ('服务已重启，先前任务未自动重试；可手动重试',)).rowcount

    def claim(self, token, session=None):
        if not isinstance(token, str) or not re.fullmatch(TOKEN_RE, token):
            raise APIError(404, 'invalid', '扫码链接无效')
        now, existing_hash = self.clock(), digest(session) if session else None
        with self.connection(True) as db:
            row = db.execute('SELECT * FROM readings WHERE token_hash=?', (digest(token),)).fetchone()
            if row is None:
                raise APIError(404, 'invalid', '扫码链接无效')
            current = db.execute('SELECT * FROM sessions WHERE hash=?', (existing_hash,)).fetchone()
            valid = current is not None and current['expires'] > now
            if row['owner_hash']:
                if row['owner_hash'] != existing_hash:
                    raise APIError(403, 'claimed', '这张签已被其他浏览器领取')
                if not valid:
                    raise APIError(401, 'session', '会话已结束，可在本机历史中回看')
                return row['id'], session, current['expires']
            if row['revoked'] or row['token_expires'] <= now:
                raise APIError(410, 'expired', '二维码已过期，请重新摇动设备')
            if not valid:
                session = secrets.token_urlsafe(32)
                existing_hash = digest(session)
                expires = now + 1800
                db.execute('INSERT INTO sessions VALUES (?,?)', (existing_hash, expires))
            else:
                expires = current['expires']
            db.execute('UPDATE readings SET owner_hash=?,claimed=? WHERE id=?',
                       (existing_hash, now, row['id']))
            return row['id'], session, expires

    def _authorize(self, db, rid, session):
        owner = digest(session) if session else None
        found = db.execute('SELECT expires FROM sessions WHERE hash=?', (owner,)).fetchone()
        if not found or found['expires'] <= self.clock():
            raise APIError(401, 'session', '会话已结束，可在本机历史中回看')
        row = db.execute('SELECT * FROM readings WHERE id=?', (rid,)).fetchone()
        if not row or row['owner_hash'] != owner:
            raise APIError(403, 'session', '当前浏览器无权访问这张签')
        return row

    def task(self, rid, task_id, session):
        with self.connection() as db:
            self._authorize(db, rid, session)
            row = db.execute('SELECT * FROM tasks WHERE id=? AND reading_id=?', (task_id, rid)).fetchone()
            if not row:
                raise APIError(404, 'invalid', '任务不存在')
            return dict(row)

    def enqueue(self, rid, session, kind, request_key, theme=None, question=None, retry=False):
        with self.connection(True) as db:
            reading = self._authorize(db, rid, session)
            if reading['base'] is None:
                if reading['error']:
                    raise APIError(409, 'invalid', '基础签生成失败，请重新摇动设备')
                if kind == 'web':
                    return None, False
                raise APIError(409, 'invalid', '基础签仍在生成，请稍后再试')
            task = db.execute('SELECT * FROM tasks WHERE reading_id=? AND kind=? AND request_key=?',
                              (rid, kind, request_key)).fetchone()
            if task and (task['theme'] != theme or task['question'] != question):
                raise APIError(409, 'invalid', '请求编号已用于其他问题')
            if task and (task['status'] != 'failed' or not retry):
                return dict(task), False
            if not task and kind == 'question' and db.execute(
                    "SELECT COUNT(*) FROM tasks WHERE reading_id=? AND kind='question'", (rid,)).fetchone()[0] >= 8:
                raise APIError(429, 'busy', '这张签已达到八个问题的上限')
            if db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'").fetchone()[0] >= 4:
                raise APIError(429, 'busy', '正在处理的请求较多，请稍后再试')
            if task:
                task_id = task['id']
                db.execute("UPDATE tasks SET status='pending',error=NULL WHERE id=?", (task_id,))
            else:
                task_id = secrets.token_hex(16)
                db.execute('''INSERT INTO tasks
                    (id,reading_id,kind,request_key,theme,question,status,created)
                    VALUES (?,?,?,?,?,?,'pending',?)''',
                    (task_id, rid, kind, request_key, theme, question, self.clock()))
            return dict(db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()), True

    def task_input(self, task_id):
        with self.connection() as db:
            row = db.execute('''SELECT tasks.*,readings.hex,readings.base FROM tasks
                JOIN readings ON readings.id=tasks.reading_id WHERE tasks.id=?''', (task_id,)).fetchone()
            return dict(row) if row else None

    def finish(self, task_id, content=None, error=None):
        with self.connection(True) as db:
            db.execute("UPDATE tasks SET status=?,content=?,error=? WHERE id=? AND status='pending'",
                       ('failed' if error else 'succeeded', packed(content) if content is not None else None,
                        error, task_id))

    def reading(self, rid, session):
        with self.connection() as db:
            row = self._authorize(db, rid, session)
            result = {'reading_id': rid, 'status': 'pending'}
            if row['base'] is None:
                if row['error']:
                    result.update(status='failed', error='基础签生成失败，请重新摇动设备')
                return result
            tasks = db.execute('SELECT * FROM tasks WHERE reading_id=? ORDER BY created,id', (rid,)).fetchall()
            web = next((t for t in tasks if t['kind'] == 'web'), None)
            if not web or web['status'] == 'pending':
                return result
            if web['status'] == 'failed':
                return {**result, 'status': 'failed', 'error': web['error']}
            scanned = iso(row['claimed'])
            result.update(status='ready', record={
                'id': rid, 'hex': json.loads(row['hex']), 'base': json.loads(row['base']),
                'web': json.loads(web['content']),
                'deep': {t['theme']: json.loads(t['content']) for t in tasks
                         if t['kind'] == 'deep' and t['status'] == 'succeeded'},
                'questions': [json.loads(t['content']) for t in tasks
                              if t['kind'] == 'question' and t['status'] == 'succeeded'],
                'selected': '', 'content_origin': 'ai', 'scanned_at': scanned, 'day': scanned[:10]})
            return result


def task_envelope(task):
    result = {'reading_id': task['reading_id'], 'task_id': task['id'], 'status': task['status']}
    if task['theme']:
        result['theme'] = task['theme']
    if task['kind'] == 'question':
        result['question_id'] = task['id']
    if task['status'] == 'succeeded':
        result['content'] = json.loads(task['content'])
    elif task['status'] == 'failed':
        result['error'] = task['error']
    return result


def generate_extension(hexagram, base, **kwargs):
    # Delayed import: Store is also imported by the device bridge.
    from ai_client import generate_extension as generate
    return generate(hexagram, base, **kwargs)


class WebApplication:
    def __init__(self, store, generate=None, public_config=None, public_base_url=None, static_dir=None):
        self.store = store
        self.generate = generate or generate_extension
        self.public_config = Path(public_config) if public_config is not None else LOCAL / 'web-public.json'
        self.public_base_url = public_base_url
        self.static_dir = Path(static_dir) if static_dir is not None else ROOT / 'h5'
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='web-reading')

    def close(self):
        self.executor.shutdown(wait=True)

    def origins(self, port):
        origins = {'http://127.0.0.1:%d' % port}
        public = self.public_base_url
        if public is None:
            try:
                public = json.loads(self.public_config.read_text()).get('base_url', '')
            except (OSError, ValueError, AttributeError):
                public = ''
        if isinstance(public, str):
            parsed = urlsplit(public)
            if (parsed.scheme == 'https' and parsed.hostname and parsed.hostname.endswith('.trycloudflare.com')
                    and not parsed.username and not parsed.password and parsed.path in ('', '/')
                    and not parsed.query and not parsed.fragment and parsed.netloc == parsed.hostname):
                origins.add('https://' + parsed.hostname)
        return origins

    def queue(self, rid, session, kind, key, **kwargs):
        task, created = self.store.enqueue(rid, session, kind, key, **kwargs)
        if created:
            try:
                self.executor.submit(self.run_task, task['id'])
            except RuntimeError:
                self.store.finish(task['id'], error=GENERATION_ERROR)
        return task

    def ensure_web(self, rid, session, retry=False):
        self.queue(rid, session, 'web', 'web', retry=retry)

    def run_task(self, task_id):
        task = self.store.task_input(task_id)
        if not task or task['status'] != 'pending':
            return
        try:
            result = self.generate(json.loads(task['hex']), json.loads(task['base']),
                                   theme=task['theme'], question=task['question'])
            fields = {'meaning', 'reflection', 'action'}
            if task['kind'] != 'question':
                fields.add('title')
            if not isinstance(result, dict) or set(result) != fields or not all(
                    isinstance(result[k], str) and result[k].strip() for k in fields):
                raise ValueError('Invalid output')
            if task['kind'] == 'question':
                result = {'id': task['id'], 'question': task['question'], 'answer': result,
                          'created_at': iso(task['created']), 'content_origin': 'ai'}
            self.store.finish(task_id, content=result)
        except Exception:
            # Never expose provider messages, keys or user content in responses/logs.
            self.store.finish(task_id, error=GENERATION_ERROR)


class Handler(BaseHTTPRequestHandler):
    server_version = 'CyberTurtle'
    sys_version = ''

    def log_message(self, format, *args):
        pass  # URLs contain one-time secrets. Do not use access logs.

    def send_error(self, code, message=None, explain=None):
        self.reply(code, {'error': '请求无效', 'code': 'invalid'})

    def reply(self, status, body, content_type='application/json; charset=utf-8', cookie=None, location=None):
        data = packed(body).encode() if isinstance(body, dict) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'")
        if cookie:
            self.send_header('Set-Cookie', cookie)
        if location:
            self.send_header('Location', location)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def security(self):
        origins = self.server.app.origins(self.server.server_port)
        hosts = self.headers.get_all('Host', [])
        if len(hosts) != 1:
            raise APIError(403, 'invalid', '访问地址不受支持')
        matching = {origin for origin in origins if urlsplit(origin).netloc == hosts[0]}
        if not matching:
            raise APIError(403, 'invalid', '访问地址不受支持')
        if self.command == 'POST':
            if self.headers.get('Origin') not in matching or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise APIError(403, 'invalid', '请从同一网页提交请求')
        return next(iter(matching)).startswith('https:')

    def session(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            value = cookie[COOKIE].value if COOKIE in cookie else None
            return value if value and re.fullmatch(r'[A-Za-z0-9_-]{43}', value) else None
        except Exception:
            return None

    def body(self):
        try:
            size = int(self.headers.get('Content-Length', '-1'))
            if (not 0 < size <= 4096 or self.headers.get('Transfer-Encoding')
                    or self.headers.get_content_type() != 'application/json'):
                raise ValueError()
            value = json.loads(self.rfile.read(size))
            if not isinstance(value, dict):
                raise ValueError()
            return value
        except (ValueError, UnicodeDecodeError):
            raise APIError(400, 'invalid', '请求内容格式无效') from None

    def dispatch(self):
        secure = self.security()
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc:
            raise APIError(400, 'invalid', '请求路径无效')
        path, app, session = parsed.path, self.server.app, self.session()
        if self.command == 'POST':
            body = self.body()
            if path == '/api/claim':
                if set(body) != {'token'}:
                    raise APIError(400, 'invalid', '请求内容格式无效')
                rid, session, expires = app.store.claim(body['token'], session)
                # Set the cookie even if the generation queue is full after a successful claim.
                cookie = '%s=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=%d%s' % (
                    COOKIE, session, max(0, int(expires-app.store.clock())), '; Secure' if secure else '')
                try:
                    if app.store.reading(rid, session)['status'] != 'failed':
                        app.ensure_web(rid, session)
                    result = app.store.reading(rid, session)
                except APIError as error:
                    self.reply(error.status, {'error': error.message, 'code': error.code, 'reading_id': rid}, cookie=cookie)
                    return
                self.reply(200, result, cookie=cookie)
                return
            route = re.fullmatch(r'/api/readings/('+RID_RE+r')/(retry|deep-reading|questions)', path)
            if not route:
                raise APIError(404, 'invalid', '接口不存在')
            rid, operation = route.groups()
            if operation == 'retry':
                if body:
                    raise APIError(400, 'invalid', '请求内容格式无效')
                app.ensure_web(rid, session, retry=True)
                self.reply(200, app.store.reading(rid, session))
                return
            if operation == 'deep-reading':
                if set(body) != {'theme'} or not isinstance(body['theme'], str) or body['theme'] not in THEMES:
                    raise APIError(400, 'invalid', '请选择有效主题')
                task = app.queue(rid, session, 'deep', body['theme'], theme=body['theme'], retry=True)
            else:
                if not {'request_id', 'question'} <= set(body) or set(body) - {'request_id', 'question', 'theme'}:
                    raise APIError(400, 'invalid', '请求内容格式无效')
                key, question, theme = body['request_id'], body['question'], body.get('theme')
                if (not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', key)
                        or not isinstance(question, str) or not 1 <= len(question.strip()) <= 200
                        or (theme is not None and (not isinstance(theme, str) or theme not in THEMES))):
                    raise APIError(400, 'invalid', '请填写一至二百字的问题及有效请求编号')
                task = app.queue(rid, session, 'question', key, theme=theme, question=question.strip(), retry=True)
            self.reply(200, task_envelope(task))
            return
        if self.command not in ('GET', 'HEAD'):
            raise APIError(405, 'invalid', '请求方法不受支持')
        if path == '/api/health':
            self.reply(200, {'service': 'cyber-turtle-web'})
            return
        route = re.fullmatch(r'/api/readings/('+RID_RE+r')(?:/tasks/('+RID_RE+r'))?', path)
        if route:
            rid, task_id = route.groups()
            if task_id:
                result = task_envelope(app.store.task(rid, task_id, session))
            else:
                result = app.store.reading(rid, session)
                if result['status'] == 'pending':
                    app.ensure_web(rid, session)
                    result = app.store.reading(rid, session)
            self.reply(200, result)
            return
        if path == '/':
            self.reply(200, '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>赛博龟壳</title><body><main><h1>请扫描设备二维码</h1><p>摇动设备后，扫描屏幕上的二维码领取本次签文</p><a href="/history/">查看已保存历史</a></main></body></html>'.encode(), 'text/html; charset=utf-8')
            return
        prefix = r'(?:r/'+TOKEN_RE+r'|s/'+RID_RE+r'|history)'
        if re.fullmatch('/'+prefix, path):
            self.reply(308, b'', location=path + '/')
            return
        if re.fullmatch('/'+prefix+r'/?', path):
            asset = 'index.html'
        else:
            match = re.fullmatch(r'/(?:'+prefix+r'/)?([^/]+)', path)
            asset = match.group(1) if match else None
        if asset not in ASSETS:
            raise APIError(404, 'invalid', '页面不存在')
        try:
            data = (app.static_dir / asset).read_bytes()
        except OSError:
            raise APIError(404, 'invalid', '页面不存在') from None
        content_type = 'text/html; charset=utf-8' if asset.endswith('.html') else (
            'text/css; charset=utf-8' if asset.endswith('.css') else 'text/javascript; charset=utf-8')
        self.reply(200, data, content_type)

    def handle_request(self):
        try:
            self.dispatch()
        except APIError as error:
            self.reply(error.status, {'error': error.message, 'code': error.code})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.reply(503, {'error': '服务暂时不可用，请稍后再试', 'code': 'network'})

    do_GET = do_POST = do_HEAD = do_OPTIONS = do_PUT = do_DELETE = handle_request


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def handle_error(self, request, client_address):
        pass


def make_server(app, port=8768):
    server = Server(('127.0.0.1', port), Handler)
    server.app = app
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    store = Store()
    app = WebApplication(store)
    server = make_server(app, args.port)
    # Bind first: a second process must not mark a running service's tasks failed.
    store.fail_pending()
    print('Cyber Turtle web service listening on 127.0.0.1:%d' % server.server_port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()


if __name__ == '__main__':
    main()
