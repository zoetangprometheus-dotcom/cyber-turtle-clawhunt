"""Temporary-database/mock-model tests; never reads the local device configuration."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import http.client
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('web_service_test_target', ROOT / 'scripts/web_service.py')
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)
HEX = {'hexagram_id': 1, 'name_zh': '乾', 'upper_trigram': '乾', 'lower_trigram': '乾',
       'lines_bottom_to_top': [1, 1, 1, 1, 1, 1]}
BASE = {'title': '稳步向前', 'message': '把注意力放回当前能够看见的小事，给自己一点观察的时间。', 'action': '先写下今天想完成的一件小事。'}
DEEP = {'title': '把目光放回眼前', 'meaning': '慢慢观察。' * 20,
        'reflection': '看见变化。' * 20, 'action': '为接下来的一小步留出十分钟。'}
ANSWER = {'meaning': '沿用此卦观察。', 'reflection': '把问题拆成小事。', 'action': '写下一个可以尝试的小步骤。'}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = [1800000000.0]
        self.store = web.Store(self.root / 'readings.sqlite3', clock=lambda: self.now[0])
        self.calls = []
        self.calls_lock = threading.Lock()
        self.gate = None
        self.model_fail = False
        self.assets = self.root / 'h5'
        self.assets.mkdir()
        for name in web.ASSETS:
            (self.assets / name).write_text('fixture-' + name)
        self.public = self.root / 'public.json'
        self.app = web.WebApplication(self.store, generate=self.model,
            public_config=self.public, static_dir=self.assets)
        self.server = web.make_server(self.app, 0)
        self.port = self.server.server_port
        self.origin = 'http://127.0.0.1:%d' % self.port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        if self.gate:
            self.gate.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.app.close()
        self.temp.cleanup()

    def model(self, hexagram, base, theme=None, question=None):
        with self.calls_lock:
            self.calls.append((hexagram, base, theme, question))
        if self.gate:
            self.gate.wait(5)
        if self.model_fail:
            raise ValueError('PRIVATE provider api key or user content')
        return dict(ANSWER if question else DEEP)

    def request(self, method, path, body=None, cookie=None, origin=True, host=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        request_headers = {'Host': host or '127.0.0.1:%d' % self.port}
        if cookie:
            request_headers['Cookie'] = cookie
        if origin:
            request_headers['Origin'] = self.origin if origin is True else origin
        if body is not None:
            request_headers['Content-Type'] = 'application/json'
        request_headers.update(headers or {})
        conn.request(method, path, json.dumps(body) if body is not None else None, request_headers)
        response = conn.getresponse()
        raw = response.read().decode()
        status, response_headers = response.status, dict(response.getheaders())
        conn.close()
        return status, json.loads(raw) if response_headers.get('Content-Type', '').startswith('application/json') else raw, response_headers

    def reading(self, event='test', base=True):
        rid, token = self.store.create(event, HEX)
        if base:
            self.store.set_base(event, BASE)
        return rid, token

    def claim(self, token, cookie=None):
        status, value, headers = self.request('POST', '/api/claim', {'token': token}, cookie)
        self.assertEqual(status, 200, value)
        return value, headers['Set-Cookie'].split(';', 1)[0]

    def wait_reading(self, rid, cookie):
        for _ in range(200):
            status, value, _ = self.request('GET', '/api/readings/' + rid, cookie=cookie)
            self.assertEqual(status, 200, value)
            if value['status'] != 'pending':
                return value
            time.sleep(.01)
        self.fail('Reading did not finish')

    def wait_task(self, rid, task_id, cookie):
        for _ in range(200):
            status, value, _ = self.request('GET', '/api/readings/%s/tasks/%s' % (rid, task_id), cookie=cookie)
            self.assertEqual(status, 200, value)
            if value['status'] != 'pending':
                return value
            time.sleep(.01)
        self.fail('Task did not finish')

    def test_atomic_claim_only_one_browser(self):
        rid, token = self.reading(base=False)
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: self.request('POST', '/api/claim', {'token': token}), range(8)))
        self.assertEqual(sorted(r[0] for r in responses), [200] + [403] * 7)
        success = next(r for r in responses if r[0] == 200)
        cookie = success[2]['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(self.claim(token, cookie)[0]['reading_id'], rid)
        self.assertEqual(len(self.calls), 0)
        self.assertIn('HttpOnly', success[2]['Set-Cookie'])
        self.assertIn('SameSite=Strict', success[2]['Set-Cookie'])

    def test_event_idempotency_expiry_revocation_and_session(self):
        rid, token = self.reading(base=False)
        self.assertIsNone(self.store.create('test', HEX))
        self.assertEqual(self.request('POST', '/api/claim', {'token': 'x' * 22})[0], 404)
        self.reading('new', base=False)
        self.assertEqual(self.request('POST', '/api/claim', {'token': token})[0], 410)
        rid2, token2 = self.reading('expiring', base=False)
        self.now[0] += 600
        self.assertEqual(self.request('POST', '/api/claim', {'token': token2})[0], 410)
        rid3, token3 = self.reading('claimed', base=False)
        _, cookie = self.claim(token3)
        self.now[0] += 601
        self.assertEqual(self.claim(token3, cookie)[0]['reading_id'], rid3)
        self.now[0] += 1200
        self.assertEqual(self.request('GET', '/api/readings/' + rid3, cookie=cookie)[0], 401)
        self.assertEqual(self.request('POST', '/api/claim', {'token': token3}, cookie)[0], 401)

    def test_owner_checks_all_paid_routes_and_tasks(self):
        rid, token = self.reading()
        _, owner = self.claim(token)
        self.wait_reading(rid, owner)
        other_rid, other_token = self.reading('other', base=False)
        _, stranger = self.claim(other_token)
        count = len(self.calls)
        for method, suffix, body in [
            ('GET', '', None), ('POST', '/retry', {}),
            ('POST', '/deep-reading', {'theme': 'today'}),
            ('POST', '/questions', {'request_id': str(uuid.uuid4()), 'question': '测试'})]:
            self.assertEqual(self.request(method, '/api/readings/' + rid + suffix, body, stranger)[0], 403)
            self.assertEqual(self.request(method, '/api/readings/' + rid + suffix, body)[0], 401)
        status, task, _ = self.request('POST', '/api/readings/' + rid + '/deep-reading', {'theme': 'today'}, owner)
        self.assertEqual(status, 200)
        wrong = self.request('GET', '/api/readings/%s/tasks/%s' % (other_rid, task['task_id']), cookie=stranger)
        self.assertEqual(wrong[0], 404)
        self.assertLessEqual(len(self.calls), count + 1)

    def test_static_allowlist_and_csrf(self):
        rid, token = self.reading(base=False)
        for path in ['/', '/api/health', '/r/' + token + '/',
                     '/s/' + rid + '/', '/history/', '/style.css',
                     '/r/' + token + '/style.css', '/s/' + rid + '/app.js', '/history/live.js']:
            self.assertEqual(self.request('GET', path)[0], 200, path)
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.request('GET', '/r/' + token)
        response = conn.getresponse()
        self.assertEqual(response.status, 308)
        self.assertEqual(response.getheader('Location'), '/r/' + token + '/')
        response.read()
        conn.close()
        for path in ['/.local/esp32/ai-config.json', '/README.md', '/scripts/web_service.py',
                     '/../AGENTS.md', '/%2e%2e/AGENTS.md', '/r/' + token + '/../../README.md',
                     '/r/' + token + '/not-allowed.js', '/r/bad/', '/s/bad/']:
            self.assertEqual(self.request('GET', path)[0], 404, path)
        self.assertEqual(self.request('GET', '/api/health', host='evil.invalid')[0], 403)
        for origin in [False, 'https://evil.invalid', 'null']:
            self.assertEqual(self.request('POST', '/api/claim', {'token': token}, origin=origin)[0], 403)
        self.assertEqual(self.request('POST', '/api/claim', {'token': token},
                                     headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.request('OPTIONS', '/api/claim')[0], 405)
        self.assertEqual(self.calls, [])

    def test_public_origin_reloads_and_sets_secure_cookie(self):
        rid, token = self.reading(base=False)
        domain = 'fixture.trycloudflare.com'
        self.assertEqual(self.request('GET', '/api/health', host=domain)[0], 403)
        self.public.write_text(json.dumps({'base_url': 'https://' + domain}))
        status, result, headers = self.request('POST', '/api/claim', {'token': token},
                                              host=domain, origin='https://' + domain)
        self.assertEqual(status, 200)
        self.assertIn('; Secure', headers['Set-Cookie'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(self.request('POST', '/api/claim', {'token': token}, host=domain)[0], 403)

    def test_record_immutable_and_tokens_absent_after_reopen(self):
        rid, token = self.reading()
        _, cookie = self.claim(token)
        ready = self.wait_reading(rid, cookie)
        other = web.Store(self.store.path, clock=lambda: self.now[0])
        self.assertFalse(other.set_base('test', {**BASE, 'title': '不可覆盖'}))
        self.assertFalse(other.fail('test', 'cannot overwrite'))
        self.assertEqual(other.reading(rid, cookie.split('=', 1)[1]), ready)
        record = ready['record']
        self.assertEqual(record['base'], BASE)
        self.assertEqual(record['hex'], HEX)
        self.assertEqual(record['content_origin'], 'ai')
        self.assertRegex(record['scanned_at'], r'\.\d{3}Z$')
        self.assertNotIn(token, json.dumps(ready))
        self.assertNotIn(cookie.split('=', 1)[1], json.dumps(ready))
        self.assertNotIn(token.encode(), self.store.path.read_bytes())
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_themes_questions_idempotent_and_bounded(self):
        rid, token = self.reading()
        _, cookie = self.claim(token)
        self.wait_reading(rid, cookie)
        route = '/api/readings/' + rid
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.request('POST', route + '/deep-reading', {'theme': 'today'}, cookie), range(6)))
        self.assertTrue(all(r[0] == 200 for r in results))
        self.assertEqual(len({r[1]['task_id'] for r in results}), 1)
        self.wait_task(rid, results[0][1]['task_id'], cookie)
        self.assertEqual(sum(call[2] == 'today' for call in self.calls), 1)
        key = str(uuid.uuid4())
        body = {'request_id': key, 'question': '  下一步怎么做？  ', 'theme': 'career'}
        first = self.request('POST', route + '/questions', body, cookie)[1]
        final = self.wait_task(rid, first['task_id'], cookie)
        self.assertEqual(final['content']['question'], '下一步怎么做？')
        self.assertEqual(final['content']['answer'], ANSWER)
        second = self.request('POST', route + '/questions', body, cookie)[1]
        self.assertEqual(first['task_id'], second['task_id'])
        self.assertEqual(self.request('POST', route + '/questions', {**body, 'question': '另一个问题'}, cookie)[0], 409)
        self.assertEqual(self.request('POST', route + '/questions', {**body, 'theme': 'today'}, cookie)[0], 409)
        for n in range(7):
            result = self.request('POST', route + '/questions', {'request_id': str(uuid.uuid4()), 'question': str(n)}, cookie)
            self.assertEqual(result[0], 200)
            self.wait_task(rid, result[1]['task_id'], cookie)
        self.assertEqual(self.request('POST', route + '/questions', {'request_id': str(uuid.uuid4()), 'question': '第九问'}, cookie)[0], 429)
        record = self.wait_reading(rid, cookie)['record']
        self.assertEqual(len(record['questions']), 8)
        self.assertEqual(record['deep']['today'], DEEP)

    def test_failed_web_never_retries_without_explicit_post(self):
        self.model_fail = True
        rid, token = self.reading()
        _, cookie = self.claim(token)
        failed = self.wait_reading(rid, cookie)
        self.assertEqual(failed['status'], 'failed')
        self.assertNotIn('PRIVATE', failed['error'])
        for _ in range(3):
            self.claim(token, cookie)
            self.wait_reading(rid, cookie)
        self.assertEqual(len(self.calls), 1)
        self.model_fail = False
        self.assertEqual(self.request('POST', '/api/readings/' + rid + '/retry', {}, cookie)[0], 200)
        self.assertEqual(self.wait_reading(rid, cookie)['status'], 'ready')
        self.assertEqual(len(self.calls), 2)
        self.request('POST', '/api/readings/' + rid + '/retry', {}, cookie)
        self.assertEqual(len(self.calls), 2)

    def test_failed_task_explicit_retry_and_base_failure(self):
        rid, token = self.reading()
        _, cookie = self.claim(token)
        self.wait_reading(rid, cookie)
        self.model_fail = True
        route = '/api/readings/' + rid + '/deep-reading'
        task = self.request('POST', route, {'theme': 'romance'}, cookie)[1]
        result = self.wait_task(rid, task['task_id'], cookie)
        self.assertEqual(result['status'], 'failed')
        for _ in range(3):
            self.wait_task(rid, task['task_id'], cookie)
        self.assertEqual(len(self.calls), 2)
        self.model_fail = False
        retry = self.request('POST', route, {'theme': 'romance'}, cookie)[1]
        self.assertEqual(retry['task_id'], task['task_id'])
        self.assertEqual(self.wait_task(rid, task['task_id'], cookie)['status'], 'succeeded')
        rid2, token2 = self.reading('base-fail', base=False)
        self.store.fail('base-fail', 'PRIVATE base failure')
        result, cookie2 = self.claim(token2)
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('PRIVATE', result['error'])
        self.assertEqual(self.request('POST', '/api/readings/' + rid2 + '/retry', {}, cookie2)[0], 409)

    def test_pending_capacity_and_two_workers(self):
        rid, token = self.reading()
        _, cookie = self.claim(token)
        self.wait_reading(rid, cookie)
        self.gate = threading.Event()
        tasks = []
        for theme in ['today', 'romance', 'career', 'friendship']:
            response = self.request('POST', '/api/readings/' + rid + '/deep-reading', {'theme': theme}, cookie)
            self.assertEqual(response[0], 200)
            tasks.append(response[1]['task_id'])
        response = self.request('POST', '/api/readings/' + rid + '/questions',
                                {'request_id': str(uuid.uuid4()), 'question': '第五个任务'}, cookie)
        self.assertEqual(response[0], 429)
        self.assertEqual(response[1]['code'], 'busy')
        self.assertLessEqual(len(self.calls), 3)  # one completed web + at most two running.
        self.gate.set()
        for task_id in tasks:
            self.assertEqual(self.wait_task(rid, task_id, cookie)['status'], 'succeeded')

    def test_reopen_does_not_restart_pending_work(self):
        rid, token = self.reading()
        rid, session, _ = self.store.claim(token)
        task, created = self.store.enqueue(rid, session, 'web', 'web')
        self.assertTrue(created)
        reopened = web.Store(self.store.path, clock=lambda: self.now[0])
        self.assertEqual(reopened.task(rid, task['id'], session)['status'], 'pending')
        self.assertEqual(self.calls, [])
        self.assertEqual(reopened.fail_pending(), 1)
        self.assertEqual(reopened.task(rid, task['id'], session)['status'], 'failed')
        self.assertEqual(self.calls, [])

    def test_input_validation_and_no_url_content_logs(self):
        rid, token = self.reading(base=False)
        output = io.StringIO()
        with contextlib.redirect_stderr(output), contextlib.redirect_stdout(output):
            self.request('GET', '/r/' + token + '/')
            _, cookie = self.claim(token)
            route = '/api/readings/' + rid + '/questions'
            for question in ['', '   ', '字' * 201, 5, ['question']]:
                self.assertEqual(self.request('POST', route, {'request_id': str(uuid.uuid4()), 'question': question}, cookie)[0], 400)
            self.assertEqual(self.request('POST', '/api/readings/' + rid + '/deep-reading', {'theme': []}, cookie)[0], 400)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
