"""Independent CLI/HTTP/report contract checks using only public adapter boundaries."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]


class AdapterBlackBoxTests(unittest.TestCase):
    def test_http_lifecycle_read_and_input_rejection(self) -> None:
        from rd_platform.runtime import Runtime
        from rd_platform.web import create_server
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "state.db"
            runtime = Runtime(db)
            project = runtime.execute("project.create", {"name": "adapter fixture", "idea": "synthetic"})
            runtime.execute("lifecycle.initialize", {"project_id": project["id"], "repository_root": str(ROOT), "mode": "active"})
            server = create_server(db, port=0)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(base + "/api/lifecycle?project_id=" + project["id"], timeout=5) as response:
                    body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(response.status, 200)
                self.assertEqual(body["schema_version"], "lifecycle-v1")
                self.assertEqual(body["project_id"], project["id"])
                self.assertIn("next_sequence", body)
                self.assertIn("has_more", body)
                for query in ("", "?project_id=x&project_id=y", "?project_id=x&limit=bad", "?project_id=x&limit=0", "?project_id=x&limit=501", "?project_id=x&after_sequence=-1"):
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(base + "/api/lifecycle" + query, timeout=5)
                    self.assertEqual(caught.exception.code, 400, query)
                request = Request(base + "/api/commands", data=json.dumps({"command": "lifecycle.initialize", "data": {"project_id": project["id"]}}).encode(), headers={"Content-Type": "application/json"})
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 403)
                self.assertEqual(runtime.lifecycle_snapshot(project["id"])["project_id"], project["id"])
            finally:
                server.shutdown(); server.server_close(); worker.join(5)

    def test_stack_probe_is_json_and_does_not_create_db(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "must-not-exist.db"
            result = subprocess.run([sys.executable, "-m", "rd_platform", "--db", str(db), "stack-probe"], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=30, check=False)
            exists = db.exists()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)
        self.assertFalse(exists)

    def test_lifecycle_missing_project_is_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-m", "rd_platform", "--db", str(Path(directory) / "state.db"), "lifecycle", "--project-id", "missing"], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=30, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("invalid choice", result.stderr)

    def test_report_never_promotes_stale_or_adverse_facts(self) -> None:
        from rd_platform.lifecycle_reporting import lifecycle_report
        empty = lifecycle_report({"project_id": "p", "test_cases": [], "test_executions": []})
        self.assertFalse(empty["recommend_release"])
        latest_fail = lifecycle_report({"project_id": "p", "test_cases": [{"id": "TC-1", "version": 2, "test_type": "BOUNDARY"}], "test_executions": [{"case_id": "TC-1", "case_version": 1, "result": "PASS"}, {"case_id": "TC-1", "case_version": 2, "result": "FAIL"}]})
        self.assertEqual(latest_fail["conclusion"], "FAIL")
        truncated = lifecycle_report({"project_id": "p", "test_cases": [{"id": "TC-1", "version": 2}], "test_executions": [{"case_id": "TC-1", "case_version": 1, "result": "PASS"}], "collections_truncated": {"test_cases": True}})
        self.assertFalse(truncated["complete_snapshot"])
        base = {"project_id": "p", "test_cases": [{"id": "TC-1", "version": 1}], "test_executions": [{"case_id": "TC-1", "case_version": 1, "result": "PASS"}], "gates": [{"gate_id": f"G{number}", "gate_status": "PASS"} for number in range(11)], "traceability": [{"requirement_id": "REQ-1", "status": "COMPLETE"}]}
        for release in ("DEPLOYMENT_FAILED", "CHANGE_PENDING", "ROLLED_BACK"):
            self.assertFalse(lifecycle_report(dict(base, releases=[{"status": release}]))["recommend_release"], release)


if __name__ == "__main__":
    unittest.main()
