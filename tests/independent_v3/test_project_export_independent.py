"""Independent public-CLI validation for TASK-V3-007 report/project-export."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from rd_platform.runtime import Runtime
from rd_platform.store import Store


REPOSITORY = Path(__file__).resolve().parents[2]


class IndependentProjectExportTests(unittest.TestCase):
    """TC-V3-IND-1101..1102 / TASK-V3-007."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-export-")
        self.root = Path(self.temp.name)
        self.db = self.root / "state.db"
        self.runtime = Runtime(self.db)
        self.project = self.runtime.execute(
            "project.create", {"name": "independent-export", "idea": "complete projection"}
        )["id"]
        for agent_id, role in (("developer", "developer"), ("tester", "tester")):
            self.runtime.execute("agent.register", {"id": agent_id, "role": role})
        self.runtime.execute(
            "lifecycle.initialize",
            {"project_id": self.project, "repository_root": str(self.root), "mode": "active"},
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *arguments: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "rd_platform", "--db", str(self.db), *arguments],
            cwd=REPOSITORY, text=True, encoding="utf-8", capture_output=True, timeout=timeout, check=False,
        )

    def database_digest(self) -> str:
        with self.runtime.store.transaction(write=False) as connection:
            return hashlib.sha256("\n".join(connection.iterdump()).encode("utf-8")).hexdigest()

    def prepare_case_model(self) -> None:
        self.runtime.execute(
            "artifact.create",
            {
                "project_id": self.project, "artifact_id": "REQ-001", "artifact_type": "REQ",
                "title": "export requirement", "state": "BASELINED",
                "content_ref": {"inline_json": {"body": "private-artifact-v1"}},
                "source": {"kind": "host", "actor": "developer"},
            },
        )
        self.runtime.execute(
            "artifact.revise",
            {
                "artifact_id": "REQ-001", "expected_version": 1, "state": "BASELINED",
                "content_ref": {"inline_json": {"body": "private-artifact-v2"}},
                "reason": "independent version-history fixture", "material": False,
            },
        )
        self.runtime.execute(
            "test_model.create",
            {
                "project_id": self.project, "artifact_id": "TM-001",
                "source": {"kind": "host", "actor": "tester"}, "requirement_refs": ["REQ-001"],
                "function_tree": {"name": "export", "children": ["paginated report"]},
                "risks": [{"risk_id": "RISK-001", "description": "later page can be omitted", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": ["REQ-001"]}],
                "objects": [{"object_id": "OBJ-001", "description": "declared test cases"}],
                "types": ["FUNCTIONAL"],
                "test_points": [{"point_id": "TP-001", "object_id": "OBJ-001", "type": "FUNCTIONAL", "rationale": "read every current case", "risk_refs": ["RISK-001"], "requirement_refs": ["REQ-001"], "coverage_rule": "all case pages"}],
            },
        )

    def create_case(self, number: int) -> dict:
        return self.runtime.execute(
            "test_case.create",
            {
                "project_id": self.project, "case_id": f"TC-{number:03d}", "test_model_id": "TM-001",
                "test_point_refs": ["TP-001"], "requirement_refs": ["REQ-001"],
                "test_type": "FUNCTIONAL", "module": "report projection", "priority": "P2", "risk": "MEDIUM",
                "preconditions": [], "test_data": {"case_number": number},
                "steps": [{"order": 1, "action": "read complete project", "expected_observation": "case is present"}],
                "expected_result": "case remains visible in export", "automation": {"status": "MANUAL"}, "state": "BASELINED",
            },
        )

    def seed_verifiable_synthetic_executions(self, cases: list[dict]) -> None:
        """Seed scale-only executions with the same provenance bindings a report admits.

        These rows are deliberately synthetic fixture data, never evidence about
        a repository project.  Each row nevertheless names its current case
        version, requirement, tester, verified environment and typed result
        evidence so the report's admission contract is exercised rather than
        bypassed by evidence-free PASS records.
        """
        now = datetime.now(timezone.utc).isoformat()
        environment = self.runtime.execute(
            "evidence.register",
            {"project_id": self.project, "kind": "test_environment", "status": "VERIFIED",
             "source": {"kind": "host", "actor": "tester"}, "observed_at": now,
             "locator": {"inline_json": {"fixture": "isolated synthetic scale environment"}}, "metadata": {}},
        )
        environment_ref = {"type": "EVIDENCE", "id": environment["id"], "version": 1}
        with self.runtime.store.transaction() as connection:
            for number, case in enumerate(cases, start=1):
                result = "FAIL" if number == len(cases) else "PASS"
                execution_id = f"synthetic-execution-{number:03d}"
                evidence_id = f"synthetic-evidence-{number:03d}"
                case_ref = {"type": "TEST_CASE", "id": case["id"], "version": case["version"]}
                observation = {"fixture": "synthetic scale observation", "case_number": number, "result": result}
                execution = {
                    "id": execution_id, "project_id": self.project, "case_id": case["id"],
                    "case_version": case["version"], "result": result, "status": "FINISHED",
                    "executor_id": "tester", "created_at": now,
                    "requirement_refs": case["requirement_refs"], "environment_ref": environment_ref,
                    "evidence_refs": [{"type": "EVIDENCE", "id": evidence_id, "version": 1}],
                }
                evidence = {
                    "id": evidence_id, "project_id": self.project, "version": 1,
                    "kind": "test_execution", "status": "VERIFIED",
                    "source": {"kind": "host", "actor": "tester"}, "recorded_by": "tester",
                    "recorded_role": "tester", "observed_at": now, "recorded_at": now,
                    "locator": {"inline_json": observation, "sha256": hashlib.sha256(Store.dumps(observation).encode("utf-8")).hexdigest()},
                    "metadata": {"execution_id": execution_id, "result": result, "artifact_refs": [case_ref]},
                    "supersedes_id": None,
                }
                connection.execute("INSERT INTO lc_test_executions VALUES (?,?,?,?)", (execution_id, self.project, "FINISHED", Store.dumps(execution)))
                connection.execute("INSERT INTO lc_evidence VALUES (?,?,?,?)", (evidence_id, self.project, "VERIFIED", Store.dumps(evidence)))

    def prepare_runner_case(self) -> dict:
        """Create one real argv Case and source file for public CLI freshness checks."""
        subject = self.root / "runner-subject.py"
        assertion = self.root / "runner-assertion.py"
        subject.write_text("SOURCE = 'baseline'\n", encoding="utf-8")
        assertion.write_text("print('independent report freshness pass')\n", encoding="utf-8")
        self.runtime.execute(
            "artifact.create",
            {"project_id": self.project, "artifact_id": "REQ-RUN", "artifact_type": "REQ", "title": "report evidence freshness",
             "state": "BASELINED", "content_ref": {"inline_json": {"acceptance": "stale execution evidence blocks current result"}},
             "source": {"kind": "host", "actor": "developer"}},
        )
        self.runtime.execute(
            "artifact.create",
            {"project_id": self.project, "artifact_id": "CODE-RUN", "artifact_type": "CODE_CHANGE", "title": "freshness source",
             "state": "BASELINED", "content_ref": {"path": "runner-subject.py", "sha256": hashlib.sha256(subject.read_bytes()).hexdigest()},
             "source": {"kind": "host", "actor": "developer"}},
        )
        self.runtime.execute(
            "test_model.create",
            {"project_id": self.project, "artifact_id": "TM-RUN", "source": {"kind": "host", "actor": "tester"},
             "requirement_refs": ["REQ-RUN"], "function_tree": {"name": "freshness", "children": ["evidence artifact"]},
             "risks": [{"risk_id": "RISK-RUN", "description": "a stale result is treated as current", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": ["REQ-RUN"]}],
             "objects": [{"object_id": "OBJ-RUN", "description": "real result evidence file"}], "types": ["DATA_CONSISTENCY"],
             "test_points": [{"point_id": "TP-RUN", "object_id": "OBJ-RUN", "type": "DATA_CONSISTENCY", "rationale": "revalidate stored observation", "risk_refs": ["RISK-RUN"], "requirement_refs": ["REQ-RUN"], "coverage_rule": "tamper and delete"}]},
        )
        initial = self.runtime.execute(
            "test_case.create",
            {"project_id": self.project, "case_id": "TC-RUN", "test_model_id": "TM-RUN", "test_point_refs": ["TP-RUN"],
             "requirement_refs": ["REQ-RUN"], "test_type": "DATA_CONSISTENCY", "module": "report evidence freshness", "priority": "P0", "risk": "HIGH",
             "preconditions": ["source hash is current"], "test_data": {"fixture": "temporary assertion"},
             "steps": [{"order": 1, "action": "execute public test-run", "expected_observation": "a result evidence file is registered"}],
             "expected_result": "report revalidates the exact file", "automation": {"status": "MANUAL"}, "state": "BASELINED"},
        )
        return self.runtime.execute(
            "test_case.revise",
            {"case_id": initial["id"], "expected_version": 1, "reason": "bind independent public runner fixture",
             "automation": {"status": "AUTOMATED", "method": "argv", "tool": "python", "entrypoint": "runner-assertion.py",
                            "argv": ["{python}", "runner-assertion.py"], "cwd": ".",
                            "subject_refs": [{"type": "CODE_CHANGE", "id": "CODE-RUN", "version": 1}]}},
        )

    def insert_legacy_secret_evidence(self) -> None:
        """Seed a legacy-shaped raw record to test export sanitization, not registration."""
        row = {
            "id": "EVD-legacy-secret", "project_id": self.project, "kind": "document", "status": "OBSERVED", "version": 1,
            "source": {"kind": "host", "actor": "developer"}, "recorded_by": "developer", "recorded_role": "developer",
            "observed_at": datetime.now(timezone.utc).isoformat(), "recorded_at": datetime.now(timezone.utc).isoformat(),
            "locator": {"inline_json": {"stdout": "Authorization: Bearer not-for-export-token", "body": "raw evidence body"}},
            "metadata": {"password": "not-for-export-password", "signed_url": "https://example.test/evidence?X-Amz-Signature=not-for-export-signature"},
            "supersedes_id": None,
        }
        with self.runtime.store.transaction() as connection:
            connection.execute("INSERT INTO lc_evidence VALUES (?,?,?,?)", (row["id"], self.project, row["status"], Store.dumps(row)))

    def test_tc_v3_ind_1101_cli_report_export_is_complete_read_only_and_sanitized(self) -> None:
        """>500 cases: a late failure is retained through public report/export CLI without source writes."""
        self.prepare_case_model()
        cases = [self.create_case(number) for number in range(1, 508)]
        self.seed_verifiable_synthetic_executions(cases)
        self.insert_legacy_secret_evidence()
        before = self.database_digest()

        report_result = self.cli("lifecycle-report", "--project-id", self.project)
        self.assertEqual(0, report_result.returncode, report_result.stderr)
        report = json.loads(report_result.stdout)
        self.assertEqual((507, 506, 1, "FAIL", True), (report["total"], report["counts"]["PASS"], report["counts"]["FAIL"], report["conclusion"], report["complete_snapshot"]))
        self.assertEqual("TC-507", report["case_results"][-1]["case_id"])
        self.assertEqual("FAIL", report["case_results"][-1]["result"])
        self.assertEqual(before, self.database_digest(), "report must not mutate source DB")

        destination = self.root / "exported-project"
        exported = self.cli("project-export", "--project-id", self.project, "--output-dir", str(destination))
        self.assertEqual(0, exported.returncode, exported.stderr)
        returned = json.loads(exported.stdout)
        self.assertEqual("COMPLETE", returned["status"])
        marker = json.loads((destination / "export-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("COMPLETE", marker["status"])
        self.assertEqual(returned["source_revision"]["sha256"], marker["source_revision"]["sha256"])
        for item in marker["files"]:
            path = destination / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual((item["bytes"], item["sha256"]), (len(path.read_bytes()), hashlib.sha256(path.read_bytes()).hexdigest()))
        exported_report = json.loads((destination / "docs/06-test/test-report.json").read_text(encoding="utf-8"))
        self.assertEqual((507, 506, 1, "FAIL"), (exported_report["total"], exported_report["counts"]["PASS"], exported_report["counts"]["FAIL"], exported_report["conclusion"]))
        self.assertEqual(before, self.database_digest(), "export must not mutate source DB")
        text = "\n".join(path.read_text(encoding="utf-8") for path in destination.rglob("*") if path.is_file())
        for forbidden in ("private-artifact-v1", "private-artifact-v2", "not-for-export-token", "not-for-export-password", "not-for-export-signature", "raw evidence body"):
            self.assertNotIn(forbidden, text)
        versions = json.loads((destination / "docs/evidence/version-index.json").read_text(encoding="utf-8"))["artifacts"]
        requirement_versions = [row for row in versions if row["id"] == "REQ-001"]
        self.assertEqual([1, 2], [row["version"] for row in requirement_versions])
        self.assertTrue(all("content_sha256" in row and "inline_json" not in row for row in requirement_versions))

        marker_hash = hashlib.sha256((destination / "export-manifest.json").read_bytes()).hexdigest()
        repeated = self.cli("project-export", "--project-id", self.project, "--output-dir", str(destination))
        self.assertEqual(2, repeated.returncode)
        self.assertIn("already exists", repeated.stderr)
        self.assertEqual(marker_hash, hashlib.sha256((destination / "export-manifest.json").read_bytes()).hexdigest())

    def test_tc_v3_ind_1102_real_destination_conflict_leaves_failed_marker(self) -> None:
        """Recovery: a true post-creation filesystem collision leaves an incomplete FAILED export."""
        from rd_platform.lifecycle_export import export_project

        self.prepare_case_model()
        observed = None
        for attempt in range(12):
            target = self.root / f"conflicted-export-{attempt}"
            finished = threading.Event()

            def create_conflict() -> None:
                deadline = time.monotonic() + 5
                marker = target / "export-manifest.json"
                while time.monotonic() < deadline and not marker.exists():
                    time.sleep(0.0005)
                if marker.exists():
                    try:
                        (target / "docs").write_text("independent filesystem collision", encoding="utf-8")
                    except FileExistsError:
                        pass
                finished.set()

            blocker = threading.Thread(target=create_conflict, daemon=True)
            blocker.start()
            try:
                export_project(self.runtime, self.project, target)
            except OSError:
                blocker.join(5)
                marker = target / "export-manifest.json"
                if finished.is_set() and marker.is_file():
                    observed = json.loads(marker.read_text(encoding="utf-8"))
                    break
            else:
                blocker.join(5)
        if observed is None:
            self.skipTest("could not deterministically win the physical export-directory race on this host")
        self.assertEqual("FAILED", observed["status"])
        self.assertIn(observed["failure_type"], {"FileExistsError", "NotADirectoryError", "OSError"})
        with self.assertRaises(ValueError):
            export_project(self.runtime, self.project, target)

    def test_tc_v3_ind_1103_cli_report_blocks_tampered_or_deleted_real_run_evidence(self) -> None:
        """A real CLI run remains historical PASS but cannot survive evidence overwrite/deletion."""
        case = self.prepare_runner_case()
        run = self.cli("test-run", "--project-id", self.project, "--case-id", case["id"],
                       "--case-version", str(case["version"]), "--executor-id", "tester")
        self.assertEqual(0, run.returncode, run.stderr)
        execution = json.loads(run.stdout)
        self.assertEqual("PASS", execution["execution"]["result"])
        result_file = self.root / execution["result_path"]
        self.assertTrue(result_file.is_file())

        result_file.write_text('{"altered":true}\n', encoding="utf-8")
        for state in ("tampered", "deleted"):
            if state == "deleted":
                result_file.unlink()
            before = self.database_digest()
            report_command = self.cli("lifecycle-report", "--project-id", self.project)
            self.assertEqual(0, report_command.returncode, report_command.stderr)
            report = json.loads(report_command.stdout)
            row = report["case_results"][0]
            self.assertEqual(("BLOCKED", "PASS", "STALE"), (row["result"], row["observed_result"], row["freshness"]))
            self.assertTrue(row["freshness_reason"].startswith("CURRENT_EVIDENCE_UNVERIFIABLE:"))
            self.assertEqual({"PASS": 1}, report["historical_execution_counts"])
            self.assertEqual(before, self.database_digest(), f"report must not alter source DB after {state}")

            destination = self.root / f"freshness-{state}"
            exported = self.cli("project-export", "--project-id", self.project, "--output-dir", str(destination))
            self.assertEqual(0, exported.returncode, exported.stderr)
            exported_report = json.loads((destination / "docs/06-test/test-report.json").read_text(encoding="utf-8"))
            self.assertEqual(("BLOCKED", "PASS", "STALE"), tuple(exported_report["case_results"][0][key] for key in ("result", "observed_result", "freshness")))
            self.assertFalse(exported_report["recommend_release"])
            self.assertEqual(before, self.database_digest(), f"export must not alter source DB after {state}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
