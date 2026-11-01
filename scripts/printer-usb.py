"""Direct USB diagnostics for the confirmed XP-58IIH (0483:070b).

Requires pyusb==1.3.1 and libusb-package==1.0.30.0 in the project environment.
Samples are saved locally; physical printing requires --send. No auto-retry.
"""
import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local/esp32'


def hexagram_raster(lines):
    # Trial canvas: 384 dots. A centered 192-dot glyph, six lines top to bottom.
    width, height = 384, 120
    bitmap = bytearray(width // 8 * height)
    for row, yang in enumerate(reversed(lines)):
        for y in range(6 + row * 18, 14 + row * 18):
            for x in range(96, 288):
                if yang or x < 176 or x >= 208:
                    bitmap[y * 48 + x // 8] |= 0x80 >> (x % 8)
    return b'\x1dv0\x00' + bytes([48, 0, height, 0]) + bitmap


def sample(kind):
    if kind == 'ascii':
        return b'\x1b@USB DIRECT TEST 002\r\n\n\n\n'
    data = json.loads((ROOT / 'data/hexagrams.json').read_text())
    qian = next(h for h in data if h['hexagram_id'] == 1)
    payload = b'\x1b@\x1ba\x01\x1c&'
    payload += '赛博龟壳\n中文与卦象测试\nTEST 003\n\n'.encode('gb18030')
    payload += hexagram_raster(qian['lines_bottom_to_top'])
    payload += '\n乾\n上卦 乾  下卦 乾\n\n联调样张 非正式签文\n\n\n'.encode('gb18030')
    return payload + b'\x1b@'


def send_payload(payload=None):
    """Probe, or send one payload; USB acknowledgement is not physical completion."""
    import libusb_package
    import usb.util
    devices = list(libusb_package.find(find_all=True, idVendor=0x0483, idProduct=0x070b))
    if len(devices) != 1:
        raise RuntimeError('Expected exactly one 0483:070b printer; found ' + str(len(devices)))
    device = devices[0]
    try:
        config = device.get_active_configuration()
        interfaces = [i for i in config if (i.bInterfaceClass, i.bInterfaceSubClass, i.bInterfaceProtocol) == (7, 1, 2)]
        if len(interfaces) != 1: raise RuntimeError('Printer interface differs; inspect before sending')
        interface = interfaces[0]
        endpoints = [{'address': hex(e.bEndpointAddress), 'attributes': e.bmAttributes, 'max_packet': e.wMaxPacketSize} for e in interface]
        print(json.dumps({'interface': interface.bInterfaceNumber, 'endpoints': endpoints}))
        if payload is None: return
        outputs = [e for e in interface if usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK]
        if len(outputs) != 1: raise RuntimeError('Expected one Bulk OUT endpoint')
        usb.util.claim_interface(device, interface.bInterfaceNumber)
        sent = 0
        try:
            for offset in range(0, len(payload), 256):
                chunk = payload[offset:offset+256]
                n = device.write(outputs[0].bEndpointAddress, chunk, timeout=3000)
                sent += n
                if n != len(chunk): raise RuntimeError('Partial USB write')
                time.sleep(0.02)
        except Exception:
            print('Transfer interrupted after', sent, 'acknowledged bytes. Check paper before any retry.')
            raise
        print('USB acknowledged', sent, 'bytes. Physical output still needs visual confirmation.')
    finally:
        # PyUSB disposes claimed interfaces and closes the handle, including
        # disconnect-related release errors; an extra release can mask the cause.
        usb.util.dispose_resources(device)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['probe', 'ascii', 'chinese'])
    parser.add_argument('--send', action='store_true', help='Print exactly one sample')
    args = parser.parse_args()
    LOCAL.mkdir(parents=True, exist_ok=True)
    payload = None
    if args.action != 'probe':
        payload = sample(args.action)
        output = LOCAL / ('printer-' + args.action + '.bin')
        output.write_bytes(payload)
        print('Sample prepared:', output.name, 'bytes:', len(payload))
        if not args.send:
            print('Not sent. Add --send for one physical print.'); return
    send_payload(payload)


if __name__ == '__main__':
    main()
