"""Project-local Arduino build/upload entry point for the Waveshare touch board."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local/esp32'
CONFIG = LOCAL / 'arduino-cli.yaml'
SKETCH = ROOT / 'firmware/cyber_turtle'
FQBN = 'esp32:esp32:esp32s3:FlashSize=16M,PSRAM=enabled,PartitionScheme=app3M_fat9M_16MB,CDCOnBoot=default,UploadSpeed=460800'
CLI = shutil.which('arduino-cli') or '/Applications/Arduino IDE.app/Contents/Resources/app/lib/backend/resources/arduino-cli'
SOURCES = [
    ('waveshare-demo.zip', 'https://files.waveshare.com/wiki/ESP32-S3-Touch-LCD-1.28/ESP32-S3-Touch-LCD-1.28-Demo.zip', 'c18af1c67b38f1ba512cfeec1489bb7a720c90157153d1e1b5295c57a1027ad0'),
    ('u8g2-tft.zip', 'https://codeload.github.com/Bodmer/U8g2_for_TFT_eSPI/zip/refs/heads/master', '793a26a987adcdce2462e9f09740effda9f7b5c28575fd1086a0163061d19708'),
]

def run(*args, cwd=ROOT):
    env = dict(os.environ, PYTHONPYCACHEPREFIX=str(LOCAL/'pycache'), PIP_CACHE_DIR=str(LOCAL/'downloads/pip'))
    subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, check=True)

def cli(*args):
    run(CLI, '--config-file', CONFIG, *args)

def native_mac_tools():
    if platform.system() != 'Darwin' or platform.machine() != 'arm64': return
    python = LOCAL/'python/bin/python'
    if not python.exists(): run('python3', '-m', 'venv', LOCAL/'python')
    run(python, '-m', 'pip', 'install', 'wheel', 'esptool==4.5.1', 'bitstring==3.1.9')
    archive = LOCAL/'downloads/arduino-ctags.tar.gz'
    if not archive.exists():
        with urllib.request.urlopen('https://codeload.github.com/arduino/ctags/tar.gz/refs/tags/5.8-arduino11', timeout=120) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == '86ca843c62aecb9bc531a73d9b6cef33179bd885b1bf8df9e0c7e9761aa9794d'
    source = LOCAL/'vendor/ctags-5.8-arduino11'
    if not (source/'ctags').exists():
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk() or not (LOCAL/'vendor'/member.name).resolve().is_relative_to((LOCAL/'vendor').resolve()):
                    raise SystemExit('Unexpected ctags archive entry')
            tar.extractall(LOCAL/'vendor')
        # Old ctags macro collides with the current macOS SDK's reserved attribute.
        for file in list(source.glob('*.c')) + list(source.glob('*.h')):
            contents = file.read_bytes()
            if b'__unused__' in contents:
                file.write_bytes(contents.replace(b'__unused__', b'CTAGS_UNUSED'))
        run('./configure', cwd=source)
        run('make', '-j4', cwd=source)
    native = LOCAL/'native'
    native.mkdir(exist_ok=True)
    wrapper = native/'esptool'
    wrapper.write_text('#!/bin/sh\nSCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$SCRIPT_DIR/../python/bin/python" -m esptool "$@"\n')
    wrapper.chmod(0o755)

def prepare():
    for folder in ['downloads', 'arduino-data', 'user/libraries', 'build', 'vendor']:
        (LOCAL / folder).mkdir(parents=True, exist_ok=True)
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps({'board_manager': {'additional_urls': ['https://espressif.github.io/arduino-esp32/package_esp32_index.json']},
            'directories': {'data': str(LOCAL/'arduino-data'), 'downloads': str(LOCAL/'downloads'), 'user': str(LOCAL/'user')}}, indent=2))
    for name, url, digest in SOURCES:
        archive = LOCAL / 'downloads' / name
        if not archive.exists():
            print('Downloading', name, flush=True)
            with urllib.request.urlopen(url, timeout=120) as response, archive.open('wb') as output:
                shutil.copyfileobj(response, output)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
            raise SystemExit('Source checksum differs: ' + name + '. Review upstream changes before updating the pinned hash.')
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                target = (LOCAL/'vendor'/entry.filename).resolve()
                if not target.is_relative_to((LOCAL/'vendor').resolve()):
                    raise SystemExit('Archive contains an unsafe path')
            z.extractall(LOCAL/'vendor')
    vendor = LOCAL/'vendor/ESP32-S3-Touch-LCD-1.28-Demo/Arduino/libraries'
    libraries = LOCAL/'user/libraries'
    for name in ['TFT_eSPI', 'TFT_eSPI_Setups']:
        shutil.copytree(vendor/name, libraries/name, dirs_exist_ok=True)
    shutil.copytree(LOCAL/'vendor/U8g2_for_TFT_eSPI-master', libraries/'U8g2_for_TFT_eSPI', dirs_exist_ok=True)
    cli('core', 'update-index')
    cli('core', 'install', 'esp32:esp32@2.0.12')
    cli('config', 'set', 'build_cache.path', LOCAL/'cache')
    native_mac_tools()

def build():
    if not CONFIG.exists():
        raise SystemExit('Run: python3 scripts/firmware.py prepare')
    run('python3', ROOT/'scripts/refresh-firmware-hexagrams.py')
    properties = []
    # Core 2.0.12 leaves these paths unquoted; project paths may contain spaces.
    if platform.system() != 'Windows':
        for hook, command in [('prebuild', ':'), ('core.prebuild', 'echo -DARDUINO_CORE_BUILD'), ('core.postbuild', ':')]:
            properties += ['--build-property', f"recipe.hooks.{hook}.set_core_build_flag.pattern=bash -c \"{command} > '{{file_opts.path}}'\""]
    if platform.system() == 'Darwin' and platform.machine() == 'arm64':
        if not (LOCAL/'native/esptool').exists(): native_mac_tools()
        for key, value in [('tools.esptool_py.path', LOCAL/'native'), ('tools.esptool_py.cmd', 'esptool'), ('runtime.tools.ctags.path', LOCAL/'vendor/ctags-5.8-arduino11')]:
            properties += ['--build-property', f'{key}={value}']
    cli('compile', '--fqbn', FQBN, *properties, '--build-path', LOCAL/'build/sketch', SKETCH)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'build', 'upload', 'monitor', 'ports'])
    p.add_argument('--port', help='Explicit connected board serial port; never auto-select a device')
    a = p.parse_args()
    if a.action == 'prepare': prepare()
    elif a.action == 'build': build()
    elif a.action == 'ports': cli('board', 'list')
    else:
        if not a.port: p.error('--port is required')
        if a.action == 'upload':
            build()
            if (LOCAL/'native/esptool').exists():
                output = LOCAL/'build/sketch'
                run(LOCAL/'native/esptool', '--chip', 'esp32s3', '--port', a.port, '--baud', '460800', '--before', 'default_reset', '--after', 'hard_reset',
                    'write_flash', '-z', '--flash_mode', 'dio', '--flash_freq', '80m', '--flash_size', '16MB',
                    '0x0', output/'cyber_turtle.ino.bootloader.bin', '0x8000', output/'cyber_turtle.ino.partitions.bin',
                    '0xe000', LOCAL/'arduino-data/packages/esp32/hardware/esp32/2.0.12/tools/partitions/boot_app0.bin', '0x10000', output/'cyber_turtle.ino.bin')
            else:
                cli('upload', '--port', a.port, '--fqbn', FQBN, '--input-dir', LOCAL/'build/sketch', SKETCH)
        else: cli('monitor', '--port', a.port, '--config', 'baudrate=115200')

if __name__ == '__main__': main()
