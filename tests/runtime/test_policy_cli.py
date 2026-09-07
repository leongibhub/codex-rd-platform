"""REQ-V3-008/021: explain strict admission without making decisions."""
import json
import http.client
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from rd_platform.runtime import Runtime
from rd_platform.orchestration import start_project


class PolicyCliTests(unittest.TestCase):
    def test_status_explains_draft_handoff_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            r = Runtime(root / 'state.db')
            project = start_project(r, name='Demo', idea='Summarize CSV', repository_root=root, request_id='status')
            pid = project['project_id']
            before = r.lifecycle_snapshot(pid)
            result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'rd_platform', '--db', str(r.store.path),
                                     'orchestrate-status', '--project-id', pid, '--limit', '2'],
                                    capture_output=True, text=True, encoding='utf-8', timeout=20)
            self.assertEqual(0, result.returncode, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(12, data['total_work_orders'])
            self.assertTrue(data['truncated'])
            self.assertEqual(2, len(data['work_orders']))
            self.assertEqual('ALLOWED', data['work_orders'][0]['stage_admission'])
            self.assertEqual('WAITING_PREREQUISITE', data['work_orders'][1]['stage_admission'])
            self.assertIn('G0', data['work_orders'][1]['reason'])
            self.assertFalse(data['execution_authorized'])
            self.assertEqual(before, r.lifecycle_snapshot(pid))
            self.assertNotIn('lease_digest', result.stdout)
            self.assertNotIn('lease_token', result.stdout)

    def test_missing_database_read_does_not_initialize_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'missing' / 'state.db'
            result = subprocess.run([sys.executable, '-m', 'rd_platform', '--db', str(path),
                                     'orchestrate-status', '--project-id', 'absent'],
                                    capture_output=True, text=True, encoding='utf-8', timeout=20)
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(path.exists())

    def test_status_is_not_a_claim_or_resume(self):
        from rd_platform.orchestration_status import orchestration_status
        with tempfile.TemporaryDirectory() as tmp:
            r = Runtime(Path(tmp) / 'state.db')
            p = start_project(r, name='Paused', idea='Pause fixture', repository_root=tmp, request_id='pause')['project_id']
            r.execute('lifecycle.control', {'project_id': p, 'action': 'pause', 'reason': 'test fixture'})
            result = orchestration_status(r, p)
            self.assertTrue(all(w['stage_admission'] == 'NOT_READY' for w in result['work_orders']))
            self.assertEqual('PAUSED', result['project_state'])
            self.assertFalse(r.lifecycle_snapshot(p)['gate_decisions'])
            for invalid in (0, 501, True):
                with self.assertRaises(ValueError):
                    orchestration_status(r, p, limit=invalid)

    def test_http_status_is_read_only_and_rejects_ambiguous_query(self):
        from rd_platform.web import create_server
        with tempfile.TemporaryDirectory() as tmp:
            server = create_server(Path(tmp) / 'state.db', port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                r = server.runtime
                pid = start_project(r, name='HTTP', idea='Inspect admission', repository_root=tmp, request_id='http')['project_id']
                before = r.lifecycle_snapshot(pid)
                for suffix, expected in (('', 200), ('&project_id=other', 400), ('&limit=0', 400), ('&execute=true', 400)):
                    conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                    conn.request('GET', '/api/orchestration?project_id=' + pid + suffix)
                    response = conn.getresponse()
                    raw = response.read()
                    self.assertEqual(expected, response.status, raw)
                    if expected == 200:
                        self.assertFalse(json.loads(raw)['execution_authorized'])
                    conn.close()
                self.assertEqual(before, r.lifecycle_snapshot(pid))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
