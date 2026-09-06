"""TASK-V3-016 worker service contracts (developer unit tests, not independent QA)."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import unittest
from pathlib import Path

from rd_platform.runtime import Runtime


class WorkerServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        self.runtime = Runtime(Path(self.temp.name) / "control.db")
        self.project = self.runtime.execute("project.create", {"name": "worker", "idea": "test"})["id"]
        self.runtime.execute("lifecycle.initialize", {"project_id": self.project, "repository_root": str(self.root), "mode": "active"})
        self.runtime.execute("agent.register", {"id": "worker-dev", "role": "developer"})

    def tearDown(self):
        self.temp.cleanup()

    def work(self, *, role="developer", required_types=("DOC",), minimum=1):
        return self.runtime.execute("work.create", {
            "project_id": self.project, "gate_id": "G0", "activity": "implement", "required_role": role,
            "why": "bounded worker test", "input_refs": [], "dependencies": [],
            "output_contract": {"required_types": list(required_types), "min_outputs": minimum},
        })

    def config(self, argv):
        return {"project_id": self.project, "repository_root": str(self.root), "once": True,
                "workers": [{"agent_id": "worker-dev", "role": "developer", "backend": {"type": "argv", "argv": argv},
                             "lease_seconds": 30, "timeout_seconds": 10, "max_output_bytes": 4096}]}

    def test_real_argv_output_registers_only_hashed_draft_artifact(self):
        self.work()
        generated = self.root / "result.md"
        generated.write_text("actual worker output\n", encoding="utf-8")
        envelope = {"status": "DONE", "summary": "actual command completed", "output_refs": [], "artifacts": [{
            "id": "DOC-WORKER-001", "type": "DOC", "title": "Worker result", "relative_path": "result.md",
            "sha256": hashlib.sha256(generated.read_bytes()).hexdigest(),
        }]}
        script = self.root / "emit.py"
        script.write_text("import json\nprint(json.dumps(" + repr(envelope) + "))\n", encoding="utf-8")
        from rd_platform.worker_service import run_service
        result = run_service(self.runtime, self.config([sys.executable, str(script)]), once=True)
        self.assertEqual(1, result["completed"])
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual("DONE", snapshot["work_orders"][0]["status"])
        artifact = snapshot["artifacts"][0]
        self.assertEqual(("DOC", "DRAFT"), (artifact["artifact_type"], artifact["state"]))
        self.assertEqual(("worker_command", "OBSERVED"), (snapshot["evidence"][0]["kind"], snapshot["evidence"][0]["status"]))

    def test_empty_or_invalid_output_fails_work_without_artifact(self):
        self.work()
        script = self.root / "empty.py"
        script.write_text("print('')\n", encoding="utf-8")
        from rd_platform.worker_service import run_service
        result = run_service(self.runtime, self.config([sys.executable, str(script)]), once=True)
        self.assertEqual(1, result["failed"])
        self.assertEqual("FAIL", result["status"])
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual("FAILED", snapshot["work_orders"][0]["status"])
        self.assertEqual([], snapshot["artifacts"])

    def test_envelope_requires_explicit_artifact_array_and_complete_refs(self):
        from rd_platform.worker_backends import parse_envelope
        with self.assertRaisesRegex(ValueError, "output lists"):
            parse_envelope({"status": "PASS", "stdout": json.dumps({"status": "DONE", "summary": "missing", "output_refs": []})})
        with self.assertRaisesRegex(ValueError, "new artifacts"):
            parse_envelope({"status": "PASS", "stdout": json.dumps({"status": "DONE", "summary": "bad ref", "output_refs": [{}], "artifacts": []})})

    def test_role_mismatch_and_control_db_in_codex_workspace_are_rejected(self):
        self.work(role="tester")
        from rd_platform.worker_service import run_service
        result = run_service(self.runtime, self.config([sys.executable, "-c", "print('{}')"]), once=True)
        self.assertEqual(0, result["claimed"], "developer worker must not claim tester work")
        bad_runtime = Runtime(self.root / ".rd-platform" / "state.db")
        bad_project = bad_runtime.execute("project.create", {"name": "bad", "idea": "bad"})["id"]
        bad_runtime.execute("lifecycle.initialize", {"project_id": bad_project, "repository_root": str(self.root), "mode": "active"})
        bad_runtime.execute("agent.register", {"id": "worker-dev", "role": "developer"})
        with self.assertRaisesRegex(ValueError, "not production-safe"):
            run_service(bad_runtime, {"project_id": bad_project, "repository_root": str(self.root), "workers": [{
                "agent_id": "worker-dev", "role": "developer", "backend": {"type": "codex", "prompt": "hello"},
                "lease_seconds": 30, "timeout_seconds": 10, "max_output_bytes": 4096,
            }]}, once=True)

    def test_empty_daemon_waits_until_stop_event(self):
        from rd_platform.worker_service import run_service
        stop = threading.Event(); result = {}
        thread = threading.Thread(target=lambda: result.setdefault("value", run_service(self.runtime, self.config([sys.executable, "-c", "print('{}')"]), stop_event=stop)), daemon=True)
        thread.start(); time.sleep(.2)
        self.assertTrue(thread.is_alive(), "non-once service must remain resident while idle")
        stop.set(); thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual("STOPPED", result["value"]["status"])

    def test_blocked_first_ready_does_not_starve_second_work(self):
        dependency = self.work(role="tester")
        self.runtime.execute("work.create", {"project_id": self.project, "gate_id": "G0", "activity": "blocked", "required_role": "developer", "why": "blocked first", "input_refs": [], "dependencies": [dependency["id"]], "output_contract": {"required_types": [], "min_outputs": 0}})
        self.work(required_types=(), minimum=0)
        script = self.root / "done.py"; script.write_text("print('{\"status\":\"DONE\",\"summary\":\"done\",\"output_refs\":[],\"artifacts\":[]}')", encoding="utf-8")
        from rd_platform.worker_service import run_service
        result = run_service(self.runtime, self.config([sys.executable, str(script)]), once=True)
        self.assertEqual(1, result["completed"])

    def test_codex_backend_is_rejected_as_unsafe_production_path(self):
        from rd_platform.worker_backends import execute_backend, validate_backend
        with self.assertRaisesRegex(ValueError, "not production-safe"):
            validate_backend({"type": "codex", "prompt": "do"}, repository_root=self.root, control_db=self.runtime.db_path)


if __name__ == "__main__":
    unittest.main()
