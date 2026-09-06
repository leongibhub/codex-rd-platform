"""REQ-V3-008/010: real CLI and restricted HTTP adapter contracts."""
import json
import subprocess
import sys
import tempfile
import unittest
import threading
import urllib.error
import urllib.request
from pathlib import Path


class V3AdapterTests(unittest.TestCase):
    def test_lifecycle_http_is_read_only_and_rejects_invalid_query(self):
        from rd_platform.web import create_server
        with tempfile.TemporaryDirectory() as folder:
            server = create_server(Path(folder) / 'state.db', port=0)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                for query in ('', '?project_id=x&project_id=y', '?project_id=x&limit=bad',
                              '?project_id=x&limit=0', '?project_id=x&after_sequence=-1'):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(base + '/api/lifecycle' + query, timeout=5)
                    self.assertEqual(caught.exception.code, 400)
                request = urllib.request.Request(base + '/api/commands',
                    data=json.dumps({'command':'lifecycle.initialize','data':{}}).encode(),
                    headers={'Content-Type':'application/json'})
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(5)

    def test_stack_probe_is_read_only_and_returns_json(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'untouched.db'
            result = subprocess.run(
                [sys.executable, '-m', 'rd_platform', '--db', str(db), 'stack-probe'],
                capture_output=True, text=True, encoding='utf-8', timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)
            self.assertFalse(db.exists(), 'tool discovery must not create project state')

    def test_lifecycle_cli_without_project_is_controlled_error(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, '-m', 'rd_platform', '--db', str(Path(folder)/'state.db'),
                 'lifecycle', '--project-id', 'missing'],
                capture_output=True, text=True, encoding='utf-8', timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)
            self.assertNotIn('invalid choice', result.stderr)


if __name__ == '__main__':
    unittest.main()
