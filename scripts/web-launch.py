"""Start/reuse the local scan service and a temporary Cloudflare HTTPS tunnel."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local/esp32'


def healthy(base):
    try:
        with urlopen(base + '/api/health', timeout=5) as response:
            return json.load(response) == {'service': 'cyber-turtle-web'}
    except Exception:
        return False


def tunnel_running():
    try:
        pid = int((LOCAL / 'web-tunnel.pid').read_text())
        command = subprocess.check_output(['ps', '-p', str(pid), '-o', 'command='], text=True)
        return 'cloudflared tunnel' in command and 'http://127.0.0.1:8768' in command
    except (OSError, ValueError, subprocess.CalledProcessError):
        return False


def start(command, label):
    with (LOCAL / (label + '.log')).open('wb') as log:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=log, start_new_session=True)
    (LOCAL / (label + '.pid')).write_text(str(process.pid))
    return process


def main():
    LOCAL.mkdir(parents=True, exist_ok=True)
    if not healthy('http://127.0.0.1:8768'):
        service = start([sys.executable, '-u', str(ROOT / 'scripts/web_service.py')], 'web-service')
        for _ in range(30):
            if healthy('http://127.0.0.1:8768'):
                break
            if service.poll() is not None:
                raise RuntimeError('本机服务未启动，请检查 .local/esp32/web-service.log')
            time.sleep(0.2)
        else:
            raise RuntimeError('本机服务暂未就绪，请检查日志后重试')

    config = LOCAL / 'web-public.json'
    try:
        base = json.loads(config.read_text())['base_url']
    except (OSError, ValueError, KeyError):
        base = ''
    if tunnel_running():
        if healthy(base):
            print('扫码服务已运行：' + base)
            print('请保持 Mac 唤醒并联网；运行电脑打印中转后重新摇动设备。')
            return
        raise RuntimeError('现有通道尚未恢复，请检查网络和 .local/esp32/web-tunnel.log；未另开重复通道')

    executable = shutil.which('cloudflared') or '/opt/homebrew/bin/cloudflared'
    if not Path(executable).is_file():
        raise RuntimeError('未找到 cloudflared，请先按 docs/WEB_LOCAL_SETUP.md 安装')
    previous_config = config.read_bytes() if config.exists() else None
    tunnel = start([executable, 'tunnel', '--url', 'http://127.0.0.1:8768',
                    '--no-autoupdate', '--protocol', 'quic'], 'web-tunnel')
    # Quick-tunnel connection retries and DNS can take over a minute to settle.
    deadline = time.monotonic() + 180
    candidate = ''
    try:
        while time.monotonic() < deadline:
            if tunnel.poll() is not None:
                raise RuntimeError('HTTPS 通道未启动，请检查 .local/esp32/web-tunnel.log')
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',
                              (LOCAL / 'web-tunnel.log').read_text(errors='replace'))
            if match and candidate != match.group():
                candidate = match.group()
                # The service reloads its Host allowlist from this file.
                temporary = config.with_suffix('.tmp')
                temporary.write_text(json.dumps({'base_url': candidate}))
                temporary.chmod(0o600)
                temporary.replace(config)
            if candidate and healthy(candidate):
                print('临时扫码服务：' + candidate)
                print('请保持 Mac 唤醒并联网；先启动电脑打印中转，再重新摇动设备使用新二维码。')
                print('通道重启可能更换地址；旧域名的浏览器历史不会自动迁移。')
                return
            time.sleep(1)
        raise RuntimeError('HTTPS 通道连接超时，请检查日志；本机服务仍保留运行，原地址配置已恢复')
    except BaseException:
        try:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        finally:
            if previous_config is None:
                config.unlink(missing_ok=True)
            else:
                temporary = config.with_suffix('.tmp')
                temporary.write_bytes(previous_config)
                temporary.chmod(0o600)
                temporary.replace(config)
        raise


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
