"""Loopback-only AI configuration and preview window. Never serves secrets."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import sqlite3
import threading
import urllib.request
import webbrowser

import ai_client as ai
import receipt_layout

PORT = 8767
ORIGIN = 'http://127.0.0.1:%d' % PORT
HEXAGRAMS = {h['hexagram_id']: h for h in json.loads((ai.ROOT / 'data/hexagrams.json').read_text())}
TOKEN = secrets.token_urlsafe(32)
TEST_LOCK = threading.Lock()


def latest_job():
    path = ai.LOCAL / 'print-bridge.sqlite3'
    if not path.exists(): return None
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        columns = {row[1] for row in db.execute('PRAGMA table_info(jobs)')}
        if not {'base_json', 'error'} <= columns: return None
        row = db.execute('SELECT event,hexagram,status,base_json,error FROM jobs ORDER BY rowid DESC LIMIT 1').fetchone()
    if not row: return None
    result = dict(row)
    result['base'] = json.loads(result.pop('base_json') or 'null')
    result['hexagram_name'] = HEXAGRAMS[result['hexagram']]['name_zh']
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # No URLs, credentials, or request bodies in access logs.

    def reply(self, status, value, html=False):
        body = value.encode() if html else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'nonce-%s'; style-src 'nonce-%s'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'" % (TOKEN, TOKEN))
        self.end_headers(); self.wfile.write(body)

    def valid_host(self):
        return self.headers.get('Host') == '127.0.0.1:%d' % self.server.server_port

    def do_GET(self):
        if not self.valid_host(): return self.reply(403, {'error': '只允许本机访问'})
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            return self.reply(403, {'error': '禁止跨站访问'})
        try:
            if self.path == '/':
                return self.reply(200, (ai.ROOT / 'scripts/ai-panel.html').read_text().replace('__NONCE__', TOKEN), html=True)
            if self.path == '/api/health': return self.reply(200, {'service': 'cyber-turtle-ai-panel'})
            if self.path == '/api/config': return self.reply(200, ai.public_config())
            if self.path == '/api/hexagrams':
                return self.reply(200, [{'id': h['hexagram_id'], 'name': h['name_zh'], **{k: h[k] for k in ('name_zh', 'upper_trigram', 'lower_trigram', 'lines_bottom_to_top')}} for h in HEXAGRAMS.values()])
            if self.path == '/api/status': return self.reply(200, {'job': latest_job()})
            if self.path == '/api/sample':
                base = json.loads((ai.ROOT / 'data/content-examples.json').read_text())['base_reading']
                return self.reply(200, {'base': base, 'hexagram': HEXAGRAMS[1]})
            self.reply(404, {'error': '没有这个页面'})
        except (ai.AIError, OSError, ValueError, sqlite3.Error):
            self.reply(500, {'error': '本机状态暂不可读，请检查配置或中转程序'})

    def do_POST(self):
        origin = 'http://127.0.0.1:%d' % self.server.server_port
        if (not self.valid_host() or self.headers.get('Origin') != origin or
                not secrets.compare_digest(self.headers.get('X-Panel-Token', ''), TOKEN)):
            return self.reply(403, {'error': '请求来源无效，请重新打开本机窗口'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16384 or self.headers.get_content_type() != 'application/json':
                return self.reply(400, {'error': '请求格式无效'})
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict): raise ValueError()
            if self.path == '/api/config':
                return self.reply(200, ai.public_config(ai.save_config(data)))
            if self.path == '/api/preview':
                number = data.get('hexagram_id')
                if type(number) is not int or number not in HEXAGRAMS: raise ValueError()
                base = ai.validate_reading(data['base']) if data.get('base') is not None else None
                image = receipt_layout.render(HEXAGRAMS[number], base, data.get('origin', 'ai'))
                return self.reply(200, {'image': receipt_layout.png_data(image)})
            if self.path == '/api/test':
                number = data.get('hexagram_id', 1)
                if type(number) is not int or number not in HEXAGRAMS: raise ValueError()
                if not TEST_LOCK.acquire(blocking=False):
                    return self.reply(409, {'error': '已有测试正在生成，请稍候'})
                try:
                    base = ai.generate(HEXAGRAMS[number])
                    self.reply(200, {'base': base, 'hexagram': HEXAGRAMS[number]})
                finally:
                    TEST_LOCK.release()
                return
            self.reply(404, {'error': '没有这个接口'})
        except ai.AIError as error:
            self.reply(400, {'error': str(error)})
        except (ValueError, TypeError):
            self.reply(400, {'error': '请求格式无效'})
        except OSError:
            self.reply(500, {'error': '本机配置无法保存，请检查文件权限'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    except OSError:
        try:
            with urllib.request.urlopen(ORIGIN + '/api/health', timeout=2) as response:
                if json.load(response).get('service') != 'cyber-turtle-ai-panel': raise ValueError()
        except Exception:
            raise SystemExit('Port 8767 is occupied by another service') from None
        if args.open: webbrowser.open(ORIGIN)
        print('AI panel already running: ' + ORIGIN)
        return
    print('AI panel: ' + ORIGIN, flush=True)
    if args.open: webbrowser.open(ORIGIN)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == '__main__':
    main()
