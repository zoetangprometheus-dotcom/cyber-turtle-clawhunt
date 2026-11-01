"""Launcher lifecycle tests: temporary files, mocked clocks/processes, no network."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('web_launch_test_target', ROOT / 'scripts/web-launch.py')
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)

LOCAL_ORIGIN = 'http://127.0.0.1:8768'
OLD_ORIGIN = 'https://previous-fixture.trycloudflare.com'
NEW_ORIGIN = 'https://candidate-fixture.trycloudflare.com'
PREVIOUS_CONFIG = ('{ "base_url": "' + OLD_ORIGIN + '" }\n').encode()


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.local = Path(self.temp.name)
        self.config = self.local / 'web-public.json'
        self.executable = self.local / 'cloudflared-fixture'
        self.executable.write_text('not an executable; never launched')
        self.clock = 0.0
        self.process = Mock(name='mock_tunnel')
        self.process.poll.return_value = None
        self.process.wait.return_value = 0
        self.replacements = []
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(launch, 'LOCAL', self.local))
        stack.enter_context(patch.object(launch, 'ROOT', self.local))
        stack.enter_context(patch.object(launch.time, 'monotonic', side_effect=lambda: self.clock))
        stack.enter_context(patch.object(launch.time, 'sleep', side_effect=self.advance))
        stack.enter_context(patch.object(launch.shutil, 'which', return_value=str(self.executable)))
        self.running = stack.enter_context(patch.object(launch, 'tunnel_running', return_value=False))
        self.health = stack.enter_context(patch.object(launch, 'healthy', side_effect=lambda base: base == LOCAL_ORIGIN))
        self.start = stack.enter_context(patch.object(launch, 'start', side_effect=self.start_tunnel))
        # Fail closed if a future change bypasses the injected lifecycle functions.
        self.network = stack.enter_context(patch.object(launch, 'urlopen', side_effect=AssertionError('No network allowed')))
        self.popen = stack.enter_context(patch.object(launch.subprocess, 'Popen', side_effect=AssertionError('No process allowed')))
        self.ps = stack.enter_context(patch.object(launch.subprocess, 'check_output', side_effect=AssertionError('No process query allowed')))
        replace = Path.replace

        def record_replace(source, target):
            self.replacements.append((source, target))
            return replace(source, target)

        stack.enter_context(patch.object(Path, 'replace', autospec=True, side_effect=record_replace))
        self.output = io.StringIO()
        stack.enter_context(contextlib.redirect_stdout(self.output))

    def tearDown(self):
        self.network.assert_not_called()
        self.popen.assert_not_called()
        self.ps.assert_not_called()

    def advance(self, seconds):
        self.clock += seconds

    def start_tunnel(self, command, label):
        self.assertEqual(label, 'web-tunnel')  # The already-healthy service must survive.
        self.assertIn(LOCAL_ORIGIN, command)
        (self.local / 'web-tunnel.log').write_text('Temporary route: ' + NEW_ORIGIN + '\n')
        return self.process

    def previous(self):
        self.config.write_bytes(PREVIOUS_CONFIG)
        self.config.chmod(0o600)

    def assert_cleaned(self):
        self.process.terminate.assert_called_once_with()
        self.process.wait.assert_called_once_with(timeout=10)
        self.assertFalse(self.config.with_suffix('.tmp').exists())
        self.assertEqual(self.start.call_count, 1)

    def test_healthy_existing_tunnel_is_reused_without_changes(self):
        self.previous()
        self.running.return_value = True
        self.health.side_effect = lambda base: base in (LOCAL_ORIGIN, OLD_ORIGIN)
        launch.main()
        self.start.assert_not_called()
        self.process.terminate.assert_not_called()
        self.assertEqual(self.config.read_bytes(), PREVIOUS_CONFIG)
        self.assertEqual(self.replacements, [])
        self.assertIn(OLD_ORIGIN, self.output.getvalue())

    def test_candidate_can_become_healthy_after_sixty_seconds(self):
        self.previous()

        def health(base):
            if base == LOCAL_ORIGIN:
                return True
            self.assertEqual(base, NEW_ORIGIN)
            # Host allowlisting must precede checking the new public origin.
            self.assertEqual(json.loads(self.config.read_text())['base_url'], NEW_ORIGIN)
            return self.clock >= 75

        self.health.side_effect = health
        launch.main()
        self.assertEqual(self.clock, 75)
        self.assertEqual(len(self.replacements), 1)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(self.config.read_text())['base_url'], NEW_ORIGIN)
        self.process.terminate.assert_not_called()
        self.process.wait.assert_not_called()
        self.assertIn(NEW_ORIGIN, self.output.getvalue())

    def test_timeout_restores_exact_previous_configuration(self):
        self.previous()
        with self.assertRaisesRegex(RuntimeError, '连接超时'):
            launch.main()
        self.assertEqual(self.clock, 180)
        self.assertEqual(self.config.read_bytes(), PREVIOUS_CONFIG)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(self.replacements), 2)  # Candidate once, then rollback.
        self.assert_cleaned()

    def test_timeout_removes_candidate_when_no_previous_configuration(self):
        with self.assertRaisesRegex(RuntimeError, '连接超时'):
            launch.main()
        self.assertEqual(self.clock, 180)
        self.assertFalse(self.config.exists())
        self.assertEqual(len(self.replacements), 1)
        self.assert_cleaned()

    def test_tunnel_exit_after_candidate_is_written_rolls_back(self):
        self.previous()
        self.process.poll.side_effect = [None, 1]
        with self.assertRaisesRegex(RuntimeError, '通道未启动'):
            launch.main()
        self.assertEqual(self.config.read_bytes(), PREVIOUS_CONFIG)
        self.assert_cleaned()

    def test_interruption_after_candidate_is_written_rolls_back(self):
        self.previous()

        def health(base):
            if base == LOCAL_ORIGIN:
                return True
            raise KeyboardInterrupt()

        self.health.side_effect = health
        with self.assertRaises(KeyboardInterrupt):
            launch.main()
        self.assertEqual(self.config.read_bytes(), PREVIOUS_CONFIG)
        self.assert_cleaned()

    def test_wait_timeout_does_not_skip_configuration_rollback(self):
        self.previous()
        self.process.wait.side_effect = subprocess.TimeoutExpired('mock-cloudflared', 10)
        with self.assertRaises((RuntimeError, subprocess.TimeoutExpired)):
            launch.main()
        self.assertEqual(self.config.read_bytes(), PREVIOUS_CONFIG)
        self.assert_cleaned()


if __name__ == '__main__':
    unittest.main()
