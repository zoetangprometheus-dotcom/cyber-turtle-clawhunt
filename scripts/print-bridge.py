"""Local ESP32 serial -> XP-58IIH USB demo bridge. No automatic print retry."""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import time
import queue
import threading
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_client
import receipt_layout

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local/esp32'
spec = importlib.util.spec_from_file_location('printer_usb', ROOT / 'scripts/printer-usb.py')
printer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(printer)
HEXAGRAMS = {h['hexagram_id']: h for h in json.loads((ROOT / 'data/hexagrams.json').read_text())}
EVENT = re.compile(r'EVENT (bringup-[0-9a-f]{8}-[1-9][0-9]*) source=(?:touch|shake|serial) hexagram_id=([0-9]+) upper=(\S+) lower=(\S+) lines=([0-9]+) content_origin=demo_random')


def log(message):
    print(time.strftime('%Y-%m-%d %H:%M:%S'), message, flush=True)


def parse_event(line):
    match = EVENT.fullmatch(line)
    if not match:
        raise ValueError('Malformed EVENT')
    key, number, upper, lower, bits = match.groups()
    hexagram = HEXAGRAMS.get(int(number))
    if not hexagram or upper != hexagram['upper_trigram'] or lower != hexagram['lower_trigram']:
        raise ValueError('Unknown or inconsistent trigrams')
    expected = sum(v << i for i, v in enumerate(hexagram['lines_bottom_to_top']))
    if int(bits) != expected:
        raise ValueError('Inconsistent hexagram lines')
    return key, hexagram


def ticket(key, hexagram, base=None, origin='ai'):
    if base is not None:
        base = ai_client.validate_reading(base)
    return receipt_layout.escpos(receipt_layout.render(hexagram, base, origin))


def configured_reading(hexagram):
    config = ai_client.load_config()
    return ai_client.generate(hexagram, config) if config.get('enabled') else None


