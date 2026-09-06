"""Black-box lifecycle contracts derived from DES-V3-001, not developer claims."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from rd_platform.runtime import Runtime


class IndependentLifecycleTests(unittest.TestCase):
    """TC-V3-IND-301..305 / REQ-V3-001..009 / NFR-V3-003..005."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-lifecycle-")
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.root / "state.db")
        self.project = self.runtime.execute("project.create", {"name": "independent lifecycle", "idea": "contract testing"})["id"]
        self.other_project = self.runtime.execute("project.create", {"name": "isolated lifecycle", "idea": "isolation testing"})["id"]
        for identity, role in (("ind-dev", "developer"), ("ind-test", "tester"), ("ind-review", "reviewer")):
            self.runtime.execute("agent.register", {"id": identity, "role": role})
        for project in (self.project, self.other_project):
            self.runtime.execute("lifecycle.initialize", {"project_id": project, "repository_root": str(self.root), "mode": "active"})

    def tearDown(self):
        self.temp.cleanup()

    def ref(self, entity_type, entity_id, version=1):
        return {"type": entity_type, "id": entity_id, "version": version}

    def artifact(self, entity_id, entity_type="REQ", *, project=None, payload=None):
        return self.runtime.execute("artifact.create", {
            "project_id": project or self.project,
            "artifact_id": entity_id,
            "artifact_type": entity_type,
            "title": entity_id,
            "state": "BASELINED",
            "content_ref": {"inline_json": payload if payload is not None else {"acceptance": "observable"}},
            "source": {"kind": "host", "actor": "ind-dev"},
        })

    def evidence(self, *, kind="test_execution", actor="ind-test", metadata=None):
        created = self.runtime.execute("evidence.register", {
            "project_id": self.project,
            "kind": kind,
            "status": "VERIFIED",
            "source": {"kind": "host", "actor": actor},
            "locator": {"inline_json": {"fixture": "independent contract test, not external approval"}},
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        })
        return self.ref("EVIDENCE", created["id"])

    def make_case(self, case_id="TC-IND-001"):
        if not any(a["id"] == "REQ-IND-001" for a in self.runtime.lifecycle_snapshot(self.project)["artifacts"]):
            self.artifact("REQ-IND-001")
        if not self.runtime.lifecycle_snapshot(self.project)["test_models"]:
            self.runtime.execute("test_model.create", {
                "project_id": self.project, "artifact_id": "TM-IND-001", "source": {"kind": "host", "actor": "ind-test"}, "requirement_refs": ["REQ-IND-001"],
                "function_tree": {"name": "lifecycle", "children": ["execution"]},
                "objects": [{"object_id": "OBJ-IND-001", "description": "public runtime interface"}],
                "risks": [{"risk_id": "RISK-IND-001", "description": "false test evidence", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": ["REQ-IND-001"]}],
                "types": ["FUNCTIONAL", "SECURITY"],
                "test_points": [{"point_id": "TP-IND-001", "object_id": "OBJ-IND-001", "type": "FUNCTIONAL", "rationale": "exercise evidence contract", "risk_refs": ["RISK-IND-001"], "requirement_refs": ["REQ-IND-001"], "coverage_rule": "all result states"}],
            })
        return self.runtime.execute("test_case.create", {
            "project_id": self.project, "case_id": case_id, "test_model_id": "TM-IND-001",
            "test_point_refs": ["TP-IND-001"], "requirement_refs": ["REQ-IND-001"],
            "test_type": "FUNCTIONAL", "module": "runtime", "priority": "P0", "risk": "HIGH",
            "preconditions": [], "test_data": {},
            "steps": [{"order": 1, "action": "invoke public Runtime API", "expected_observation": "contract result"}],
            "expected_result": "evidence is validated", "automation": {"status": "MANUAL"}, "state": "BASELINED",
        })

    def execute_case(self, case_id, result):
        environment = self.evidence(kind="test_environment")
        execution = self.runtime.execute("test_execution.start", {
            "case_id": case_id, "case_version": 1, "executor_id": "ind-test", "environment_ref": environment,
        })
        evidence = self.evidence(metadata={"execution_id": execution["id"], "result": result, "artifact_refs": [self.ref("TEST_CASE", case_id)]})
        return self.runtime.execute("test_execution.finish", {
            "execution_id": execution["id"], "result": result, "actual_result": "independent isolated execution", "evidence_refs": [evidence],
        })

    def completed_synthetic_fix_quality_task(self, bug_id):
        """Build a local synthetic V2 chain; it is fixture data, not project evidence."""
        quality = self.runtime.execute("task.create", {
            "project_id": self.project, "title": "synthetic completed defect repair", "why": "exercise strict lifecycle contract",
            "role": "developer", "requirements": ["REQ-IND-001"], "dependencies": [],
            "inputs": {"fix_defect_id": bug_id, "lifecycle_task_ref": self.ref("TASK", "TASK-IND-001")},
        })
        self.artifact("TASK-IND-001", "TASK", payload={"defect_id": bug_id, "requirement_refs": ["REQ-IND-001"], "quality_task_id": quality["id"]})
        for phase, agent in (("implementation", "ind-dev"), ("unit", "ind-test"), ("integration", "ind-test"), ("review", "ind-review")):
            run = self.runtime.execute("run.start", {"task_id": quality["id"], "agent_id": agent, "phase": phase})
            self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "synthetic local fixture quality phase", "evidence": {"synthetic_fixture": True, "result": "PASS"}})
        return quality

    def test_tc_v3_ind_301_cross_project_refs_rejected_and_unrelated_branch_survives_revision(self):
        self.artifact("REQ-IND-001")
        self.artifact("DES-IND-001", "DES")
        self.artifact("REQ-IND-002")
        self.artifact("DES-IND-002", "DES")
        link_one = {"project_id": self.project, "from": self.ref("REQ", "REQ-IND-001"), "to": self.ref("DES", "DES-IND-001"), "relation": "realized_by"}
        link_two = {"project_id": self.project, "from": self.ref("REQ", "REQ-IND-002"), "to": self.ref("DES", "DES-IND-002"), "relation": "realized_by"}
        self.runtime.execute("trace.link", link_one)
        self.runtime.execute("trace.link", link_two)
        with self.assertRaisesRegex(ValueError, "another project"):
            self.runtime.execute("trace.link", dict(link_one, project_id=self.other_project))
        self.make_case()
        self.runtime.execute("artifact.revise", {"artifact_id": "REQ-IND-001", "expected_version": 1, "state": "BASELINED", "content_ref": {"inline_json": {"acceptance": "changed"}}, "reason": "independent change scope", "material": False})
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual("REVIEW_REQUIRED", next(case for case in snapshot["test_cases"] if case["id"] == "TC-IND-001")["status"])
        self.assertEqual("VALID", next(link for link in snapshot["trace_links"] if link["from"]["id"] == "REQ-IND-002")["status"])

    def test_tc_v3_ind_302_execution_defect_resolution_and_closure_require_separate_roles(self):
        self.make_case("TC-IND-001")
        self.make_case("TC-IND-002")
        environment = self.evidence(kind="test_environment")
        with self.assertRaises(ValueError):
            self.runtime.execute("test_execution.start", {"case_id": "TC-IND-001", "case_version": 1, "executor_id": "ind-dev", "environment_ref": environment})
        failed = self.execute_case("TC-IND-001", "FAIL")
        bug_id = failed["defect_id"]
        self.runtime.execute("defect.classify", {"defect_id": bug_id, "category": "PRODUCT", "severity": "CRITICAL", "owner_role": "developer", "rationale": "independent failure classification", "classified_by": "ind-test", "evidence_refs": failed["evidence_refs"]})
        quality = self.completed_synthetic_fix_quality_task(bug_id)
        self.runtime.execute("defect.fix", {"defect_id": bug_id, "fix_task_id": "TASK-IND-001", "completion_task_id": quality["id"], "fixed_by": "ind-dev", "evidence_refs": [self.evidence(kind="document", actor="ind-dev")]})
        retest = self.execute_case("TC-IND-001", "PASS")
        with self.assertRaises(ValueError):
            self.runtime.execute("defect.resolve", {"defect_id": bug_id, "resolved_by": "ind-test", "execution_refs": [self.ref("TEST_EXECUTION", retest["id"]) ]})
        regression = self.execute_case("TC-IND-002", "PASS")
        resolved = self.runtime.execute("defect.resolve", {"defect_id": bug_id, "resolved_by": "ind-test", "execution_refs": [self.ref("TEST_EXECUTION", retest["id"]), self.ref("TEST_EXECUTION", regression["id"])]})
        self.assertEqual("RESOLVED", resolved["status"])
        review = self.evidence(kind="review", actor="ind-review", metadata={"subject_id": bug_id, "result": "PASS", "artifact_refs": [self.ref("BUG", bug_id)]})
        with self.assertRaises(ValueError):
            self.runtime.execute("defect.close", {"defect_id": bug_id, "closed_by": "ind-dev", "evidence_refs": [review]})
        self.assertEqual("CLOSED", self.runtime.execute("defect.close", {"defect_id": bug_id, "closed_by": "ind-review", "evidence_refs": [review]})["status"])

    def test_tc_v3_ind_303_gate_cannot_promote_missing_or_spoofed_evidence(self):
        assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": "G0"})
        self.assertEqual("BLOCKED", assessment["candidate"])
        with self.assertRaises(ValueError):
            self.runtime.execute("gate.decide", {"assessment_id": assessment["id"], "status": "PASS", "decided_by": "ind-review", "decision_evidence_refs": []})
        with self.assertRaises(ValueError):
            self.runtime.execute("evidence.register", {"project_id": self.project, "kind": "human_approval", "status": "VERIFIED"})
        with self.assertRaises(ValueError):
            self.runtime.execute("evidence.register", {"project_id": self.project, "kind": "gate_decision", "status": "VERIFIED", "source": {"kind": "model", "actor": "ind-review"}, "locator": {"inline_json": {"claim": "PASS"}}, "observed_at": datetime.now(timezone.utc).isoformat(), "metadata": {}})

    def test_tc_v3_ind_304_pause_invalidates_lease_and_old_token_cannot_finish(self):
        work = self.runtime.execute("work.create", {"project_id": self.project, "gate_id": "G0", "activity": "implementation", "required_role": "developer", "why": "verify pause boundary", "input_refs": [], "dependencies": [], "output_contract": {"required_types": ["REQ"], "min_outputs": 1}})
        first = self.runtime.execute("work.claim", {"work_order_id": work["id"], "agent_id": "ind-dev", "lease_seconds": 60})
        payload = {"work_order_id": work["id"], "agent_id": "ind-dev", "lease_token": first["lease_token"]}
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "pause", "reason": "independent pause"})
        with self.assertRaises(ValueError):
            self.runtime.execute("work.heartbeat", payload)
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "resume", "reason": "independent resume"})
        second = self.runtime.execute("work.claim", {"work_order_id": work["id"], "agent_id": "ind-dev", "lease_seconds": 60})
        self.artifact("REQ-LEASE-001")
        with self.assertRaises(ValueError):
            self.runtime.execute("work.finish", dict(payload, status="DONE", output_refs=[self.ref("REQ", "REQ-LEASE-001")], summary="stale host result"))
        finished = self.runtime.execute("work.finish", {"work_order_id": work["id"], "agent_id": "ind-dev", "lease_token": second["lease_token"], "status": "DONE", "output_refs": [self.ref("REQ", "REQ-LEASE-001")], "summary": "fresh host result"})
        self.assertEqual("DONE", finished["status"])
        self.assertNotIn("lease_token", str(self.runtime.lifecycle_snapshot(self.project)["work_orders"]))

    def test_tc_v3_ind_305_path_and_secret_boundaries_reject_without_registering_artifact(self):
        with self.assertRaises(ValueError):
            self.artifact("REQ-ESCAPE", payload={"password": "plaintext"})
        with self.assertRaises(ValueError):
            self.runtime.execute("artifact.create", {"project_id": self.project, "artifact_id": "REQ-PATH", "artifact_type": "REQ", "title": "bad path", "state": "BASELINED", "content_ref": {"path": "../outside.md", "sha256": "0" * 64}, "source": {"kind": "host", "actor": "ind-dev"}})
        self.assertNotIn("REQ-ESCAPE", [artifact["id"] for artifact in self.runtime.lifecycle_snapshot(self.project)["artifacts"]])
        self.assertNotIn("REQ-PATH", [artifact["id"] for artifact in self.runtime.lifecycle_snapshot(self.project)["artifacts"]])

    def test_tc_v3_ind_306_generic_api_cannot_create_human_approval_without_trusted_provider(self):
        """A bare operator string is not observable human-approval provenance."""
        approval_subject = self.artifact("DOC-APPROVAL", "DOC")
        with self.assertRaises(ValueError):
            self.runtime.register_human_approval({
                "project_id": self.project, "kind": "human_approval", "status": "VERIFIED",
                "locator": {"inline_json": {"synthetic": "untrusted generic caller"}},
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"gate_id": "G9", "decision": "APPROVE", "statement": "untrusted caller must not approve", "artifact_refs": [self.ref("DOC", approval_subject["id"])]},
            }, operator="arbitrary-local-string")

    def test_tc_v3_ind_307_defect_fix_rejects_draft_task_without_finished_quality_evidence(self):
        """A fix must reference a completed quality task, not merely a TASK artifact."""
        self.make_case()
        failed = self.execute_case("TC-IND-001", "FAIL")
        bug_id = failed["defect_id"]
        self.runtime.execute("defect.classify", {"defect_id": bug_id, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer", "rationale": "needs an implemented repair", "classified_by": "ind-test", "evidence_refs": failed["evidence_refs"]})
        self.artifact("TASK-DRAFT-ONLY", "TASK", payload={"state": "draft-only fixture"})
        with self.assertRaises(ValueError):
            self.runtime.execute("defect.fix", {"defect_id": bug_id, "fix_task_id": "TASK-DRAFT-ONLY", "fixed_by": "ind-dev", "evidence_refs": [self.evidence(kind="document", actor="ind-dev")]})

    def test_tc_v3_ind_308_evidence_registration_never_persists_bearer_credential(self):
        """V3 evidence admission must reject or redact credential-bearing stdout."""
        token = "fixture-sensitive-token"
        try:
            self.runtime.execute("evidence.register", {
                "project_id": self.project, "kind": "document", "status": "VERIFIED",
                "source": {"kind": "host", "actor": "ind-dev"},
                "locator": {"inline_json": {"fixture": "independent output scan"}},
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"stdout": "Authorization: Bearer " + token},
            })
        except ValueError:
            return
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertNotIn(token, str(snapshot["evidence"]))
        self.assertNotIn(token, str(snapshot["events"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
