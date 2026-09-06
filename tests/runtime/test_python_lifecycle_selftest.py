"""TASK-V3-008 harness contract checks; temporary identities are synthetic fixtures.

These tests create no production review, Gate decision or human approval facts.
The actual application lifecycle execution is delegated to an independent tester.
"""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.validate_python_lifecycle import PythonLifecycle, REQS, ROOT, case_catalog
from rd_platform.lifecycle_reporting import lifecycle_report


class PythonLifecycleSelftestTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".rd-platform"
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="contract-python-lifecycle-", dir=base)
        self.directory = Path(self.temp.name)
        self.harness = PythonLifecycle(self.directory / "state")
        self.addCleanup(self.temp.cleanup)

    def prepare(self):
        return self.harness.prepare("synthetic-fixture-developer", "Synthetic temporary-db harness contract fixture only", self.directory / "docs")

    def test_catalog_has_separate_requirement_and_resource_partitions(self):
        cases = case_catalog()
        self.assertEqual(len(cases), len({c["id"] for c in cases}))
        for requirement in REQS:
            self.assertTrue(any(requirement in c["requirements"] for c in cases), requirement)
        self.assertEqual({c["data"]["rows"] for c in cases if "rows" in c["data"]}, {100000, 100001})
        encoding = next(c for c in cases if c["id"] == "TC-PLC-ENCODING")
        with self.assertRaises(UnicodeDecodeError):
            base64.b64decode(encoding["data"]["input_base64"]).decode("utf-8")

    def test_prepare_resumes_existing_project_without_approval_or_execution(self):
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(first["project_id"], second["project_id"])
        self.assertEqual(second["case_count"], len(case_catalog()))
        self.assertEqual(len(self.harness.runtime.snapshot()["projects"]), 1)
        snapshot = self.harness.runtime.lifecycle_snapshot(first["project_id"], limit=500)
        self.assertEqual(snapshot["test_executions"], [])
        self.assertEqual(snapshot["gate_decisions"], [])
        self.assertFalse(any(e["kind"] in {"review", "human_approval", "gate_decision"} for e in snapshot["evidence"]))
        self.assertTrue(all(a["state"] != "APPROVED" for a in snapshot["artifacts"]))

    def test_developer_cannot_execute_as_independent_tester(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "cannot act as independent tester"):
            self.harness.execute("synthetic-fixture-developer", "fixture")
        self.assertEqual(len(self.harness.runtime.snapshot()["agents"]), 1)

    def test_source_drift_prevents_new_execution(self):
        self.prepare()
        with patch.object(self.harness, "file_hashes", return_value={"drift": "observed"}):
            with self.assertRaisesRegex(ValueError, "source baseline drift"):
                self.harness.execute("synthetic-fixture-tester", "fixture")
        self.assertEqual(len(self.harness.runtime.snapshot()["agents"]), 1)

    def test_generated_report_uses_actual_tester_not_prepare_author(self):
        self.prepare()
        self.harness.register_actor("synthetic-fixture-tester", "tester", "Synthetic contract fixture only")
        artifact = self.harness.artifact("DOC-FIXTURE-REPORT", "DOC", "Synthetic provenance fixture", {"inline_json": {"fixture": True}}, actor="synthetic-fixture-tester")
        self.assertEqual(artifact["created_by"], "synthetic-fixture-tester")
        self.assertNotEqual(artifact["created_by"], self.harness.index["author"])

    def test_review_plan_uses_current_artifact_versions(self):
        self.prepare()
        self.harness.runtime.execute("artifact.revise", {"artifact_id": "CODE-PLC-HARNESS", "expected_version": 1,
            "material": False, "reason": "Synthetic current-version projection contract only", "state": "BASELINED",
            "content_ref": self.harness.content(ROOT / "scripts/validate_python_lifecycle.py")})
        self.harness.export()
        plan = json.loads((self.harness.output / "promotion-plan.json").read_text(encoding="utf-8"))
        current = next(r for r in plan["review_subject_refs"] if r["id"] == "CODE-PLC-HARNESS")
        self.assertEqual(current["version"], 2)

    def test_actual_cli_positive_and_error_are_asserted_separately(self):
        self.harness.index["source_hashes"] = self.harness.file_hashes()
        for ident, expected_exit in [("TC-PLC-TOTAL", 0), ("TC-PLC-NEGATIVE", 1)]:
            case = next(c for c in case_catalog() if c["id"] == ident)
            result = self.harness.run_case(case)
            self.assertEqual(result["result"], "PASS", result)
            self.assertEqual(result["actual"]["exit_code"], expected_exit)
            self.assertTrue(result["assertions"]["input_unchanged"])

    def test_finalization_requires_external_evidence_and_rejects_author(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "externally registered"):
            self.harness.finalize(None)
        bundle = self.directory / "fake-review-ids.json"
        bundle.write_text(json.dumps({"reviewer_id": "synthetic-fixture-developer", "evidence_ids": ["EVD-NOT-REAL"]}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must differ"):
            self.harness.finalize(bundle)

    def test_missing_actor_does_not_poison_resumption_index(self):
        with self.assertRaisesRegex(ValueError, "actual actor"):
            self.harness.prepare(None, None, self.directory / "docs")
        self.assertFalse(self.harness.index_path.exists())

    def test_resume_after_report_before_work_finish_keeps_original_report(self):
        """Real CLI runs once; injected crash leaves actual finished execution/EVD."""
        selected = [next(c for c in case_catalog() if c["id"] == "TC-PLC-TOTAL")]
        with patch("scripts.validate_python_lifecycle.case_catalog", return_value=selected):
            self.prepare()
            actual_api = self.harness.api

            def crash_before_finish(command, data, label):
                if label == "execution-work-finish":
                    raise RuntimeError("simulated crash after durable report and evidence")
                return actual_api(command, data, label)

            with patch.object(self.harness, "api", side_effect=crash_before_finish):
                with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                    self.harness.execute("synthetic-fixture-tester", "Synthetic isolated crash-window contract")
            path = self.directory / "docs" / "test-report.md"
            original_report = path.read_bytes()
            before = self.harness.runtime.lifecycle_snapshot(self.harness.index["project_id"], limit=500)
            self.assertEqual(len(before["test_executions"]), 1)
            self.assertEqual(before["test_executions"][0]["status"], "FINISHED")
            resumed = PythonLifecycle(self.harness.output)
            with patch.object(resumed, "run_case", side_effect=AssertionError("finished application execution must not run twice")):
                result = resumed.execute("synthetic-fixture-tester", "Synthetic isolated crash-window contract")
            self.assertTrue(result["executed"])
            self.assertEqual(result["counts"]["PASS"], 1)
            self.assertEqual(path.read_bytes(), original_report)
            after = resumed.runtime.lifecycle_snapshot(resumed.index["project_id"], limit=500)
            self.assertEqual(after["test_executions"], before["test_executions"])

    def test_resume_after_work_finish_before_index_save_never_reclaims_done_work(self):
        selected = [next(c for c in case_catalog() if c["id"] == "TC-PLC-TOTAL")]
        with patch("scripts.validate_python_lifecycle.case_catalog", return_value=selected):
            self.prepare()
            original_save = self.harness.save

            def crash_on_completion_index():
                if self.harness.index.get("executed"):
                    raise RuntimeError("simulated crash before completion index persistence")
                original_save()

            with patch.object(self.harness, "save", side_effect=crash_on_completion_index):
                with self.assertRaisesRegex(RuntimeError, "completion index"):
                    self.harness.execute("synthetic-fixture-tester", "Synthetic post-finish crash contract")
            report_path = self.directory / "docs" / "test-report.md"
            original_report = report_path.read_bytes()
            before = self.harness.runtime.lifecycle_snapshot(self.harness.index["project_id"], limit=500)
            resumed = PythonLifecycle(self.harness.output)
            self.assertFalse(resumed.index.get("executed"))
            with patch.object(resumed, "run_case", side_effect=AssertionError("must preserve finished process")):
                result = resumed.execute("synthetic-fixture-tester", "Synthetic post-finish crash contract")
            self.assertTrue(result["executed"])
            self.assertEqual(report_path.read_bytes(), original_report)
            after = resumed.runtime.lifecycle_snapshot(resumed.index["project_id"], limit=500)
            self.assertEqual(after["test_executions"], before["test_executions"])
            self.assertEqual(after["work_orders"], before["work_orders"])

    def test_resume_rejects_tampered_report_without_overwriting_it(self):
        selected = [next(c for c in case_catalog() if c["id"] == "TC-PLC-TOTAL")]
        with patch("scripts.validate_python_lifecycle.case_catalog", return_value=selected):
            self.prepare()
            self.harness.execute("synthetic-fixture-tester", "Synthetic report tamper contract")
            path = self.directory / "docs" / "test-report.md"
            tampered = path.read_bytes().replace(b'"PASS": 1', b'"PASS": 999', 1)
            path.write_bytes(tampered)
            resumed = PythonLifecycle(self.harness.output)
            with patch.object(resumed, "run_case", side_effect=AssertionError("must not execute to conceal changed evidence")):
                with self.assertRaisesRegex(ValueError, "report content"):
                    resumed.execute("synthetic-fixture-tester", "Synthetic report tamper contract")
            self.assertEqual(path.read_bytes(), tampered)

    def test_resume_rejects_new_case_version_instead_of_reusing_old_pass(self):
        selected = [next(c for c in case_catalog() if c["id"] == "TC-PLC-TOTAL")]
        with patch("scripts.validate_python_lifecycle.case_catalog", return_value=selected):
            self.prepare()
            self.harness.execute("synthetic-fixture-tester", "Synthetic stale-case contract")
            self.harness.runtime.execute("test_case.revise", {"case_id": "TC-PLC-TOTAL", "expected_version": 1,
                "reason": "Synthetic contract: revised acceptance requires new evidence", "expected_result": "A revised expectation, not covered by prior execution"})
            path = self.directory / "docs" / "test-report.md"
            original_report = path.read_bytes()
            resumed = PythonLifecycle(self.harness.output)
            with patch.object(resumed, "run_case", side_effect=AssertionError("must not silently reinterpret original execution")):
                with self.assertRaisesRegex(ValueError, "case/execution versions"):
                    resumed.execute("synthetic-fixture-tester", "Synthetic stale-case contract")
            self.assertEqual(path.read_bytes(), original_report)

    def test_resume_accepts_legacy_report_without_additive_freshness_annotations(self):
        """Persist through an older projection, then resume through today's API."""
        selected = [next(c for c in case_catalog() if c["id"] == "TC-PLC-TOTAL")]

        def legacy_projection(snapshot):
            report = lifecycle_report(snapshot)
            for row in report["case_results"]:
                for key in ("observed_result", "freshness", "freshness_reason"):
                    row.pop(key, None)
            return report

        with patch("scripts.validate_python_lifecycle.case_catalog", return_value=selected):
            self.prepare()
            with patch("scripts.validate_python_lifecycle.lifecycle_report", side_effect=legacy_projection):
                self.harness.execute("synthetic-fixture-tester", "Synthetic legacy report contract")
            path = self.directory / "docs" / "test-report.md"
            original_report = path.read_bytes()
            self.assertNotIn(b'"observed_result"', original_report)
            before = self.harness.runtime.lifecycle_snapshot(self.harness.index["project_id"], limit=500)
            resumed = PythonLifecycle(self.harness.output)
            with patch.object(resumed, "run_case", side_effect=AssertionError("legacy report must not replay completed CLI")):
                result = resumed.execute("synthetic-fixture-tester", "Synthetic legacy report contract")
            self.assertEqual(result["counts"]["PASS"], 1)
            self.assertEqual(path.read_bytes(), original_report)
            after = resumed.runtime.lifecycle_snapshot(resumed.index["project_id"], limit=500)
            self.assertEqual(after["test_executions"], before["test_executions"])

    def test_compatible_annotations_never_hide_bound_result_or_reference_changes(self):
        historical = {"case_id": "TC-FIXTURE", "case_version": 1, "result": "PASS",
            "execution_id": "execution-fixture", "evidence_refs": [{"id": "EVD-FIXTURE", "type": "EVIDENCE", "version": 1}],
            "requirement_refs": [{"id": "REQ-FIXTURE", "type": "REQ", "version": 1}]}
        current = dict(historical, observed_result="PASS", freshness="CURRENT", freshness_reason=None)
        normalize = self.harness.stable_result_rows
        self.assertEqual(normalize([historical]), normalize([current]))
        for field, value in (("case_version", 2), ("result", "BLOCKED"), ("observed_result", "FAIL"),
                             ("execution_id", "another-execution"), ("evidence_refs", []), ("requirement_refs", [])):
            with self.subTest(field=field):
                self.assertNotEqual(normalize([historical]), normalize([dict(current, **{field: value})]))
        for change in ({"freshness": "STALE"}, {"freshness_reason": "changed content"}):
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, "stale or unverifiable"):
                    normalize([dict(current, **change)])

    def test_resume_rejects_stale_execution_evidence_without_rewriting_history(self):
        selected = [next(c for c in case_catalog() if c["id"] == "TC-PLC-TOTAL")]
        with patch("scripts.validate_python_lifecycle.case_catalog", return_value=selected):
            self.prepare()
            self.harness.execute("synthetic-fixture-tester", "Synthetic evidence drift contract")
            snapshot = self.harness.runtime.lifecycle_snapshot(self.harness.index["project_id"], limit=500)
            execution = snapshot["test_executions"][0]
            evidence_id = execution["evidence_refs"][0]["id"]
            evidence = next(e for e in snapshot["evidence"] if e["id"] == evidence_id)
            evidence_path = ROOT / evidence["locator"]["path"]
            evidence_path.write_bytes(evidence_path.read_bytes() + b"\n")
            path = self.directory / "docs" / "test-report.md"
            original_report = path.read_bytes()
            resumed = PythonLifecycle(self.harness.output)
            with patch.object(resumed, "run_case", side_effect=AssertionError("must not rerun to conceal evidence drift")):
                with self.assertRaisesRegex(ValueError, "current.*evidence|current case/execution"):
                    resumed.execute("synthetic-fixture-tester", "Synthetic evidence drift contract")
            self.assertEqual(path.read_bytes(), original_report)
            after = resumed.runtime.lifecycle_snapshot(resumed.index["project_id"], limit=500)
            self.assertEqual(after["test_executions"], snapshot["test_executions"])


if __name__ == "__main__":
    unittest.main()
