"""Local HTTP fixtures and bridge integration; no paid API or USB writes."""
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import ai_client as ai
spec = importlib.util.spec_from_file_location('bridge', ROOT / 'scripts/print-bridge.py')
bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
BASE = json.loads((ROOT / 'data/content-examples.json').read_text())['base_reading']
WEB = {'title':'留一点余地', 'meaning':'观察当下的变化。'*16, 'reflection':'给自己的选择留出空间。'*12, 'action':'写下一件今天可以开始的小事。'}
ANSWER = {'meaning':'沿用原签看待选择。','reflection':'先确认事实，再作尝试。','action':'花十分钟整理一个问题。'}


class Mock(BaseHTTPRequestHandler):
    mode = 'ok'
    seen = None
    def log_message(self, *_): pass
    def do_POST(self):
        Mock.seen = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.mode == 'redirect':
            self.send_response(302); self.send_header('Location', '/stolen'); self.end_headers(); return
        if self.mode == 'error':
            self.send_response(401); self.end_headers(); self.wfile.write(b'private provider detail'); return
        self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
        content = BASE if self.mode == 'ok' else {'title': '\x1b@bad', 'message': 'short', 'action':'short'}
        if self.mode == 'web': content = WEB
        if self.mode == 'question': content = ANSWER
        self.wfile.write(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(content,ensure_ascii=False)}}]}).encode())


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1',0), Mock)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
        cls.config={'base_url':'http://127.0.0.1:%d/v1' % cls.server.server_port,'model':'fixture','api_key':'test-fixture-not-a-secret','enabled':True,'json_mode':True}
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def setUp(self): Mock.mode='ok'

    def test_protocol_and_canonical_input(self):
        result=ai.generate(bridge.HEXAGRAMS[20],self.config)
        self.assertEqual(result, BASE)
        request=Mock.seen
        self.assertEqual(request['response_format'],{'type':'json_object'})
        canonical=json.loads(request['messages'][1]['content'])
        self.assertEqual(canonical['hexagram_id'],20)
        self.assertEqual(canonical['upper_trigram'],'巽')
        self.assertFalse(request['stream'])

    def test_deepseek_flash_non_thinking_request(self):
        reply=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(BASE,ensure_ascii=False)}}]}).encode()
        for url,model,expected in [('https://api.deepseek.com','deepseek-flash',True),
                                   ('https://api.deepseek.com/v1','deepseek-flash',True),
                                   ('https://example.com/v1','deepseek-flash',False),
                                   ('https://api.deepseek.com','another-model',False)]:
            with patch.object(ai.urllib.request,'build_opener') as opener:
                opener.return_value.open.return_value=BytesIO(reply)
                self.assertEqual(ai.generate(bridge.HEXAGRAMS[1],dict(self.config,base_url=url,model=model)),BASE)
                request=opener.return_value.open.call_args.args[0]
                body=json.loads(request.data)
                self.assertEqual(body.get('thinking'),{'type':'disabled'} if expected else None)
                self.assertEqual(body['response_format'],{'type':'json_object'})
                self.assertEqual(request.full_url,url+'/chat/completions')

    def test_errors_redirects_and_controls(self):
        for mode in ('redirect','error','invalid'):
            Mock.mode=mode
            with self.assertRaises(ai.AIError) as caught: ai.generate(bridge.HEXAGRAMS[1],self.config)
            self.assertNotIn('private provider detail',str(caught.exception))
            self.assertNotIn(self.config['api_key'],str(caught.exception))
        with self.assertRaises(ai.AIError): ai.validate_reading(dict(BASE,message=BASE['message']+'\x1b'))
        with self.assertRaises(ai.AIError): ai.endpoint('http://example.com/v1')
        with self.assertRaises(ai.AIError): ai.endpoint('https://secret@example.com/v1')

    def test_web_and_question_keep_original_paper(self):
        with patch.object(ai,'load_config',return_value=self.config):
            Mock.mode='web'
            self.assertEqual(ai.generate_extension(bridge.HEXAGRAMS[20],BASE,theme='career'),WEB)
            request=json.loads(Mock.seen['messages'][1]['content'])
            self.assertEqual(request['canonical_hexagram']['hexagram_id'],20)
            self.assertEqual(request['base_reading'],BASE)
            self.assertEqual(Mock.seen['max_tokens'],3072)
            Mock.mode='question'
            self.assertEqual(ai.generate_extension(bridge.HEXAGRAMS[20],BASE,question='怎样开始新项目？'),ANSWER)
            self.assertEqual(json.loads(Mock.seen['messages'][1]['content'])['question'],'怎样开始新项目？')
            Mock.mode='invalid'
            with self.assertRaises(ai.AIError): ai.generate_extension(bridge.HEXAGRAMS[20],BASE)

    def test_private_save_and_key_destination_change(self):
        old=ai.LOCAL
        try:
            with tempfile.TemporaryDirectory() as temp:
                ai.LOCAL=Path(temp)
                ai.save_config(self.config)
                self.assertEqual((ai.LOCAL/'ai-config.json').stat().st_mode & 0o777,0o600)
                self.assertNotIn('api_key',ai.public_config())
                c=ai.save_config(dict(self.config,api_key=''))
                self.assertTrue(c['api_key'])
                c=ai.save_config(dict(self.config,base_url='https://example.com/v1',api_key='',enabled=False))
                self.assertEqual(c['api_key'],'')
        finally: ai.LOCAL=old

    def test_panel_origin_and_secret_redaction(self):
        panel_spec=importlib.util.spec_from_file_location('panel',ROOT/'scripts/ai-panel.py')
        panel=importlib.util.module_from_spec(panel_spec); panel_spec.loader.exec_module(panel)
        server=ThreadingHTTPServer(('127.0.0.1',0),panel.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin='http://127.0.0.1:%d' % server.server_port
        old=ai.LOCAL
        try:
            with tempfile.TemporaryDirectory() as temp:
                ai.LOCAL=Path(temp)
                data=json.dumps(self.config).encode()
                headers={'Content-Type':'application/json','Origin':origin,'X-Panel-Token':panel.TOKEN}
                request=urllib.request.Request(origin+'/api/config',data=data,headers=headers)
                with urllib.request.urlopen(request) as response:
                    raw=response.read().decode()
                self.assertNotIn(self.config['api_key'],raw)
                self.assertTrue(json.loads(raw)['has_key'])
                for changed in ({'Origin':'https://example.com'},{'X-Panel-Token':'wrong'},{'Host':'example.com'}):
                    bad=urllib.request.Request(origin+'/api/config',data=data,headers=dict(headers,**changed))
                    with self.assertRaises(urllib.error.HTTPError) as caught: urllib.request.urlopen(bad)
                    self.assertEqual(caught.exception.code,403)
                with urllib.request.urlopen(origin+'/api/config') as response:
                    self.assertNotIn(self.config['api_key'],response.read().decode())
                # Preview must match the printer renderer without contacting AI.
                with patch.object(ai, 'generate', side_effect=AssertionError('preview must be local')):
                    preview=urllib.request.Request(origin+'/api/preview',data=json.dumps({'hexagram_id':20,'base':BASE,'origin':'sample'}).encode(),headers=headers)
                    with urllib.request.urlopen(preview) as response: result=json.load(response)
                    expected=bridge.receipt_layout.render(bridge.HEXAGRAMS[20],BASE,'sample')
                    self.assertEqual(result['image'],bridge.receipt_layout.png_data(expected))
        finally:
            server.shutdown();server.server_close();thread.join();ai.LOCAL=old

    def test_ai_paper_and_persisted_immutable_text(self):
        sent=[]; calls=[]
        def factory(h): calls.append(h['hexagram_id']); return BASE
        b=bridge.Bridge(':memory:',sent.append,factory)
        b.current='event-1'
        b.print_job('event-1',bridge.HEXAGRAMS[1]); b.print_job('event-1',bridge.HEXAGRAMS[1])
        self.assertEqual(calls,[1]); self.assertEqual(len(sent),1)
        self.assertEqual(sent[0],bridge.receipt_layout.escpos(bridge.receipt_layout.render(bridge.HEXAGRAMS[1],BASE)))
        self.assertNotEqual(sent[0],bridge.ticket('event-1',bridge.HEXAGRAMS[1]))
        self.assertEqual(json.loads(b.db.execute('SELECT base_json FROM jobs').fetchone()[0]),BASE)
        b.db.close()

    def test_failed_and_stale_ai_never_print(self):
        sent=[]
        def fail(_): raise ai.AIError('fixture failure')
        b=bridge.Bridge(':memory:',sent.append,fail); b.current='event-1'
        b.print_job('event-1',bridge.HEXAGRAMS[1])
        self.assertEqual(b.db.execute('SELECT status FROM jobs').fetchone()[0],'generation_failed')
        def stale(_): b.current='new-event'; return BASE
        b.reading_factory=stale; b.current='event-2'; b.print_job('event-2',bridge.HEXAGRAMS[2])
        self.assertEqual(b.db.execute("SELECT status FROM jobs WHERE event='event-2'").fetchone()[0],'superseded')
        self.assertEqual(sent,[]); b.db.close()


if __name__ == '__main__': unittest.main()
