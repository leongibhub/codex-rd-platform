"""REQ-V3-021 policy tests using isolated Runtime databases only.

Fixture approvals/evidence in this module prove command contracts; they are
not human approvals, Gate decisions, deployments or acceptance for this repo.
"""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from rd_platform.lifecycle_governance import POLICY
from rd_platform.orchestration import start_project
from rd_platform.runtime import Runtime


def ref(kind, ident, version=1):
    return {"type": kind, "id": ident, "version": version}


class StrictOrchestrationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.root / "state.db")
        self.started = start_project(
            self.runtime, name="strict fixture", idea="test policy", repository_root=self.root,
            request_id="strict-policy-bootstrap",
        )
        self.project = self.started["project_id"]
        self.orchestrator = "orchestrator:" + self.project
        for ident, role in (("research", "researcher"), ("review", "reviewer"),
                            ("test", "tester"), ("dev", "developer"), ("product", "product_manager"),
                            ("docs", "documentation_manager")):
            self.runtime.execute("agent.register", {"id": ident, "role": role})

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, ident, kind="DOC", state="DRAFT", actor=None):
        return self.runtime.execute("artifact.create", {
            "project_id": self.project, "artifact_id": ident, "artifact_type": kind,
            "title": ident, "state": state,
            "content_ref": {"inline_json": {"fixture": "strict policy isolated test"}},
            "source": {"kind": "host", "actor": actor or self.orchestrator},
        })

    def evidence(self, kind, actor, metadata):
        return self.runtime.execute("evidence.register", {
            "project_id": self.project, "kind": kind, "status": "VERIFIED",
            "source": {"kind": "host", "actor": actor},
            "locator": {"inline_json": {"fixture": "isolated, not a real project fact"}},
            "observed_at": datetime.now(timezone.utc).isoformat(), "metadata": metadata,
        })

    def finish_work(self, work, agent, output):
        claim = self.runtime.execute("work.claim", {
            "work_order_id": work["id"], "agent_id": agent, "lease_seconds": 60,
        })
        return self.runtime.execute("work.finish", {
            "work_order_id": work["id"], "agent_id": agent, "lease_token": claim["lease_token"],
            "status": "DONE", "output_refs": [output], "summary": "candidate draft only",
        })

    def pass_g0_fixture(self, artifact_id="DOC-G0-EVIDENCE", subject=None):
        """A narrow synthetic Gate fixture; no human approval is involved."""
        if subject is None:
            baseline = self.runtime.lifecycle_snapshot(self.project)["artifacts"]
            current = next((item for item in baseline if item["id"] == artifact_id), None)
            if current is None:
                current = self.artifact(artifact_id, state="BASELINED")
            subject = [ref("DOC", current["id"], current["version"])]
        self.pass_gate_fixture("G0", subject)

    def pass_gate_fixture(self, gate_id, subject):
        self.evidence("document", self.orchestrator, {
            "gate_id": gate_id, "criteria": list(POLICY[gate_id]), "artifact_refs": subject,
        })
        assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": gate_id})
        self.assertEqual("PASS", assessment["candidate"])
        decision = self.evidence("gate_decision", "review", {
            "assessment_id": assessment["id"], "status": "PASS", "artifact_refs": subject,
        })
        self.runtime.execute("gate.decide", {
            "assessment_id": assessment["id"], "status": "PASS", "decided_by": "review",
            "decision_evidence_refs": [ref("EVIDENCE", decision["id"])],
        })

    def adopted_case_handoff(self, change=None, suffix=""):
        """Build one isolated G0 TEST_CASE candidate and current G0 adoption."""
        requirement = self.artifact("REQ-CASE-SEMANTIC-001" + suffix, kind="REQ", state="BASELINED", actor="dev")
        alternate = self.artifact("REQ-CASE-SEMANTIC-002" + suffix, kind="REQ", state="BASELINED", actor="dev")
        self.runtime.execute("test_model.create", {
            "project_id": self.project, "artifact_id": "TM-CASE-SEMANTIC-001" + suffix,
            "source": {"kind": "host", "actor": "test"},
            "requirement_refs": [requirement["id"], alternate["id"]], "function_tree": {"name": "case adoption"},
            "risks": [{"risk_id": "RISK-CASE", "description": "adoption", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": [requirement["id"]]}],
            "objects": [{"object_id": "OBJ-CASE", "description": "case"}], "types": ["FUNCTIONAL"],
            "test_points": [{"point_id": "TP-CASE", "object_id": "OBJ-CASE", "type": "FUNCTIONAL", "rationale": "handoff", "risk_refs": ["RISK-CASE"], "requirement_refs": [requirement["id"], alternate["id"]], "coverage_rule": "all"}],
        })
        case = self.runtime.execute("test_case.create", {
            "project_id": self.project, "case_id": "TC-CASE-SEMANTIC-001" + suffix, "test_model_id": "TM-CASE-SEMANTIC-001" + suffix, "test_point_refs": ["TP-CASE"],
            "requirement_refs": [requirement["id"]], "test_type": "FUNCTIONAL", "module": "policy", "priority": "P0", "risk": "HIGH",
            "preconditions": ["fixture available"], "test_data": {"input": "fixture"},
            "steps": [{"order": 1, "action": "execute original", "expected_observation": "original observation"}],
            "expected_result": "original result", "automation": {"status": "MANUAL"}, "state": "DRAFT",
        })
        g0 = self.runtime.execute("work.create", {
            "project_id": self.project, "gate_id": "G0", "activity": "candidate test case", "required_role": "tester",
            "why": "prove versioned test-case handoff", "input_refs": [], "dependencies": [],
            "output_contract": {"required_types": ["TEST_CASE"], "min_outputs": 1},
        })
        self.finish_work(g0, "test", ref("TEST_CASE", case["id"]))
        revision_data = dict(case, expected_version=1, reason="independent state adoption", state="BASELINED")
        if change:
            revision_data.update(change(requirement, alternate))
        adopted = self.runtime.execute("test_case.revise", revision_data)
        self.pass_g0_fixture(subject=[ref("TEST_CASE", adopted["id"], adopted["version"])])
        downstream = self.runtime.execute("work.create", {
            "project_id": self.project, "gate_id": "G1", "activity": "consume adopted case", "required_role": "researcher",
            "why": "strict downstream handoff", "input_refs": [], "dependencies": [g0["id"]],
            "output_contract": {"required_types": ["DOC"], "min_outputs": 1},
        })
        return downstream, adopted

    def test_test_case_adoption_allows_governance_only_change_and_locks_current_version(self):
        downstream, adopted = self.adopted_case_handoff()
        claim = self.runtime.execute("work.claim", {"work_order_id": downstream["id"], "agent_id": "research", "lease_seconds": 60})
        self.assertEqual([ref("TEST_CASE", adopted["id"], 2)], claim["dependency_input_refs"])

    def test_test_case_adoption_rejects_all_semantic_drift(self):
        changes = {
            "steps": lambda requirement, alternate: {"steps": [{"order": 1, "action": "changed step", "expected_observation": "original observation"}]},
            "expected_result": lambda requirement, alternate: {"expected_result": "changed result"},
            "requirement_refs": lambda requirement, alternate: {"requirement_refs": [alternate["id"]]},
        }
        for name, change in changes.items():
            with self.subTest(field=name):
                downstream, _ = self.adopted_case_handoff(change, "-" + name.upper())
                with self.assertRaisesRegex(ValueError, "STRICT_POLICY_STAGE_OUTPUT_ADOPTION_DRIFT:TC-CASE-SEMANTIC-001-" + name.upper()):
                    self.runtime.execute("work.claim", {"work_order_id": downstream["id"], "agent_id": "research", "lease_seconds": 60})

    def adopted_g0_document(self):
        g0 = self.started["work_orders"][0]
        candidate = self.artifact("DOC-G0-RECOVERY")
        self.finish_work(g0, self.orchestrator, ref("DOC", candidate["id"]))
        adopted = self.runtime.execute("artifact.revise", {
            "artifact_id": candidate["id"], "expected_version": 1, "state": "BASELINED",
            "content_ref": {"inline_json": {"fixture": "strict policy isolated test"}},
            "reason": "fixture adoption", "material": False,
        })
        self.pass_g0_fixture(adopted["id"])
        return g0

    def test_internal_gate_remediation_and_work_rollback_bind_real_predecessor_handoff(self):
        g0 = self.adopted_g0_document()
        assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": "G1"})
        self.assertEqual("BLOCKED", assessment["candidate"])
        self.runtime.execute("gate.decide", {
            "assessment_id": assessment["id"], "status": "FAIL", "decided_by": "review",
            "decision_evidence_refs": [], "reason": "synthetic missing G1 evidence", "resolution": "create real evidence",
        })
        remediation = next(work for work in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if work["activity"] == "remediate gate G1")
        self.assertEqual([g0["id"]], remediation["dependencies"])
        self.runtime.execute("work.claim", {"work_order_id": remediation["id"], "agent_id": "docs", "lease_seconds": 60})

        # The same internal dependency binding prevents work.rollback from
        # constructing a strict G1 compensation order that can never claim.
        original = self.started["work_orders"][1]
        rollback = self.runtime.execute("work.control", {
            "work_order_id": original["id"], "action": "rollback", "reason": "isolated recovery fixture",
        })
        compensation = next(work for work in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if work["id"] == rollback["compensation_work_id"])
        self.assertEqual([g0["id"]], compensation["dependencies"])
        self.runtime.execute("work.claim", {"work_order_id": compensation["id"], "agent_id": "research", "lease_seconds": 60})

    def test_lifecycle_rollback_compensation_binds_real_predecessor_handoff(self):
        g0 = self.adopted_g0_document()
        g1 = self.started["work_orders"][1]
        candidate = self.artifact("DOC-G1-ROLLBACK")
        self.finish_work(g1, "research", ref("DOC", candidate["id"]))
        adopted = self.runtime.execute("artifact.revise", {
            "artifact_id": candidate["id"], "expected_version": 1, "state": "BASELINED",
            "content_ref": {"inline_json": {"fixture": "strict policy isolated test"}},
            "reason": "fixture adoption", "material": False,
        })
        self.pass_gate_fixture("G1", [ref("DOC", adopted["id"], adopted["version"])])
        change = self.artifact("CR-ROLLBACK-STRICT-001", kind="CR", state="BASELINED")
        result = self.runtime.execute("lifecycle.control", {
            "project_id": self.project, "action": "rollback", "target_gate": "G1",
            "reason": "isolated strict recovery", "change_id": change["id"],
            "affected_refs": [ref("DOC", adopted["id"], adopted["version"])],
        })
        compensation = next(work for work in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if work["id"] == result["compensation_work_id"])
        self.assertEqual([g0["id"]], compensation["dependencies"])
        self.runtime.execute("work.claim", {"work_order_id": compensation["id"], "agent_id": "docs", "lease_seconds": 60})

    def test_raw_work_claim_cannot_bypass_predecessor_gate_and_done_is_only_candidate(self):
        g0, g1, g2 = self.started["work_orders"][:3]
        candidate = self.artifact("DOC-G0-CANDIDATE")
        self.finish_work(g0, self.orchestrator, ref("DOC", candidate["id"]))
        adopted = self.runtime.execute("artifact.revise", {
            "artifact_id": candidate["id"], "expected_version": 1, "state": "BASELINED",
            "content_ref": {"inline_json": {"fixture": "strict policy isolated test"}},
            "reason": "independent fixture adoption", "material": False,
        })
        self.pass_g0_fixture(adopted["id"])

        g1_candidate = self.artifact("DOC-G1-CANDIDATE", actor="research")
        claim = self.runtime.execute("work.claim", {"work_order_id": g1["id"], "agent_id": "research", "lease_seconds": 60})
        self.assertEqual([ref("DOC", candidate["id"], 2)], claim["dependency_input_refs"])
        self.runtime.execute("work.finish", {"work_order_id": g1["id"], "agent_id": "research", "lease_token": claim["lease_token"],
            "status": "DONE", "output_refs": [ref("DOC", g1_candidate["id"])], "summary": "candidate draft only"})
        self.assertEqual("DONE", self.runtime.lifecycle_snapshot(self.project)["work_orders"][0]["status"])
        # This is a direct raw Runtime command, not worker-service filtering.
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_PREDECESSOR_GATE_NOT_PASS:G1"):
            self.runtime.execute("work.claim", {"work_order_id": g2["id"], "agent_id": "product", "lease_seconds": 60})
        self.assertIsNone(next(g for g in self.runtime.lifecycle_snapshot(self.project)["gates"] if g["gate_id"] == "G1")["gate_status"])

    def test_unrelated_gate_evidence_cannot_adopt_or_unlock_predecessor_candidate(self):
        g0, g1 = self.started["work_orders"][:2]
        candidate = self.artifact("DOC-G0-UNADOPTED")
        self.finish_work(g0, self.orchestrator, ref("DOC", candidate["id"]))
        self.pass_g0_fixture()  # Deliberately baselines a different DOC.
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_STAGE_OUTPUT_NOT_ADOPTED:DOC-G0-UNADOPTED"):
            self.runtime.execute("work.claim", {"work_order_id": g1["id"], "agent_id": "research", "lease_seconds": 60})

    def test_adopted_candidate_content_drift_stales_gate_and_blocks_downstream_claim(self):
        g0, g1 = self.started["work_orders"][:2]
        candidate = self.artifact("DOC-G0-DRIFT")
        self.finish_work(g0, self.orchestrator, ref("DOC", candidate["id"]))
        adopted = self.runtime.execute("artifact.revise", {
            "artifact_id": candidate["id"], "expected_version": 1, "state": "BASELINED",
            "content_ref": {"inline_json": {"fixture": "strict policy isolated test"}},
            "reason": "adopt", "material": False,
        })
        self.pass_g0_fixture(adopted["id"])
        change = self.artifact("CR-STRICT-DRIFT", kind="CR", state="BASELINED")
        self.runtime.execute("artifact.revise", {
            "artifact_id": candidate["id"], "expected_version": 2, "state": "APPROVED",
            "content_ref": {"inline_json": {"fixture": "different approved content"}},
            "reason": "scope drift", "material": True, "change_id": change["id"],
        })
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_PREDECESSOR_GATE_NOT_PASS:G0"):
            self.runtime.execute("work.claim", {"work_order_id": g1["id"], "agent_id": "research", "lease_seconds": 60})

    def test_strict_work_rejects_baselined_output_as_agent_completion_authority(self):
        work = self.started["work_orders"][0]
        baseline = self.artifact("DOC-G0-BASELINED", state="BASELINED")
        claim = self.runtime.execute("work.claim", {"work_order_id": work["id"], "agent_id": self.orchestrator, "lease_seconds": 60})
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_WORK_OUTPUT_MUST_REMAIN_DRAFT"):
            self.runtime.execute("work.finish", {
                "work_order_id": work["id"], "agent_id": self.orchestrator, "lease_token": claim["lease_token"],
                "status": "DONE", "output_refs": [ref("DOC", baseline["id"])], "summary": "must reject",
            })

    def test_raw_client_cannot_forge_repair_metadata_to_bypass_gates_or_budget(self):
        base = {
            "project_id": self.project, "gate_id": "G11", "activity": "forged repair",
            "required_role": "developer", "why": "must not be accepted", "input_refs": [], "dependencies": [],
            "output_contract": {"required_types": ["CODE_CHANGE"], "min_outputs": 1},
        }
        for forged in (
            {"repair_defect_id": "BUG-NOT-REAL", "repair_stage": "fix", "source_execution": "execution-not-real"},
            {"repair_defect_id": "BUG-NOT-REAL", "repair_stage": "unknown", "source_execution": "execution-not-real"},
        ):
            with self.assertRaisesRegex(ValueError, "repair metadata is internal only"):
                self.runtime.execute("work.create", {**base, **forged})

    def test_actual_failed_execution_creates_bounded_triage_then_role_separated_repair_chain(self):
        requirement = self.artifact("REQ-STRICT-001", kind="REQ", state="BASELINED", actor="dev")
        self.runtime.execute("test_model.create", {
            "project_id": self.project, "artifact_id": "TM-STRICT-001", "source": {"kind": "host", "actor": "test"},
            "requirement_refs": [requirement["id"]], "function_tree": {"name": "fixture"},
            "risks": [{"risk_id": "RISK-1", "description": "failure", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": [requirement["id"]]}],
            "objects": [{"object_id": "OBJ-1", "description": "input"}], "types": ["FUNCTIONAL"],
            "test_points": [{"point_id": "TP-1", "object_id": "OBJ-1", "type": "FUNCTIONAL", "rationale": "verify", "risk_refs": ["RISK-1"], "requirement_refs": [requirement["id"]], "coverage_rule": "all"}],
        })
        self.runtime.execute("test_case.create", {
            "project_id": self.project, "case_id": "TC-STRICT-001", "test_model_id": "TM-STRICT-001", "test_point_refs": ["TP-1"],
            "requirement_refs": [requirement["id"]], "test_type": "FUNCTIONAL", "module": "fixture", "priority": "P0", "risk": "HIGH",
            "preconditions": [], "test_data": {}, "steps": [{"order": 1, "action": "run", "expected_observation": "pass"}],
            "expected_result": "pass", "automation": {"status": "MANUAL"}, "state": "BASELINED",
        })
        env = self.evidence("test_environment", "test", {"artifact_refs": [ref("REQ", requirement["id"])]})
        execution = self.runtime.execute("test_execution.start", {
            "case_id": "TC-STRICT-001", "case_version": 1, "executor_id": "test", "environment_ref": ref("EVIDENCE", env["id"]),
        })
        result = self.evidence("test_execution", "test", {
            "execution_id": execution["id"], "result": "FAIL", "artifact_refs": [ref("TEST_CASE", "TC-STRICT-001")],
        })
        completed = self.runtime.execute("test_execution.finish", {
            "execution_id": execution["id"], "result": "FAIL", "actual_result": "isolated failure", "evidence_refs": [ref("EVIDENCE", result["id"])],
        })
        defect_id = completed["defect_id"]
        works = [w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == defect_id]
        self.assertEqual(["triage"], [w["repair_stage"] for w in works])
        triage_claim = self.runtime.execute("work.claim", {
            "work_order_id": works[0]["id"], "agent_id": "test", "lease_seconds": 60,
        })
        classification = self.evidence("document", "test", {"artifact_refs": [ref("REQ", requirement["id"])]})
        self.runtime.execute("defect.classify", {
            "defect_id": defect_id, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer",
            "rationale": "isolated fixture classification", "classified_by": "test", "evidence_refs": [ref("EVIDENCE", classification["id"])],
        })
        works = [w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == defect_id]
        stages = {w["repair_stage"]: w for w in works}
        self.assertEqual({"triage", "fix", "retest", "review"}, set(stages))
        self.assertEqual("developer", stages["fix"]["required_role"])
        self.assertEqual("tester", stages["retest"]["required_role"])
        self.assertEqual("reviewer", stages["review"]["required_role"])
        self.assertEqual([stages["fix"]["id"]], stages["retest"]["dependencies"])
        self.assertEqual([stages["retest"]["id"]], stages["review"]["dependencies"])
        fix_claim = self.runtime.execute("work.claim", {
            "work_order_id": stages["fix"]["id"], "agent_id": "dev", "lease_seconds": 60,
        })
        with self.assertRaisesRegex(ValueError, "classified defect repair chain is immutable"):
            self.runtime.execute("defect.classify", {
                "defect_id": defect_id, "category": "PERFORMANCE", "severity": "MAJOR", "owner_role": "architect",
                "rationale": "material owner change", "classified_by": "test", "evidence_refs": [ref("EVIDENCE", classification["id"])],
            })
        # The rejected mutation does not invalidate the already-assigned
        # developer lease or silently move its responsibility to another role.
        self.runtime.execute("work.heartbeat", {
            "work_order_id": stages["fix"]["id"], "agent_id": "dev", "lease_token": fix_claim["lease_token"],
        })
        # A classification received while a triage worker has a lease emits the
        # standard invalidation fact; its old token cannot heartbeat/finish and
        # the now-superseded triage cannot be retried into a second worker.
        with self.assertRaisesRegex(ValueError, "stale or invalid work lease"):
            self.runtime.execute("work.heartbeat", {
                "work_order_id": stages["triage"]["id"], "agent_id": "test", "lease_token": triage_claim["lease_token"],
            })
        for action, extra in (("retry", {}), ("reassign", {"agent_id": "test"}),
                              ("modify", {"input_refs": []}), ("rollback", {})):
            expected = "reconcile original external outcome before compensation" if action == "rollback" else "classified defect triage is superseded and cannot be made executable"
            with self.assertRaisesRegex(ValueError, expected):
                self.runtime.execute("work.control", {
                    "work_order_id": stages["triage"]["id"], "action": action, "reason": "must not replay", **extra,
                })
        # Reclassification retains one bounded chain, rather than recursively
        # enqueueing repairs from a stale/failed result.
        self.runtime.execute("defect.classify", {
            "defect_id": defect_id, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer",
            "rationale": "isolated fixture classification", "classified_by": "test", "evidence_refs": [ref("EVIDENCE", classification["id"])],
        })
        repeated = [w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == defect_id]
        self.assertEqual(4, len(repeated))
        def later_failure(label, case_id="TC-STRICT-001"):
            environment = self.evidence("test_environment", "test", {"artifact_refs": [ref("REQ", requirement["id"])]})
            execution = self.runtime.execute("test_execution.start", {
                "case_id": case_id, "case_version": 1, "executor_id": "test", "environment_ref": ref("EVIDENCE", environment["id"]),
            })
            evidence = self.evidence("test_execution", "test", {
                "execution_id": execution["id"], "result": "FAIL", "artifact_refs": [ref("TEST_CASE", case_id)],
            })
            return self.runtime.execute("test_execution.finish", {
                "execution_id": execution["id"], "result": "FAIL", "actual_result": label, "evidence_refs": [ref("EVIDENCE", evidence["id"])],
            })["defect_id"]

        # Three exact-case cycles are bounded but automatic; the fourth still
        # preserves its FAIL/defect history and escalates without new worker
        # work, preventing an infinite external-cost retry loop.
        defect2 = later_failure("second isolated failure")
        self.assertNotEqual(defect_id, defect2)
        self.runtime.execute("defect.classify", {
            "defect_id": defect2, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer",
            "rationale": "second classification", "classified_by": "test", "evidence_refs": [ref("EVIDENCE", classification["id"])],
        })
        defect3 = later_failure("third isolated failure")
        self.runtime.execute("defect.classify", {
            "defect_id": defect3, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer",
            "rationale": "third classification", "classified_by": "test", "evidence_refs": [ref("EVIDENCE", classification["id"])],
        })
        for item in (defect2, defect3):
            self.assertEqual(4, len([w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == item]))
        defect4 = later_failure("fourth failure must escalate")
        self.assertEqual([], [w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == defect4])
        self.assertEqual("PENDING_HUMAN", next(b for b in self.runtime.lifecycle_snapshot(self.project)["defects"] if b["id"] == defect4)["repair_disposition"])
        events = self.runtime.lifecycle_snapshot(self.project)["events"]
        self.assertTrue(any(event["type"] == "defect.repair_escalated" and event["entity_id"] == defect4 for event in events))
        self.runtime.execute("test_case.create", {
            "project_id": self.project, "case_id": "TC-STRICT-002", "test_model_id": "TM-STRICT-001", "test_point_refs": ["TP-1"],
            "requirement_refs": [requirement["id"]], "test_type": "FUNCTIONAL", "module": "fixture", "priority": "P0", "risk": "HIGH",
            "preconditions": [], "test_data": {}, "steps": [{"order": 1, "action": "run distinct", "expected_observation": "pass"}],
            "expected_result": "pass", "automation": {"status": "MANUAL"}, "state": "BASELINED",
        })
        distinct = later_failure("distinct case receives its own budget", "TC-STRICT-002")
        self.assertEqual(1, len([w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == distinct]))


if __name__ == "__main__":
    unittest.main()
