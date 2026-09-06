from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
import time
import subprocess
from unittest.mock import patch


class CommandRunnerTests(unittest.TestCase):
    def test_sensitive_flag_variants_redact_assignment_and_next_value(self):
        argv = [sys.executable, '-c', 'import sys; print(sys.argv[1:])',
                '--client-secret', 'client-fixture', '--access-token=access-fixture',
                '--database-password', 'database-fixture', '--service-api_key=service-fixture']
        result = self.runner()(argv, os.getcwd())
        for value in ('client-fixture', 'access-fixture', 'database-fixture', 'service-fixture'):
            self.assertNotIn(value, str(result))

    @unittest.skipUnless(os.name == 'nt', 'real Job cleanup fallback')
    def test_query_and_termination_errors_return_fail_and_close_job(self):
        from rd_platform._process_tree import WindowsJob
        original_close = WindowsJob.close
        for method in ('active', 'stop'):
            closed = []
            def close(job):
                original_close(job)
                closed.append(job.handle)
            with self.subTest(method=method), patch('rd_platform._process_tree.ProcessTree.' + method, side_effect=OSError('sensitive-error-fixture')), patch.object(WindowsJob, 'close', close):
                result = self.runner()([sys.executable, '-c', 'import time; time.sleep(5)'], os.getcwd(), timeout=0.15)
                self.assertEqual(result['status'], 'FAIL')
                self.assertIsNotNone(result['launch_error'])
                self.assertNotIn('sensitive-error-fixture', str(result))
                self.assertEqual(closed, [None])

    def test_wait_failure_returns_fail_with_sanitized_error(self):
        original_wait = subprocess.Popen.wait
        calls = []
        def wait(process, *args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired('sensitive-error-fixture', 5)
            return original_wait(process, *args, **kwargs)
        with patch.object(subprocess.Popen, 'wait', wait):
            result = self.runner()([sys.executable, '-c', 'pass'], os.getcwd())
        self.assertEqual(result['status'], 'FAIL')
        self.assertNotIn('sensitive-error-fixture', str(result))

    @unittest.skipUnless(os.name == 'nt', 'real Job handle cleanup')
    def test_close_failure_is_fail_and_retried(self):
        from rd_platform._process_tree import WindowsJob
        original_close = WindowsJob.close
        calls = []
        def close(job):
            calls.append(1)
            if len(calls) == 1:
                raise OSError('sensitive-error-fixture')
            return original_close(job)
        with patch.object(WindowsJob, 'close', close):
            result = self.runner()([sys.executable, '-c', 'pass'], os.getcwd())
        self.assertEqual(result['status'], 'FAIL')
        self.assertGreaterEqual(len(calls), 2)
        self.assertNotIn('sensitive-error-fixture', str(result))

    @unittest.skipUnless(os.name == 'nt', 'Windows Job containment')
    def test_job_assignment_failure_never_executes_target(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'must-not-start'
            with patch('rd_platform._process_tree.WindowsJob.assign', side_effect=OSError('assignment failure')):
                result = self.runner()([sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()'], directory)
            self.assertEqual(result['status'], 'FAIL')
            self.assertIsNotNone(result['launch_error'])
            self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows Job containment')
    def test_job_creation_failure_never_starts_any_process(self):
        with patch('rd_platform._process_tree.WindowsJob', side_effect=OSError('job failure')), patch('subprocess.Popen') as popen:
            result = self.runner()([sys.executable, '-c', 'pass'], os.getcwd())
        popen.assert_not_called()
        self.assertEqual(result['status'], 'FAIL')

    def test_success_waits_for_descendant_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'completed'
            child = f"import time,pathlib; time.sleep(0.15); pathlib.Path({str(marker)!r}).touch()"
            parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)"
            result = self.runner()([sys.executable, '-c', parent], directory, timeout=2)
            self.assertEqual(result['status'], 'PASS', result)
            self.assertTrue(marker.exists())

    def test_overflow_kills_descendants_with_closed_output_handles(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'must-not-survive'
            child = f"import time,pathlib; time.sleep(0.6); pathlib.Path({str(marker)!r}).touch()"
            parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); print('x'*5000000)"
            result = self.runner()([sys.executable, '-c', parent], directory, timeout=2, max_output_bytes=1024)
            time.sleep(0.7)
            self.assertEqual(result['status'], 'FAIL')
            self.assertTrue(result['output_truncated'])
            self.assertFalse(marker.exists())

    def test_streaming_redaction_at_every_chunk_boundary(self):
        from rd_platform.runner import _BoundedRedactor
        secret = 'cross-chunk-fixture'
        payload = ('prefix ' + secret + ' suffix').encode()
        for split in range(len(payload) + 1):
            redactor = _BoundedRedactor([secret], 100)
            redactor.feed(payload[:split])
            redactor.feed(payload[split:])
            self.assertEqual(redactor.text(), 'prefix [REDACTED] suffix')
        redactor = _BoundedRedactor([secret], 12)
        for _ in range(100):
            redactor.feed(b'x' * 4096)
            self.assertLessEqual(len(redactor.output), 12)
            self.assertLessEqual(len(redactor.pending), len(secret))

    def test_explicit_secret_is_redacted_in_output_and_argv(self):
        result = self.runner()([sys.executable, '-c', 'import sys; print(sys.argv[1])', 'tiny'], os.getcwd(), explicit_secret_values=['tiny'])
        self.assertNotIn('tiny', str(result))
        self.assertEqual(result['status'], 'PASS')

    def test_exited_parent_descendant_cannot_survive_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'descendant-marker'
            child = f"import time,pathlib; time.sleep(0.6); pathlib.Path({str(marker)!r}).touch()"
            parent = f"import subprocess,sys; subprocess.Popen([sys.executable,'-c',{child!r}])"
            result = self.runner()([sys.executable, '-c', parent], directory, timeout=0.2)
            time.sleep(0.7)
            self.assertFalse(marker.exists(), result)
            self.assertEqual(result['status'], 'FAIL')
            self.assertTrue(result['timed_out'])

    def test_secret_prefix_at_output_boundary_is_not_disclosed(self):
        with patch.dict(os.environ, {'RD_TEST_SECRET': 'secret-boundary-fixture'}):
            result = self.runner()([sys.executable, '-c', "import os; print(os.environ['RD_TEST_SECRET'])"], os.getcwd(), max_output_bytes=8)
        self.assertNotIn('secret', result['stdout'])
        self.assertLessEqual(len(result['stdout'].encode()), 8)
        self.assertEqual(result['status'], 'FAIL')

    def test_short_secrets_and_command_line_credentials_are_redacted(self):
        with patch.dict(os.environ, {'RD_TEST_SECRET': 'xyZ'}):
            result = self.runner()([sys.executable, '-c', 'import os,sys; print(os.environ["RD_TEST_SECRET"]); print(sys.argv[1:])', '--token', 'token-fixture', '--password=pw-fixture', '--api-key', 'key-fixture'], os.getcwd())
        for secret in ('xyZ', 'token-fixture', 'pw-fixture', 'key-fixture'):
            self.assertNotIn(secret, str(result))

    def test_invalid_utf8_return_value_has_strict_byte_cap(self):
        result = self.runner()([sys.executable, '-c', 'import os; os.write(1, bytes([255])*5000000)'], os.getcwd(), max_output_bytes=31)
        self.assertLessEqual(len(result['stdout'].encode()), 31)
        self.assertEqual(result['status'], 'FAIL')

    def test_output_does_not_use_disk_spool(self):
        with patch('tempfile.TemporaryFile', side_effect=AssertionError('disk spool forbidden')):
            result = self.runner()([sys.executable, '-c', "print('x'*5000000)"], os.getcwd(), max_output_bytes=1024)
        self.assertTrue(result['output_truncated'])
        self.assertEqual(result['status'], 'FAIL')

    def runner(self):
        path = Path(__file__).resolve().parents[2] / 'rd_platform' / 'runner.py'
        self.assertTrue(path.is_file(), 'A real bounded command runner must exist')
        spec = importlib.util.spec_from_file_location('tested_runner', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.run_command

    def test_real_exit_and_output_are_collected(self):
        run = self.runner()
        result = run([sys.executable, '-c', "print('observed'); raise SystemExit(3)"], cwd=os.getcwd())
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['exit_code'], 3)
        self.assertIn('observed', result['stdout'])
        self.assertGreater(result['duration_seconds'], 0)

    def test_success_is_based_on_process_exit(self):
        result = self.runner()([sys.executable, '-c', "print('PASS')"], cwd=os.getcwd())
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['status'], 'PASS')

    def test_timeout_is_not_pass(self):
        result = self.runner()([sys.executable, '-c', 'import time; time.sleep(5)'], cwd=os.getcwd(), timeout=0.15)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['timed_out'])
        self.assertLess(result['duration_seconds'], 4)

    def test_output_budget_prevents_unbounded_evidence(self):
        result = self.runner()([sys.executable, '-c', "print('x'*100000)"], cwd=os.getcwd(), max_output_bytes=1024)
        self.assertTrue(result['output_truncated'])
        self.assertEqual(result['status'], 'FAIL')
        self.assertLessEqual(len(result['stdout'].encode('utf-8')), 1100)

    def test_rejects_shell_strings_and_invalid_limits(self):
        run = self.runner()
        for argv in ('echo hello', [], [sys.executable, 1]):
            with self.assertRaises(ValueError):
                run(argv, cwd=os.getcwd())
        for timeout in (0, -1, True, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                run([sys.executable, '-c', 'pass'], cwd=os.getcwd(), timeout=timeout)

    def test_secret_environment_values_not_written_to_evidence(self):
        run = self.runner()
        key = 'RD_TEST_SECRET'
        old = os.environ.get(key)
        os.environ[key] = 'secret-fixture-value-not-real'
        try:
            result = run([sys.executable, '-c', "import os; print(os.environ['RD_TEST_SECRET'])"], cwd=os.getcwd())
            self.assertNotIn('secret-fixture-value-not-real', result['stdout'])
            self.assertIn('[REDACTED]', result['stdout'])
        finally:
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old

    def test_cwd_and_argv_are_used_without_shell(self):
        with tempfile.TemporaryDirectory(prefix='rd-runner-') as directory:
            result = self.runner()([sys.executable, '-c', 'import os,sys; print(os.getcwd()); print(sys.argv[1])', 'a & b'], cwd=directory)
            self.assertIn('a & b', result['stdout'])
            self.assertEqual(result['cwd'], str(Path(directory).resolve()))


if __name__ == '__main__':
    unittest.main()
