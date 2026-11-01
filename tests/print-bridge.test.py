"""Bridge regression tests; no serial port or physical printer used."""
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bridge', ROOT / 'scripts/print-bridge.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def event(number=3, sequence=1):
    h = module.HEXAGRAMS[number]
    bits = sum(v << i for i, v in enumerate(h['lines_bottom_to_top']))
    return ('EVENT bringup-1234abcd-%d source=shake hexagram_id=%d upper=%s lower=%s lines=%d content_origin=demo_random'
            % (sequence, number, h['upper_trigram'], h['lower_trigram'], bits))


class Tests(unittest.TestCase):
    def test_all_64_match_and_encode(self):
        for number in range(1, 65):
            key, h = module.parse_event(event(number))
            payload = module.ticket(key, h)
            expected = module.receipt_layout.render(h)
            # Decode the actual ESC/POS bands, including headers and polarity.
            self.assertEqual(payload[:5], b'\x1b@\x1ba\x00')
            offset, data, height = 5, bytearray(), 0
            while payload[offset:offset+4] == b'\x1dv0\x00':
                width = int.from_bytes(payload[offset+4:offset+6], 'little')
                rows = int.from_bytes(payload[offset+6:offset+8], 'little')
                self.assertEqual(width, 48); self.assertLessEqual(rows, 120)
                data.extend(payload[offset+8:offset+8+width*rows])
                offset += 8+width*rows; height += rows
            self.assertEqual(payload[offset:], b'\n\n\n\x1b@')
            actual = ImageOps.invert(Image.frombytes('1', (384,height), bytes(data)).convert('L'))
            self.assertEqual(actual.tobytes(), expected.convert('L').tobytes())
            for row, yang in enumerate(reversed(h['lines_bottom_to_top'])):
                self.assertEqual(actual.getpixel((192,156+row*22)), 0 if yang else 255)
                self.assertEqual(actual.getpixel((60,156+row*22)), 0)
        raster = module.printer.hexagram_raster([1, 0, 0, 0, 0, 0])[8:]
        self.assertEqual(raster[6 * 48 + 24], 0)  # Top line is yin.
        self.assertEqual(raster[96 * 48 + 24], 255)  # Bottom line is yang.

    def test_maximum_text_fits_with_clear_margins(self):
        base = {'title': '前'*12, 'message': '路'*50, 'action': '行'*25}
        for h in module.HEXAGRAMS.values():
            image = module.receipt_layout.render(h, base)
            self.assertLess(image.height, 1800)
            ink = ImageOps.invert(image.convert('L')).getbbox()
            self.assertGreaterEqual(ink[0], 20); self.assertLessEqual(ink[2], 364)
            self.assertGreaterEqual(ink[1], 16); self.assertLessEqual(ink[3], image.height-20)

    def test_only_ready_new_event_prints_and_duplicates_survive_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            db = str(Path(temp) / 'jobs.db')
            sent = []
            b = module.Bridge(db, sent.append)
            b.feed('STATE 3')
            b.feed(event())
            b.feed('STATE 1'); b.feed('STATE 2')
            self.assertEqual(len(sent), 0)
            b.feed('STATE 3'); b.feed('STATE 4'); b.feed('STATE 3')
            self.assertEqual(len(sent), 1)
            b.db.close()
            b = module.Bridge(db, sent.append)
            b.feed(event()); b.feed('STATE 3')
            self.assertEqual(len(sent), 1)
            b.feed(event(sequence=2)); b.feed('STATE 3')
            self.assertEqual(len(sent), 2)
            b.db.close()

    def test_invalid_and_reset_do_not_print(self):
        sent = []
        b = module.Bridge(':memory:', sent.append)
        with self.assertRaises(ValueError):
            b.feed(event().replace('lines=17', 'lines=63'))
        b.feed('STATE 3')
        for reset in ('STATE 0', 'BOOT cyber-turtle 0.3.0-bringup'):
            b.feed(event()); b.feed(reset); b.feed('STATE 3')
        self.assertEqual(sent, [])
        b.db.close()

    def test_partial_failure_is_not_retried(self):
        sender = Mock(side_effect=OSError('simulated USB timeout after partial transfer'))
        b = module.Bridge(':memory:', sender)
        b.feed(event())
        with self.assertRaises(OSError):
            b.feed('STATE 3')
        self.assertEqual(b.db.execute('SELECT status,error FROM jobs').fetchone(),
                         ('uncertain', 'OSError: simulated USB timeout after partial transfer'))
        b.feed(event()); b.feed('STATE 3')  # No second call to failing sender.
        sender.assert_called_once()
        b.db.close()

    def test_missing_printer_raises_exception_and_marks_job_uncertain(self):
        fake_libusb = ModuleType('libusb_package')
        fake_libusb.find = Mock(return_value=[])
        fake_usb = ModuleType('usb')
        fake_usb.__path__ = []
        fake_usb.util = ModuleType('usb.util')
        fake_usb.util.dispose_resources = Mock()
        key, h = module.parse_event(event())
        b = module.Bridge(':memory:', module.printer.send_payload)
        self.addCleanup(b.db.close)
        b.current = key
        with patch.dict(sys.modules, {'libusb_package': fake_libusb,
                                     'usb': fake_usb, 'usb.util': fake_usb.util}), \
                patch.object(module, 'ticket', return_value=b'fake receipt'):
            # Exercise the real discovery code, not a sender that already raises
            # an ordinary Exception. SystemExit would escape both bridge/worker.
            with self.assertRaisesRegex(Exception, 'Expected exactly one'):
                b.print_job(key, h)
            self.assertEqual(b.db.execute('SELECT status,error FROM jobs WHERE event=?', (key,)).fetchone(),
                             ('uncertain', 'RuntimeError: Expected exactly one 0483:070b printer; found 0'))
            b.print_job(key, h)  # A failed job must not rediscover/send automatically.
        fake_libusb.find.assert_called_once_with(find_all=True, idVendor=0x0483, idProduct=0x070b)
        fake_usb.util.dispose_resources.assert_not_called()

    def test_disconnect_cleanup_preserves_transfer_error_and_disposes(self):
        class Interface(list):
            bInterfaceClass, bInterfaceSubClass, bInterfaceProtocol = 7, 1, 2
            bInterfaceNumber = 0
        endpoint = Mock(bEndpointAddress=1, bmAttributes=2, wMaxPacketSize=64)
        device = Mock()
        device.get_active_configuration.return_value = [Interface([endpoint])]
        device.write.side_effect = OSError('simulated USB disconnect')
        fake_libusb = ModuleType('libusb_package')
        fake_libusb.find = Mock(return_value=[device])
        fake_usb = ModuleType('usb')
        fake_usb.__path__ = []
        fake_usb.util = ModuleType('usb.util')
        fake_usb.util.ENDPOINT_OUT = 0
        fake_usb.util.ENDPOINT_TYPE_BULK = 2
        fake_usb.util.endpoint_direction = lambda _: 0
        fake_usb.util.endpoint_type = lambda _: 2
        fake_usb.util.claim_interface = Mock()
        fake_usb.util.release_interface = Mock(side_effect=OSError('secondary release error'))
        fake_usb.util.dispose_resources = Mock()
        with patch.dict(sys.modules, {'libusb_package': fake_libusb,
                                     'usb': fake_usb, 'usb.util': fake_usb.util}):
            with self.assertRaisesRegex(OSError, 'simulated USB disconnect'):
                module.printer.send_payload(b'fake receipt')
        fake_usb.util.claim_interface.assert_called_once_with(device, 0)
        fake_usb.util.dispose_resources.assert_called_once_with(device)
        fake_usb.util.release_interface.assert_not_called()
        device.write.assert_called_once()

    def test_web_receives_exact_paper_before_usb_and_failure_is_published(self):
        base = {'title': '先走一小步', 'message': '把眼前的小事慢慢做好，也给自己留下一点调整和休息的时间。',
                'action': '挑一件小事，先做十分钟。'}
        publisher = Mock()
        key, h = module.parse_event(event())
        def send(payload):
            publisher.set_base.assert_called_once_with(key, base)
            self.assertEqual(payload, module.ticket(key, h, base))
        sender = Mock(side_effect=send)
        b = module.Bridge(':memory:', sender, lambda _: base, publisher)
        b.feed(event()); b.feed('STATE 3')
        sender.assert_called_once()
        b.db.close()
        publisher.reset_mock()
        def fail(_):
            raise module.ai_client.AIError('模拟生成失败')
        sender = Mock()
        b = module.Bridge(':memory:', sender, fail, publisher)
        b.feed(event()); b.feed('STATE 3')
        sender.assert_not_called()
        publisher.set_base.assert_not_called()
        publisher.fail.assert_called_once()
        b.db.close()


if __name__ == '__main__':
    unittest.main()
