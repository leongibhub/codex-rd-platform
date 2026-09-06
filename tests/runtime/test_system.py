"""Independent system tests for the V2 local runtime.

These tests derive from DES-V2-001 / REQ-V2-001..009.  They deliberately use
temporary on-disk SQLite databases, the public Runtime interface, a real
``python -m rd_platform`` HTTP-server subprocess, and the bounded command
runner.  No production dependency is mocked.
"""

from __future__ import annotations

import http.client
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from rd_platform.reporting import report
from rd_platform.runner import run_command
from rd_platform.runtime import Runtime


ROOT = Path(__file__).resolve().parents[2]


class RuntimeSystemTests(unittest.TestCase):
    """Black-box system tests: durable state, quality controls, and recovery."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rd-platform-system-")
        self.db_path = Path(self.temp_dir.name) / "state.db"
        self.runtime = Runtime(self.db_path)
        self.project = self.runtime.execute("project.create", {"name": "system", "idea": "independent QA"})
        for agent_id, role in (("dev-a", "developer"), ("test-a", "tester"), ("review-a", "reviewer")):
            self.runtime.execute("agent.register", {"id": agent_id, "role": role})

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def task(self, title: str = "deliver", dependencies: list[str] | None = None) -> dict:
        return self.runtime.execute(
            "task.create",
            {
                "project_id": self.project["id"],
                "title": title,
                "why": "required by acceptance criteria",
                "role": "developer",
                "requirements": ["REQ-V2-003", "REQ-V2-004", "REQ-V2-005"],
                "dependencies": dependencies or [],
                "inputs": {"source": "independent-system-test"},
            },
        )

    def start_and_finish(self, task_id: str, agent_id: str, phase: str, status: str = "PASS") -> dict:
        run = self.runtime.execute("run.start", {"task_id": task_id, "agent_id": agent_id, "phase": phase})
        return self.runtime.execute(
            "run.finish",
            {
                "run_id": run["id"],
                "status": status,
                "summary": f"{phase} {status.lower()}",
                "evidence": {"exit_code": 0 if status == "PASS" else 1, "observed": phase},
            },
        )

    def complete_to_done(self, task_id: str) -> dict:
        for phase, agent_id in (("implementation", "dev-a"), ("unit", "test-a"), ("integration", "test-a"), ("review", "review-a")):
            result = self.start_and_finish(task_id, agent_id, phase)
        return result

    def snapshot_task(self, task_id: str) -> dict:
        return next(task for task in self.runtime.snapshot(self.project["id"])["tasks"] if task["id"] == task_id)

    def test_durable_identity_separation_and_final_review_gate(self) -> None:
        """TC-V2-901 / REQ-V2-001,003: reopen keeps facts; no self-validation."""
        task = self.task()
        self.start_and_finish(task["id"], "dev-a", "implementation")
        with self.assertRaises(ValueError):
            self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev-a", "phase": "unit"})
        self.start_and_finish(task["id"], "test-a", "unit")
        self.start_and_finish(task["id"], "test-a", "integration")
        before_review = self.snapshot_task(task["id"])
        self.assertEqual("READY", before_review["status"])
        self.assertEqual("review", before_review["next_phase"])

        done = self.start_and_finish(task["id"], "review-a", "review")
        reopened = Runtime(self.db_path).snapshot(self.project["id"])
        reopened_task = next(item for item in reopened["tasks"] if item["id"] == task["id"])
        self.assertEqual("DONE", done["status"])
        self.assertEqual("DONE", reopened_task["status"])
        self.assertEqual(4, reopened_task["checks_passed"])
        self.assertTrue(all(event["sequence"] > 0 for event in reopened["events"]))

    def test_fail_retry_retest_closes_defect_only_after_fresh_review(self) -> None:
        """TC-V2-902 / REQ-V2-004: failed evidence cannot establish a later PASS."""
        task = self.task()
        self.start_and_finish(task["id"], "dev-a", "implementation", "FAIL")
        failed_snapshot = self.runtime.snapshot(self.project["id"])
        self.assertEqual("FAILED", self.snapshot_task(task["id"])["status"])
        self.assertEqual("OPEN", failed_snapshot["defects"][0]["status"])

        retried = self.runtime.execute("task.control", {"task_id": task["id"], "action": "retry", "reason": "repair applied"})
        self.assertEqual(2, retried["attempt"])
        self.assertEqual(0, retried["checks_passed"])
        self.start_and_finish(task["id"], "dev-a", "implementation")
        self.start_and_finish(task["id"], "test-a", "unit")
        self.start_and_finish(task["id"], "test-a", "integration")
        before_review = self.snapshot_task(task["id"])
        self.assertEqual("READY", before_review["status"])
        self.assertEqual("OPEN", self.runtime.snapshot(self.project["id"])["defects"][0]["status"])
        self.start_and_finish(task["id"], "review-a", "review")
        final = self.runtime.snapshot(self.project["id"])
        self.assertEqual("DONE", self.snapshot_task(task["id"])["status"])
        self.assertEqual("CLOSED", final["defects"][0]["status"])

    def test_pause_rejects_late_result_without_partial_write(self) -> None:
        """TC-V2-903 / REQ-V2-005: pause invalidates the in-flight run atomically."""
        task = self.task()
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev-a", "phase": "implementation"})
        self.runtime.execute("task.control", {"task_id": task["id"], "action": "pause", "reason": "operator stop"})
        with self.assertRaises(ValueError):
            self.runtime.execute(
                "run.finish",
                {"run_id": run["id"], "status": "PASS", "summary": "late worker result", "evidence": {"exit_code": 0}},
            )
        snapshot = self.runtime.snapshot(self.project["id"])
        stored_run = next(item for item in snapshot["runs"] if item["id"] == run["id"])
        self.assertEqual("INVALIDATED", stored_run["status"])
        self.assertIsNone(stored_run["evidence"])
        self.assertEqual("PAUSED", self.snapshot_task(task["id"])["status"])

    def test_modify_cascades_to_completed_dependents(self) -> None:
        """TC-V2-904 / REQ-V2-002,005: upstream change voids downstream evidence."""
        upstream = self.task("upstream")
        downstream = self.task("downstream", [upstream["id"]])
        self.complete_to_done(upstream["id"])
        self.complete_to_done(downstream["id"])
        old_downstream = self.snapshot_task(downstream["id"])
        self.assertEqual("DONE", old_downstream["status"])

        changed = self.runtime.execute(
            "task.control",
            {"task_id": upstream["id"], "action": "modify", "reason": "upstream contract changed", "inputs": {"version": 2}},
        )
        invalidated_downstream = self.snapshot_task(downstream["id"])
        self.assertEqual(2, changed["revision"])
        self.assertNotEqual("DONE", invalidated_downstream["status"])
        self.assertGreater(invalidated_downstream["revision"], old_downstream["revision"])
        self.assertEqual(0, invalidated_downstream["checks_passed"])
        with self.assertRaises(ValueError):
            self.runtime.execute("run.start", {"task_id": downstream["id"], "agent_id": "dev-a", "phase": "implementation"})

    def test_concurrent_runtime_instances_allow_one_active_run(self) -> None:
        """TC-V2-905 / REQ-V2-001,002: SQLite transaction/index protect contention."""
        task = self.task()
        barrier = threading.Barrier(8)
        successes: list[dict] = []
        errors: list[BaseException] = []

        def start() -> None:
            try:
                barrier.wait(timeout=3)
                successes.append(Runtime(self.db_path).execute("run.start", {"task_id": task["id"], "agent_id": "dev-a", "phase": "implementation"}))
            except BaseException as exc:  # expected losing contenders return an API error
                errors.append(exc)

        threads = [threading.Thread(target=start) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(1, len(successes))
        self.assertEqual(7, len(errors))
        snapshot = self.runtime.snapshot(self.project["id"])
        self.assertEqual(1, sum(run["status"] == "ACTIVE" for run in snapshot["runs"] if run["task_id"] == task["id"]))


class CliHttpRunnerSystemTests(unittest.TestCase):
    """TC-V2-906..908: process-level CLI, HTTP boundary, runner, reporting."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rd-platform-e2e-")
        self.db_path = Path(self.temp_dir.name) / "state.db"
        self.server: subprocess.Popen[str] | None = None
        self.port: int | None = None

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.terminate()
            try:
                self.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=5)
            if self.server.stdout is not None:
                self.server.stdout.close()
            if self.server.stderr is not None:
                self.server.stderr.close()
        self.temp_dir.cleanup()

    def cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "rd_platform", "--db", str(self.db_path), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

    def start_server(self) -> int:
        self.server = subprocess.Popen(
            [sys.executable, "-m", "rd_platform", "--db", str(self.db_path), "serve", "--port", "0"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertIsNotNone(self.server.stdout)
        line = self.server.stdout.readline().strip()
        match = re.fullmatch(r".*127\.0\.0\.1:(\d+)", line)
        if match is None:
            stderr = self.server.stderr.read() if self.server.stderr is not None else ""
            self.fail(f"server did not publish a loopback endpoint: stdout={line!r}, stderr={stderr!r}")
        self.port = int(match.group(1))
        return self.port

    def http(self, method: str, path: str, body: object | bytes | None = None, **headers: str) -> tuple[int, bytes]:
        self.assertIsNotNone(self.port)
        encoded = body if isinstance(body, bytes) else (None if body is None else json.dumps(body).encode("utf-8"))
        request_headers = {"Host": f"127.0.0.1:{self.port}", **headers}
        if encoded is not None:
            request_headers.setdefault("Content-Type", "application/json")
            request_headers["Content-Length"] = str(len(encoded))
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=encoded, headers=request_headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def http_command(self, command: str, data: dict, request_id: str | None = None) -> dict:
        payload: dict[str, object] = {"command": command, "data": data}
        if request_id is not None:
            payload["request_id"] = request_id
        status, raw = self.http("POST", "/api/commands", payload)
        self.assertEqual(200, status, raw.decode("utf-8", errors="replace"))
        return json.loads(raw)

    def test_cli_http_runner_lifecycle_and_report_are_real(self) -> None:
        """TC-V2-906 / REQ-V2-001,003,006,008,009: actual process-to-report path."""
        created = self.cli("command", "project.create", json.dumps({"name": "E2E", "idea": "real process"}), "--request-id", "e2e-project")
        self.assertEqual(0, created.returncode, created.stderr)
        project = json.loads(created.stdout)
        self.start_server()
        for agent_id, role in (("dev-e2e", "developer"), ("test-e2e", "tester"), ("review-e2e", "reviewer")):
            self.http_command("agent.register", {"id": agent_id, "role": role})
        task = self.http_command(
            "task.create",
            {
                "project_id": project["id"], "title": "real lifecycle", "why": "verify system boundary",
                "role": "developer", "requirements": ["REQ-V2-008"], "dependencies": [], "inputs": {"e2e": True},
            },
        )
        runtime = Runtime(self.db_path)
        first_report = report(runtime.snapshot(project["id"]))
        self.assertEqual("NOT_EXECUTED", first_report["test_execution"]["status"])
        self.assertEqual("DO_NOT_RELEASE", first_report["release_recommendation"]["status"])

        for phase, agent_id in (("implementation", "dev-e2e"), ("unit", "test-e2e"), ("integration", "test-e2e"), ("review", "review-e2e")):
            evidence = run_command([sys.executable, "-c", f"print('observed {phase}')"], cwd=ROOT, timeout=5)
            self.assertEqual("PASS", evidence["status"])
            self.assertIn(f"observed {phase}", evidence["stdout"])
            run = runtime.execute("run.start", {"task_id": task["id"], "agent_id": agent_id, "phase": phase})
            runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": phase, "evidence": evidence})

        final_report = report(Runtime(self.db_path).snapshot(project["id"]))
        self.assertEqual("PASS", final_report["test_execution"]["status"])
        # A fully recorded module workflow establishes module quality, not an
        # invented deployment or human-acceptance decision.
        self.assertEqual("NO_RELEASE_EVIDENCE", final_report["release_recommendation"]["status"])

    def test_http_rejects_malicious_origin_host_and_json_without_writing(self) -> None:
        """TC-V2-907 / REQ-V2-009: HTTP validation is fail-closed and non-mutating."""
        self.start_server()
        payload = {"command": "project.create", "data": {"name": "attack", "idea": "must not persist"}}
        status, _ = self.http("POST", "/api/commands", payload, Origin="https://attacker.example")
        self.assertEqual(403, status)
        status, _ = self.http("POST", "/api/commands", payload, Host="attacker.example")
        self.assertEqual(400, status)
        status, _ = self.http("POST", "/api/commands", b"{not-json")
        self.assertEqual(400, status)
        status, _ = self.http("POST", "/api/commands", [])
        self.assertEqual(400, status)
        snapshot = Runtime(self.db_path).snapshot()
        self.assertEqual([], snapshot["projects"])
        self.assertEqual([], snapshot["events"])

    def test_report_does_not_promote_unexecuted_or_stale_evidence_to_pass(self) -> None:
        """TC-V2-908 / REQ-V2-004,008: report counts only current, executed evidence."""
        snapshot = {
            "projects": [],
            "agents": [],
            "events": [],
            "defects": [],
            "tasks": [{"id": "task-1", "project_id": "project-1", "requirements": ["REQ-V2-008"], "revision": 2, "attempt": 2, "status": "READY"}],
            "runs": [
                {"task_id": "task-1", "phase": "unit", "status": "PASS", "revision": 1, "attempt": 1, "evidence": {"exit_code": 0}},
                {"task_id": "task-1", "phase": "integration", "status": "PASS", "revision": 2, "attempt": 2, "evidence": {}},
            ],
        }
        result = report(snapshot)
        self.assertEqual("NOT_EXECUTED", result["test_execution"]["status"])
        self.assertEqual(0, result["test_execution"]["passed"])
        self.assertEqual("DO_NOT_RELEASE", result["release_recommendation"]["status"])


if __name__ == "__main__":
    unittest.main()