class Bridge:
    def __init__(self, database, sender, reading_factory=None, publisher=None):
        self.db = sqlite3.connect(database, check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (event TEXT PRIMARY KEY, hexagram INTEGER NOT NULL, status TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)')
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(jobs)')}
        for column in ('base_json', 'error'):
            if column not in columns:
                self.db.execute('ALTER TABLE jobs ADD COLUMN %s TEXT' % column)
        self.db.commit()
        self.sender = sender
        self.reading_factory = reading_factory or (lambda _: None)
        self.publisher = publisher
        self.pending = None
        self.current = None
        self.on_ready = self.print_job

    def feed(self, line):
        if line.startswith('BOOT ') or line == 'STATE 0':
            self.pending = None
            self.current = None
        elif line.startswith('EVENT '):
            self.pending = None
            self.current = None
            self.pending = parse_event(line)
            self.current = self.pending[0]
            log('EVENT accepted: %s hexagram=%s' % (self.pending[0], self.pending[1]['hexagram_id']))
        elif line == 'STATE 3' and self.pending:
            key, hexagram = self.pending
            self.pending = None
            self.on_ready(key, hexagram)

    def print_job(self, key, hexagram):
        if key != self.current: return
        cursor = self.db.execute('INSERT OR IGNORE INTO jobs(event, hexagram, status) VALUES (?, ?, ?)',
                                 (key, hexagram['hexagram_id'], 'generating'))
        self.db.commit()
        if not cursor.rowcount:
            log('SKIP duplicate: ' + key)
            return
        try:
            base = self.reading_factory(hexagram)
            payload = ticket(key, hexagram, base)
        except ai_client.AIError as error:
            self.db.execute('UPDATE jobs SET status=?, error=? WHERE event=?', ('generation_failed', str(error), key))
            self.db.commit()
            log('AI FAILED (not printed): ' + str(error))
            if self.publisher: self.publisher.fail(key, '短签生成失败，请在设备上重新起卦')
            return
        self.db.execute('UPDATE jobs SET base_json=?, status=? WHERE event=?',
                        (json.dumps(base, ensure_ascii=False) if base else None,
                         'attempting' if key == self.current else 'superseded', key))
        self.db.commit()  # Persist immutable text BEFORE USB; never auto-reprint after a crash.
        if key != self.current:
            log('SKIP superseded result: ' + key)
            if self.publisher: self.publisher.fail(key, '设备已进入下一签，本次未打印，请扫描新二维码')
            return
        if self.publisher:
            if base: self.publisher.set_base(key, base)
            else: self.publisher.fail(key, '本机 AI 尚未启用，请联系设备管理员后重新起卦')
        try:
            self.sender(payload)
        except Exception as error:
            reason = '%s: %s' % (type(error).__name__, error)
            self.db.execute('UPDATE jobs SET status=?, error=? WHERE event=?', ('uncertain', reason, key))
            self.db.commit()
            log('PRINT UNCERTAIN: stopped; inspect paper before any manual retry: ' + key + '; ' + reason)
            raise
        self.db.execute('UPDATE jobs SET status=? WHERE event=?', ('usb_sent', key))
        self.db.commit()
        log('USB_SENT: %s hexagram=%s upper=%s lower=%s; physical output not confirmed'
            % (key, hexagram['hexagram_id'], hexagram['upper_trigram'], hexagram['lower_trigram']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='ESP32 USB serial port; auto-detect only when unique')
    parser.add_argument('--send', action='store_true', help='Enable physical printing; default is dry run')
    parser.add_argument('--trigger-once', action='store_true', help='Start one device event for acceptance')
    parser.add_argument('--stop', action='store_true', help='Stop the running project bridge')
    args = parser.parse_args()
    LOCAL.mkdir(parents=True, exist_ok=True)
    if args.stop:
        with (LOCAL / 'print-bridge.lock').open('a+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lock.seek(0)
                os.kill(int(lock.read().strip()), signal.SIGTERM)
                log('Stop requested')
            else:
                log('No bridge running')
        return
    import serial
    from serial.tools import list_ports
    if not args.port:
        ports = [p.device for p in list_ports.comports() if p.vid == 0x1a86 and p.pid in (0x55d3, 0x55d4)]
        if len(ports) != 1:
            raise SystemExit('Specify --port: expected one CH343 ESP32, found %s' % ports)
        args.port = ports[0]
    with (LOCAL / 'print-bridge.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another print bridge is already running')
        lock.seek(0); lock.truncate(); lock.write(str(os.getpid())); lock.flush()
        if args.send:
            printer.send_payload()  # Verify printer before accepting new events.
        sender = printer.send_payload if args.send else lambda data: log('DRY_RUN bytes=%d; not printed' % len(data))
        database = str(LOCAL / 'print-bridge.sqlite3') if args.send else ':memory:'
        publisher = None
        web_config = LOCAL / 'web-public.json'
        if args.send and web_config.exists():
            from web_service import Store
            publisher = Store(LOCAL / 'web-readings.sqlite3')
        bridge = Bridge(database, sender, configured_reading if args.send else None, publisher)
        jobs = queue.Queue(maxsize=1)
        stopping = threading.Event()
        failed = threading.Event()
        def enqueue(key, hexagram):
            try: jobs.get_nowait()
            except queue.Empty: pass
            jobs.put_nowait((key, hexagram))
        awaiting_qr = None
        def prepare_web(key, hexagram):
            nonlocal awaiting_qr
            if not publisher:
                enqueue(key, hexagram); return
            public = json.loads(web_config.read_text()).get('base_url', '').rstrip('/')
            if not re.fullmatch(r'https://[a-z0-9.-]+', public):
                raise RuntimeError('Invalid public web address')
            created = publisher.create(key, hexagram)
            if created is None: return
            reading_id, token = created
            url = public + '/r/' + token + '/'
            if len(url) > 90:
                publisher.fail(key, '入口地址过长，设备无法显示，请联系管理员')
                raise RuntimeError('Web QR base too long')
            awaiting_qr = (key, hexagram, time.monotonic())
            port.write(('qrurl ' + url + '\n').encode('ascii'))
            log('WEB prepared; waiting for device QR acknowledgement')
        bridge.on_ready = prepare_web
        def work():
            while not stopping.is_set():
                try: key, hexagram = jobs.get(timeout=0.2)
                except queue.Empty: continue
                try: bridge.print_job(key, hexagram)
                except Exception:
                    log('PRINT WORKER STOPPED: inspect printer and local job state')
                    failed.set(); return
        worker = threading.Thread(target=work, daemon=True)
        port = serial.Serial(baudrate=115200, timeout=0.2, write_timeout=2, exclusive=True)
        port.dtr = False; port.rts = False; port.port = args.port
        def stop(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try:
            port.open()
            worker.start()
            # DTR/RTS are disabled; still allow a driver-induced boot to finish.
            time.sleep(2)
            port.reset_input_buffer()
            port.write(b'status\n')
            log('READY mode=%s; waiting for a NEW shake/touch event' % ('PRINT' if args.send else 'DRY_RUN'))
            if args.trigger_once:
                port.write(b'start\n')
            buffer = b''
            while True:
                if failed.is_set(): raise RuntimeError('Print worker stopped')
                if awaiting_qr and time.monotonic() - awaiting_qr[2] > 3:
                    publisher.fail(awaiting_qr[0], '设备二维码未能更新，请重新起卦')
                    awaiting_qr = None
                    log('WEB QR update timed out; no print started')
                buffer += port.read(1024)
                if len(buffer) > 8192:
                    raise RuntimeError('Serial input overflow; bridge stopped')
                while b'\n' in buffer:
                    raw, buffer = buffer.split(b'\n', 1)
                    line = raw.decode('utf-8', errors='replace').strip()
                    if line.startswith(('EVENT ', 'STATE ', 'BOOT ', 'STATUS ', 'QR ')):
                        log('DEVICE ' + line)
                    if line == 'QR_URL_SAVED' and awaiting_qr:
                        key, hexagram, _ = awaiting_qr
                        awaiting_qr = None
                        if key == bridge.current: enqueue(key, hexagram)
                        continue
                    if line.startswith(('QR_URL_INVALID', 'QR_SAVE_FAILED')) and awaiting_qr:
                        publisher.fail(awaiting_qr[0], '设备二维码更新失败，请联系管理员')
                        awaiting_qr = None
                        log('WEB QR rejected; no print started')
                        continue
                    bridge.feed(line)
        except KeyboardInterrupt:
            log('STOPPED')
        finally:
            stopping.set(); bridge.current = None
            port.close()
            if worker.is_alive(): worker.join(timeout=1)
            if not worker.is_alive(): bridge.db.close()


if __name__ == '__main__':
    main()
