"""Independent public-CLI tests for TASK-V3-010's version-bound runner.

Every fixture is an isolated temporary lifecycle project.  The runner is
invoked only through ``python -m rd_platform ... test-run``; setup and
readback use the documented Runtime lifecycle interface, not implementation
test helpers or mocks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from rd_platform.runtime import Runtime


REPOSITORY = Path(__file__).resolve().parents[2]


class IndependentLifecycleRunnerTests(unittest.TestCase):
    """TC-V3-IND-1001..1007 / REQ-V3-006, NFR-V3-003..005."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-runner-")
        self.root = Path(self.temp.name)
        self.db = self.root / "state.db"
        self.runtime = Runtime(self.db)
        self.project = self.runtime.execute(
            "project.create", {"name": "independent-runner", "idea": "CLI contract"}
        )["id"]
        for agent_id, role in (("developer", "developer"), ("tester", "tester")):
            self.runtime.execute("agent.register", {"id": agent_id, "role": role})
        self.runtime.execute(
            "lifecycle.initialize",
            {"project_id": self.project, "repository_root": str(self.root), "mode": "active"},
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli_argv(self, *arguments: str) -> list[str]:
        return [sys.executable, "-m", "rd_platform", "--db", str(self.db), *arguments]

    def run_cli(self, *arguments: str, timeout: float = 30) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self.cli_argv(*arguments), cwd=REPOSITORY, text=True, encoding="utf-8",
            capture_output=True, timeout=timeout, check=False,
        )

    def snapshot(self) -> dict:
        return self.runtime.lifecycle_snapshot(self.project, limit=500)

    def baseline_case(self, assertion_source: str) -> dict:
        """Create a real v2 AUTOMATED argv Case bound to a hashed source file."""
        subject = self.root / "subject.py"
        subject.write_text("SOURCE = 'v1'\n", encoding="utf-8")
        (self.root / "assertion.py").write_text(assertion_source, encoding="utf-8")
        digest = hashlib.sha256(subject.read_bytes()).hexdigest()
        self.runtime.execute(
            "artifact.create",
            {
                "project_id": self.project,
                "artifact_id": "REQ-001",
                "artifact_type": "REQ",
                "title": "runner assertion requirement",
                "state": "BASELINED",
                "content_ref": {"inline_json": {"acceptance": "runner records real result"}},
                "source": {"kind": "host", "actor": "developer"},
            },
        )
        self.runtime.execute(
            "artifact.create",
            {
                "project_id": self.project,
                "artifact_id": "CODE-001",
                "artifact_type": "CODE_CHANGE",
                "title": "hashed assertion subject",
                "state": "BASELINED",
                "content_ref": {"path": "subject.py", "sha256": digest},
                "source": {"kind": "host", "actor": "developer"},
            },
        )
        self.runtime.execute(
            "test_model.create",
            {
                "project_id": self.project,
                "artifact_id": "TM-001",
                "source": {"kind": "host", "actor": "tester"},
                "requirement_refs": ["REQ-001"],
                "function_tree": {"name": "runner", "children": ["argv execution"]},
                "risks": [{"risk_id": "RISK-001", "description": "untrusted result admission", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": ["REQ-001"]}],
                "objects": [{"object_id": "OBJ-001", "description": "baseline argv case"}],
                "types": ["FUNCTIONAL"],
                "test_points": [{"point_id": "TP-001", "object_id": "OBJ-001", "type": "FUNCTIONAL", "rationale": "observe runner result", "risk_refs": ["RISK-001"], "requirement_refs": ["REQ-001"], "coverage_rule": "each assertion result"}],
            },
        )
        initial = self.runtime.execute(
            "test_case.create",
            {
                "project_id": self.project,
                "case_id": "TC-001",
                "test_model_id": "TM-001",
                "test_point_refs": ["TP-001"],
                "requirement_refs": ["REQ-001"],
                "test_type": "FUNCTIONAL",
                "module": "trusted runner CLI",
                "priority": "P0",
                "risk": "HIGH",
                "preconditions": ["baseline source hash is current"],
                "test_data": {"fixture": "temporary local assertion.py"},
                "steps": [{"order": 1, "action": "invoke public test-run CLI", "expected_observation": "execution result is version-bound"}],
                "expected_result": "only current hashed source can admit a result",
                "automation": {"status": "MANUAL"},
                "state": "BASELINED",
            },
        )
        case = self.runtime.execute(
            "test_case.revise",
            {
                "case_id": initial["id"],
                "expected_version": 1,
                "reason": "bind independently controlled argv fixture",
                "automation": {
                    "status": "AUTOMATED",
                    "method": "argv",
                    "tool": "python",
                    "entrypoint": "assertion.py",
                    "argv": ["{python}", "assertion.py"],
                    "cwd": ".",
                    "subject_refs": [{"type": "CODE_CHANGE", "id": "CODE-001", "version": 1}],
                },
            },
        )
        self.assertEqual((2, "AUTOMATED", "argv"), (case["version"], case["status"], case["automation"]["method"]))
        self.assertEqual([{"type": "CODE_CHANGE", "id": "CODE-001", "version": 1}], case["automation"]["subject_refs"])
        return case

    def test_tc_v3_ind_1001_pass_records_hashed_result_and_evidence(self) -> None:
        """Functional: a passing argv produces a current execution and result file."""
        case = self.baseline_case("print('independent assertion pass')\n")
        result = self.run_cli(
            "test-run", "--project-id", self.project, "--case-id", case["id"],
            "--case-version", str(case["version"]), "--executor-id", "tester",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual("PASS", body["execution"]["result"])
        self.assertEqual(0, body["command"]["exit_code"])
        saved = self.root / body["result_path"]
        self.assertTrue(saved.is_file())
        recorded = json.loads(saved.read_text(encoding="utf-8"))
        self.assertEqual({"type": "TEST_CASE", "id": case["id"], "version": 2}, recorded["case_ref"])
        self.assertEqual("PASS", recorded["command"]["status"])
        evidence = self.snapshot()["evidence"]
        self.assertEqual({"test_environment", "test_execution"}, {item["kind"] for item in evidence})
        self.assertTrue(any(item["metadata"].get("result") == "PASS" for item in evidence))

    def test_tc_v3_ind_1002_nonzero_assertion_is_fail_with_open_defect(self) -> None:
        """Negative: real nonzero process status never becomes PASS."""
        case = self.baseline_case("import sys\nprint('expected assertion failure')\nraise SystemExit(17)\n")
        result = self.run_cli(
            "test-run", "--project-id", self.project, "--case-id", case["id"],
            "--case-version", str(case["version"]), "--executor-id", "tester",
        )
        self.assertEqual(1, result.returncode, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual(("FAIL", 17), (body["execution"]["result"], body["command"]["exit_code"]))
        self.assertIn("defect_id", body["execution"])
        defects = self.snapshot()["defects"]
        self.assertEqual(1, len(defects))
        self.assertEqual(("OPEN", body["execution"]["id"]), (defects[0]["status"], defects[0]["source_execution"]))

    def test_tc_v3_ind_1003_timeout_is_fail_and_late_side_effect_is_absent(self) -> None:
        """Reliability: real timeout stops a sleeping assertion before its write."""
        case = self.baseline_case(
            "import time\nfrom pathlib import Path\ntime.sleep(2)\nPath('late.txt').write_text('late', encoding='utf-8')\n"
        )
        result = self.run_cli(
            "test-run", "--project-id", self.project, "--case-id", case["id"],
            "--case-version", str(case["version"]), "--executor-id", "tester", "--timeout", "0.15",
            timeout=15,
        )
        self.assertEqual(1, result.returncode, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual("FAIL", body["execution"]["result"])
        self.assertTrue(body["command"]["timed_out"])
        self.assertFalse((self.root / "late.txt").exists(), "timed-out assertion must not complete its delayed write")

    def test_tc_v3_ind_1004_output_budget_marks_execution_fail(self) -> None:
        """Reliability: actual runner output cap is an execution failure, not success."""
        case = self.baseline_case("print('x' * 70000)\n")
        result = self.run_cli(
            "test-run", "--project-id", self.project, "--case-id", case["id"],
            "--case-version", str(case["version"]), "--executor-id", "tester",
        )
        self.assertEqual(1, result.returncode, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual("FAIL", body["execution"]["result"])
        self.assertTrue(body["command"]["output_truncated"])
        self.assertLessEqual(len(body["command"]["stdout"].encode("utf-8")), 65536)

    def test_tc_v3_ind_1005_wrong_executor_or_version_never_launches(self) -> None:
        """Authorization/version contract: reject before an argv process or execution exists."""
        case = self.baseline_case("from pathlib import Path\nPath('launched.txt').write_text('bad', encoding='utf-8')\n")
        for label, version, executor in (("stale-version", 1, "tester"), ("developer-role", 2, "developer")):
            with self.subTest(label=label):
                result = self.run_cli(
                    "test-run", "--project-id", self.project, "--case-id", case["id"],
                    "--case-version", str(version), "--executor-id", executor,
                )
                self.assertEqual(2, result.returncode)
                self.assertIn("error:", result.stderr)
                self.assertFalse((self.root / "launched.txt").exists())
                self.assertEqual([], self.snapshot()["test_executions"])

    def test_tc_v3_ind_1006_source_drift_after_execution_is_blocked(self) -> None:
        """TOCTOU: a changed bound CODE_CHANGE file cannot admit a PASS."""
        case = self.baseline_case(
            "from pathlib import Path\nPath('subject.py').write_text(\"SOURCE = 'drifted'\\n\", encoding='utf-8')\nprint('command passed before drift check')\n"
        )
        result = self.run_cli(
            "test-run", "--project-id", self.project, "--case-id", case["id"],
            "--case-version", str(case["version"]), "--executor-id", "tester",
        )
        self.assertEqual(1, result.returncode, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual(("BLOCKED", "FINISHED"), (body["execution"]["result"], body["execution"]["status"]))
        self.assertEqual("PASS", body["command"]["status"], "the assertion passed but evidence admission must be blocked")
        self.assertIsNone(body["result_path"])
        raw = self.root / body["unadmitted_result_path"]
        self.assertTrue(raw.is_file(), "unadmitted raw command observation must remain auditable")
        self.assertEqual("RAW_COMMAND_OBSERVATION", json.loads(raw.read_text(encoding="utf-8"))["scope"])
        receipt = raw.with_name("admission.json")
        self.assertEqual("NOT_ADMITTED", json.loads(receipt.read_text(encoding="utf-8"))["admission_status"])
        self.assertEqual([], self.snapshot()["defects"])
        self.assertIn("drifted", (self.root / "subject.py").read_text(encoding="utf-8"))

    def test_tc_v3_ind_1007_pause_during_actual_run_blocks_admission(self) -> None:
        """Recovery: pause does not turn an in-flight command into an admissible PASS."""
        case = self.baseline_case(
            "import time\nfrom pathlib import Path\nPath('started.txt').write_text('started', encoding='utf-8')\ntime.sleep(1.5)\nPath('completed.txt').write_text('completed', encoding='utf-8')\n"
        )
        process = subprocess.Popen(
            self.cli_argv(
                "test-run", "--project-id", self.project, "--case-id", case["id"],
                "--case-version", str(case["version"]), "--executor-id", "tester", "--timeout", "5",
            ), cwd=REPOSITORY, text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not (self.root / "started.txt").exists():
                time.sleep(0.02)
            self.assertTrue((self.root / "started.txt").exists(), "runner did not start the real assertion")
            paused = self.run_cli(
                "command", "lifecycle.control",
                json.dumps({"project_id": self.project, "action": "pause", "reason": "independent mid-run pause"}),
            )
            self.assertEqual(0, paused.returncode, paused.stderr)
            stdout, stderr = process.communicate(timeout=15)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
        self.assertEqual(1, process.returncode, stderr)
        body = json.loads(stdout)
        self.assertEqual(("FINISHED", "BLOCKED"), (body["execution"]["status"], body["execution"]["result"]))
        self.assertTrue((self.root / "completed.txt").exists(), "pause must not falsely claim external process cancellation")
        execution = self.snapshot()["test_executions"]
        self.assertEqual(1, len(execution))
        self.assertEqual(("FINISHED", "BLOCKED"), (execution[0]["status"], execution[0]["result"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
