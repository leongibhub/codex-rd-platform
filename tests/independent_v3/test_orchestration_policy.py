"""Independent tests for REQ-V3-021 strict lifecycle orchestration policy.

All records and the tiny local application in this module live in a temporary
directory.  Synthetic verifier output exercises binding mechanics only; it is
never a human approval, deployment, or acceptance record for this repository.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from rd_platform.lifecycle_base import LifecycleBase
from rd_platform.lifecycle_governance import POLICY, REVIEW_CRITERIA, TEST_CRITERIA
from rd_platform.orchestration import start_project
from rd_platform.runtime import Runtime


def ref(kind: str, ident: str, version: int = 1) -> dict:
    return {"type": kind, "id": ident, "version": version}


class TemporarySyntheticApprovalVerifier:
    """Temporary fixture only; it authenticates no person or real approval."""

    def verify(self, *, binding, approval_request):
        return {
            "authenticated": True,
            "operator": "temporary-synthetic-operator",
            "provider_id": "temporary-synthetic-verifier",
            "verification_id": "temporary-" + binding["gate_id"],
            "binding_digest": LifecycleBase.digest(binding),
        }


class StrictOrchestrationPolicyIndependentTests(unittest.TestCase):
    """Risk-driven host/API boundary tests, independent from implementation tests."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.root / "state.db")
        started = start_project(
            self.runtime,
            name="strict policy independent fixture",
            idea="verify host-enforced lifecycle policy",
            repository_root=self.root,
            request_id="independent-strict-policy",
        )
        self.project = started["project_id"]
        self.work = {row["gate_id"]: row for row in started["work_orders"]}
        self.orchestrator = "orchestrator:" + self.project
        for ident, role in (
            ("research", "researcher"), ("product", "product_manager"),
            ("requirements", "requirement_analyst"), ("architect", "architect"),
            ("developer", "developer"), ("tester", "tester"),
            ("reviewer", "reviewer"), ("release", "release_manager"),
            ("docs", "documentation_manager"),
        ):
            self.runtime.execute("agent.register", {"id": ident, "role": role})

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, ident: str, kind: str = "DOC", *, state: str = "DRAFT", actor: str | None = None, content=None):
        return self.runtime.execute("artifact.create", {
            "project_id": self.project,
            "artifact_id": ident,
            "artifact_type": kind,
            "title": ident,
            "state": state,
            "content_ref": {"inline_json": content if content is not None else {"fixture": ident}},
            "source": {"kind": "host", "actor": actor or self.orchestrator},
        })

    def evidence(self, kind: str, actor: str, metadata: dict, *, observed_at: str | None = None):
        return self.runtime.execute("evidence.register", {
            "project_id": self.project,
            "kind": kind,
            "status": "VERIFIED",
            "source": {"kind": "host", "actor": actor},
            "locator": {"inline_json": {"fixture": "independent temporary test only"}},
            "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
        })

    def pass_g0(self, candidate_id: str | None = None):
        if candidate_id:
            candidate = next(a for a in self.runtime.lifecycle_snapshot(self.project)["artifacts"] if a["id"] == candidate_id)
            subject = self.runtime.execute("artifact.revise", {"artifact_id": candidate_id, "expected_version": candidate["version"], "state": "BASELINED", "content_ref": candidate["content_ref"], "reason": "temporary candidate adoption", "material": False})
        else:
            subject = self.artifact("DOC-G0-STRICT", state="BASELINED")
        subject_ref = [ref("DOC", subject["id"], subject["version"])]
        self.evidence("document", self.orchestrator, {
            "gate_id": "G0", "criteria": list(POLICY["G0"]), "artifact_refs": subject_ref,
        })
        assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": "G0"})
        self.assertEqual("PASS", assessment["candidate"])
        decision = self.evidence("gate_decision", "reviewer", {
            "assessment_id": assessment["id"], "status": "PASS", "artifact_refs": subject_ref,
        })
        self.runtime.execute("gate.decide", {
            "assessment_id": assessment["id"], "status": "PASS", "decided_by": "reviewer",
            "decision_evidence_refs": [ref("EVIDENCE", decision["id"])],
        })
        return subject

    def claim(self, work, agent: str):
        return self.runtime.execute("work.claim", {
            "work_order_id": work["id"], "agent_id": agent, "lease_seconds": 60,
        })

    def finish(self, work, agent: str, claim: dict, output: dict):
        return self.runtime.execute("work.finish", {
            "work_order_id": work["id"], "agent_id": agent,
            "lease_token": claim["lease_token"], "status": "DONE",
            "output_refs": [output], "summary": "temporary candidate handoff",
        })

    def model_case_and_pass_execution(self, *, case_id="TC-POLICY-001"):
        requirement = self.artifact("REQ-POLICY-001", "REQ", state="BASELINED", actor="developer")
        self.runtime.execute("test_model.create", {
            "project_id": self.project, "artifact_id": "TM-POLICY-001",
            "source": {"kind": "host", "actor": "tester"}, "requirement_refs": [requirement["id"]],
            "function_tree": {"name": "policy", "children": ["lifecycle"]},
            "risks": [{"risk_id": "RISK-POLICY-001", "description": "policy bypass", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": [requirement["id"]]}],
            "objects": [{"object_id": "OBJ-POLICY-001", "description": "host command"}], "types": ["FUNCTIONAL"],
            "test_points": [{"point_id": "TP-POLICY-001", "object_id": "OBJ-POLICY-001", "type": "FUNCTIONAL", "rationale": "policy enforcement", "risk_refs": ["RISK-POLICY-001"], "requirement_refs": [requirement["id"]], "coverage_rule": "valid and invalid lifecycle paths"}],
        })
        self.runtime.execute("test_case.create", {
            "project_id": self.project, "case_id": case_id, "test_model_id": "TM-POLICY-001",
            "test_point_refs": ["TP-POLICY-001"], "requirement_refs": [requirement["id"]],
            "test_type": "FUNCTIONAL", "module": "policy", "priority": "P0", "risk": "HIGH",
            "preconditions": [], "test_data": {},
            "steps": [{"order": 1, "action": "execute controlled test", "expected_observation": "observable result"}],
            "expected_result": "observable result", "automation": {"status": "MANUAL"}, "state": "BASELINED",
        })
        environment = self.evidence("test_environment", "tester", {"artifact_refs": [ref("REQ", requirement["id"])]})
        execution = self.runtime.execute("test_execution.start", {
            "case_id": case_id, "case_version": 1, "executor_id": "tester",
            "environment_ref": ref("EVIDENCE", environment["id"]),
        })
        proof = self.evidence("test_execution", "tester", {
            "execution_id": execution["id"], "result": "PASS", "artifact_refs": [ref("TEST_CASE", case_id)],
        })
        complete = self.runtime.execute("test_execution.finish", {
            "execution_id": execution["id"], "result": "PASS", "actual_result": "temporary passing fixture",
            "evidence_refs": [ref("EVIDENCE", proof["id"])],
        })
        return requirement, complete

    def execute_case(self, case_id: str, environment: dict, result: str, label: str):
        execution = self.runtime.execute("test_execution.start", {
            "case_id": case_id, "case_version": 1, "executor_id": "tester", "environment_ref": environment,
        })
        proof = self.evidence("test_execution", "tester", {
            "execution_id": execution["id"], "result": result, "artifact_refs": [ref("TEST_CASE", case_id)],
        })
        return self.runtime.execute("test_execution.finish", {
            "execution_id": execution["id"], "result": result, "actual_result": label,
            "evidence_refs": [ref("EVIDENCE", proof["id"])],
        })

    def quality_task(self, bug: str, requirement: str, task_artifact: str):
        return self.runtime.execute("task.create", {
            "project_id": self.project, "title": "temporary repair " + bug,
            "why": "quality chain for " + bug, "role": "developer", "requirements": [requirement],
            "dependencies": [], "inputs": {"fix_defect_id": bug, "lifecycle_task_ref": ref("TASK", task_artifact)},
        })

    def finish_quality_task(self, quality: dict):
        for phase, actor in (("implementation", "developer"), ("unit", "tester"), ("integration", "tester"), ("review", "reviewer")):
            run = self.runtime.execute("run.start", {"task_id": quality["id"], "agent_id": actor, "phase": phase})
            self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "temporary quality fixture", "evidence": {"temporary_fixture": True, "status": "PASS", "exit_code": 0}})

    def complete_through_g9_with_temporary_approval(self):
        """Build only the minimal isolated evidence required to test G9/G10 mechanics."""
        requirement, execution = self.model_case_and_pass_execution()
        design = self.artifact("DES-POLICY-001", "DES", state="BASELINED", actor="architect")
        task = self.artifact("TASK-POLICY-001", "TASK", state="BASELINED", actor="architect")
        code = self.artifact("CODE-POLICY-001", "CODE_CHANGE", state="BASELINED", actor="developer")
        for left, right, relation in (
            (ref("REQ", requirement["id"]), ref("DES", design["id"]), "realized_by"),
            (ref("DES", design["id"]), ref("TASK", task["id"]), "planned_by"),
            (ref("TASK", task["id"]), ref("CODE_CHANGE", code["id"]), "implemented_by"),
        ):
            self.runtime.execute("trace.link", {"project_id": self.project, "from": left, "to": right, "relation": relation})
        self.assertEqual("COMPLETE", self.runtime.lifecycle_snapshot(self.project)["traceability"][0]["status"])

        temporary_runtime = Runtime(self.root / "state.db", approval_provider=TemporarySyntheticApprovalVerifier())
        for number in range(10):
            gate = "G" + str(number)
            subject = self.artifact("DOC-" + gate + "-POLICY", state="BASELINED")
            subject_ref = [ref("DOC", subject["id"])]
            ordinary = [item for item in POLICY[gate] if item not in TEST_CRITERIA | REVIEW_CRITERIA | {"human_acceptance"}]
            if ordinary:
                self.evidence("document", self.orchestrator, {"gate_id": gate, "criteria": ordinary, "artifact_refs": subject_ref})
            tests = [item for item in POLICY[gate] if item in TEST_CRITERIA]
            if tests:
                self.evidence("test_execution", "tester", {"gate_id": gate, "criteria": tests, "execution_id": execution["id"], "result": "PASS", "artifact_refs": [ref("TEST_CASE", "TC-POLICY-001")]})
            reviews = [item for item in POLICY[gate] if item in REVIEW_CRITERIA]
            if reviews:
                self.evidence("review", "reviewer", {"gate_id": gate, "criteria": reviews, "subject_id": subject["id"], "result": "PASS", "artifact_refs": subject_ref})
            if gate == "G9":
                without_human = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": gate})
                self.assertIn("WAITING_HUMAN_APPROVAL", without_human["missing"])
                rejected = {
                    "project_id": self.project, "kind": "human_approval", "status": "VERIFIED",
                    "locator": {"inline_json": {"temporary_synthetic_fixture": True}},
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"gate_id": "G9", "criteria": ["human_acceptance"], "decision": "APPROVE", "statement": "Temporary synthetic verifier fixture only; not a human acceptance.", "artifact_refs": subject_ref},
                }
                with self.assertRaisesRegex(ValueError, "NOT_AVAILABLE"):
                    self.runtime.register_human_approval(rejected, operator="temporary-synthetic-operator")
                temporary_runtime.register_human_approval(rejected, operator="temporary-synthetic-operator")
            assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": gate})
            self.assertEqual("PASS", assessment["candidate"], (gate, assessment["missing"]))
            decision = self.evidence("gate_decision", "reviewer", {"assessment_id": assessment["id"], "status": "PASS", "artifact_refs": subject_ref})
            self.runtime.execute("gate.decide", {"assessment_id": assessment["id"], "status": "PASS", "decided_by": "reviewer", "decision_evidence_refs": [ref("EVIDENCE", decision["id"])]})

    def complete_adopted_stage_chain_to_g9(self):
        """Exercise the real staged candidate-adoption path, G0 through G9."""
        types = ["DOC", "DOC", "PRD", "REQ", "DES", "TASK", "CODE_CHANGE", "DOC", "DOC", "DOC"]
        roles = [self.orchestrator, "research", "product", "requirements", "architect", "architect", "developer", "tester", "reviewer", "docs"]
        candidates = [self.artifact(f"{'CODE' if kind == 'CODE_CHANGE' else kind}-CHAIN-{n}", kind, actor=roles[n]) for n, kind in enumerate(types)]
        temporary_runtime = Runtime(self.root / "state.db", approval_provider=TemporarySyntheticApprovalVerifier())
        execution = None
        for n in range(10):
            gate, work, candidate = f"G{n}", self.work[f"G{n}"], candidates[n]
            claim = self.claim(work, roles[n])
            self.finish(work, roles[n], claim, ref(types[n], candidate["id"]))
            adopted = self.runtime.execute("artifact.revise", {"artifact_id": candidate["id"], "expected_version": 1, "state": "BASELINED", "content_ref": candidate["content_ref"], "reason": "temporary identical candidate adoption", "material": False})
            candidates[n] = adopted
            if n == 3:
                # Build current-version trace and executable temporary test facts
                # after REQ adoption and before G3 is assessed.
                self.runtime.execute("trace.link", {"project_id": self.project, "from": ref("REQ", adopted["id"], 2), "to": ref("DES", candidates[4]["id"]), "relation": "realized_by"})
                self.runtime.execute("trace.link", {"project_id": self.project, "from": ref("DES", candidates[4]["id"]), "to": ref("TASK", candidates[5]["id"]), "relation": "planned_by"})
                self.runtime.execute("trace.link", {"project_id": self.project, "from": ref("TASK", candidates[5]["id"]), "to": ref("CODE_CHANGE", candidates[6]["id"]), "relation": "implemented_by"})
                self.runtime.execute("test_model.create", {"project_id": self.project, "artifact_id": "TM-CHAIN", "source": {"kind": "host", "actor": "tester"}, "requirement_refs": [adopted["id"]], "function_tree": {"name": "chain"}, "risks": [{"risk_id":"RISK-CHAIN","description":"temporary","likelihood":"HIGH","impact":"HIGH","priority":"P0","requirement_refs":[adopted["id"]]}], "objects":[{"object_id":"OBJ-CHAIN","description":"temporary"}], "types":["FUNCTIONAL"], "test_points":[{"point_id":"TP-CHAIN","object_id":"OBJ-CHAIN","type":"FUNCTIONAL","rationale":"temporary","risk_refs":["RISK-CHAIN"],"requirement_refs":[adopted["id"]],"coverage_rule":"all"}]})
                self.runtime.execute("test_case.create", {"project_id":self.project,"case_id":"TC-CHAIN","test_model_id":"TM-CHAIN","test_point_refs":["TP-CHAIN"],"requirement_refs":[adopted["id"]],"test_type":"FUNCTIONAL","module":"chain","priority":"P0","risk":"HIGH","preconditions":[],"test_data":{},"steps":[{"order":1,"action":"temporary","expected_observation":"pass"}],"expected_result":"pass","automation":{"status":"MANUAL"},"state":"BASELINED"})
                env=self.evidence("test_environment","tester",{"artifact_refs":[ref("REQ",adopted["id"],2)]}); execution=self.execute_case("TC-CHAIN",ref("EVIDENCE",env["id"]),"PASS","temporary chain pass")
            if n in {4,5,6}:
                # Re-link exact adopted versions before evaluating the Gate.
                if n == 4: self.runtime.execute("trace.link", {"project_id":self.project,"from":ref("REQ",candidates[3]["id"],2),"to":ref("DES",adopted["id"],2),"relation":"realized_by"})
                if n == 5: self.runtime.execute("trace.link", {"project_id":self.project,"from":ref("DES",candidates[4]["id"],2),"to":ref("TASK",adopted["id"],2),"relation":"planned_by"})
                if n == 6: self.runtime.execute("trace.link", {"project_id":self.project,"from":ref("TASK",candidates[5]["id"],2),"to":ref("CODE_CHANGE",adopted["id"],2),"relation":"implemented_by"})
            subject=[ref(types[n],adopted["id"],2)]
            ordinary=[x for x in POLICY[gate] if x not in TEST_CRITERIA|REVIEW_CRITERIA|{"human_acceptance"}]
            if ordinary: self.evidence("document", self.orchestrator, {"gate_id":gate,"criteria":ordinary,"artifact_refs":subject})
            tests=[x for x in POLICY[gate] if x in TEST_CRITERIA]
            if tests: self.evidence("test_execution","tester",{"gate_id":gate,"criteria":tests,"execution_id":execution["id"],"result":"PASS","artifact_refs":[ref("TEST_CASE","TC-CHAIN")]})
            reviews=[x for x in POLICY[gate] if x in REVIEW_CRITERIA]
            if reviews: self.evidence("review","reviewer",{"gate_id":gate,"criteria":reviews,"subject_id":adopted["id"],"result":"PASS","artifact_refs":subject})
            if n == 9:
                data={"project_id":self.project,"kind":"human_approval","status":"VERIFIED","locator":{"inline_json":{"temporary":True}},"observed_at":datetime.now(timezone.utc).isoformat(),"metadata":{"gate_id":"G9","criteria":["human_acceptance"],"decision":"APPROVE","statement":"Temporary fixture only, not human acceptance.","artifact_refs":subject}}
                temporary_runtime.register_human_approval(data,operator="temporary-synthetic-operator")
            assessment=self.runtime.execute("gate.assess",{"project_id":self.project,"gate_id":gate}); self.assertEqual("PASS",assessment["candidate"],(gate,assessment["missing"]))
            decision=self.evidence("gate_decision","reviewer",{"assessment_id":assessment["id"],"status":"PASS","artifact_refs":subject}); self.runtime.execute("gate.decide",{"assessment_id":assessment["id"],"status":"PASS","decided_by":"reviewer","decision_evidence_refs":[ref("EVIDENCE",decision["id"])]})
        return candidates

    def test_raw_runtime_cannot_bypass_gate_and_done_is_draft_candidate_only(self):
        g0 = self.work["G0"]
        candidate = self.artifact("DOC-G0-CANDIDATE")
        self.finish(g0, self.orchestrator, self.claim(g0, self.orchestrator), ref("DOC", candidate["id"]))
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_PREDECESSOR_GATE_NOT_PASS:G0"):
            self.claim(self.work["G1"], "research")
        self.pass_g0(candidate["id"])
        baseline = self.artifact("DOC-G1-BASELINE", state="BASELINED", actor="research")
        claim = self.claim(self.work["G1"], "research")
        self.assertEqual([ref("DOC", candidate["id"], 2)], claim["dependency_input_refs"])
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_WORK_OUTPUT_MUST_REMAIN_DRAFT"):
            self.finish(self.work["G1"], "research", claim, ref("DOC", baseline["id"]))
        self.assertIsNone(next(g for g in self.runtime.lifecycle_snapshot(self.project)["gates"] if g["gate_id"] == "G1")["gate_status"])

    def test_stale_gate_evidence_and_stale_requirement_block_claim_and_finish(self):
        candidate = self.artifact("DOC-G0-STALE-CANDIDATE")
        self.finish(self.work["G0"], self.orchestrator, self.claim(self.work["G0"], self.orchestrator), ref("DOC", candidate["id"]))
        g0_evidence_subject = self.runtime.execute("artifact.revise", {"artifact_id": candidate["id"], "expected_version": 1, "state": "BASELINED", "content_ref": candidate["content_ref"], "reason": "adopt temporary candidate", "material": False})
        g0_ref = [ref("DOC", g0_evidence_subject["id"], g0_evidence_subject["version"])]
        self.evidence("document", self.orchestrator, {"gate_id": "G0", "criteria": list(POLICY["G0"]), "artifact_refs": g0_ref})
        g0_assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": "G0"})
        g0_decision = self.evidence("gate_decision", "reviewer", {"assessment_id": g0_assessment["id"], "status": "PASS", "artifact_refs": g0_ref})
        self.runtime.execute("gate.decide", {"assessment_id": g0_assessment["id"], "status": "PASS", "decided_by": "reviewer", "decision_evidence_refs": [ref("EVIDENCE", g0_decision["id"]) ]})
        claim = self.claim(self.work["G1"], "research")
        change = self.artifact("CR-STALE-POLICY", "CR", state="BASELINED")
        self.runtime.execute("artifact.revise", {"artifact_id": candidate["id"], "expected_version": 2, "state": "APPROVED", "content_ref": {"inline_json": {"changed": True}}, "reason": "temporary drift", "material": True, "change_id": change["id"]})
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_PREDECESSOR_GATE_NOT_PASS:G0"):
            self.runtime.execute("work.heartbeat", {"work_order_id": self.work["G1"]["id"], "agent_id": "research", "lease_token": claim["lease_token"]})

        # Cancel the invalid lease. A separate G0 work has no predecessor, so
        # it isolates stale input-reference admission from the stale Gate.
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "pause", "reason": "invalidate stale temporary lease"})
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "resume", "reason": "continue temporary negative check"})
        requirement = self.artifact("REQ-STALE-POLICY", "REQ", state="BASELINED")
        extra = self.runtime.execute("work.create", {
            "project_id": self.project, "gate_id": "G0", "activity": "stale input check", "required_role": "researcher",
            "why": "must reject revision drift", "input_refs": [ref("REQ", requirement["id"])], "dependencies": [],
            "output_contract": {"required_types": ["DOC"], "min_outputs": 1},
        })
        extra_claim = self.claim(extra, "research")
        self.runtime.execute("artifact.revise", {
            "artifact_id": requirement["id"], "expected_version": 1, "state": "BASELINED",
            "content_ref": {"inline_json": {"changed": "requirement input"}}, "reason": "temporary requirement revision", "material": False,
        })
        output = self.artifact("DOC-STALE-OUTPUT", actor="research")
        with self.assertRaisesRegex(ValueError, "stale or invalid work lease"):
            self.finish(extra, "research", extra_claim, ref("DOC", output["id"]))
        with self.assertRaisesRegex(ValueError, "(work is not ready|unknown external outcome requires explicit safe_to_retry)"):
            self.claim(extra, "research")

    def test_g10_claim_requires_g9_approval_with_temporary_verifier_only(self):
        candidates = self.complete_adopted_stage_chain_to_g9()
        release_work = self.runtime.execute("work.create", {
            "project_id": self.project, "gate_id": "G10", "activity": "prepare release candidate", "required_role": "release_manager",
            "why": "verify post-acceptance host claim", "input_refs": [], "dependencies": [self.work["G9"]["id"]],
            "output_contract": {"required_types": ["DOC"], "min_outputs": 1},
        })
        claim = self.claim(release_work, "release")
        self.assertEqual([ref("DOC", candidates[9]["id"], 2)], claim["dependency_input_refs"])
        evidence = [item for item in self.runtime.lifecycle_snapshot(self.project)["evidence"] if item["kind"] == "human_approval"]
        self.assertEqual(1, len(evidence))
        self.assertEqual("temporary-synthetic-verifier", evidence[0]["metadata"]["provider_id"])
        self.assertEqual("human", evidence[0]["recorded_role"])

    def test_actual_local_failure_fix_retest_and_fresh_review_close_is_role_separated(self):
        requirement, _ = self.model_case_and_pass_execution(case_id="TC-ACTUAL-LOCAL-001")
        application = self.root / "bounded_app.txt"
        application.write_text("BROKEN", encoding="utf-8")
        command = [sys.executable, "-c", "from pathlib import Path; raise SystemExit(0 if Path('bounded_app.txt').read_text() == 'FIXED' else 7)"]
        failed_command = subprocess.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        self.assertEqual(7, failed_command.returncode)
        environment = self.evidence("test_environment", "tester", {"artifact_refs": [ref("REQ", requirement["id"])]})
        failed_execution = self.runtime.execute("test_execution.start", {"case_id": "TC-ACTUAL-LOCAL-001", "case_version": 1, "executor_id": "tester", "environment_ref": ref("EVIDENCE", environment["id"])})
        failed_proof = self.evidence("test_execution", "tester", {"execution_id": failed_execution["id"], "result": "FAIL", "artifact_refs": [ref("TEST_CASE", "TC-ACTUAL-LOCAL-001")], "command": command, "exit_code": failed_command.returncode})
        failure = self.runtime.execute("test_execution.finish", {"execution_id": failed_execution["id"], "result": "FAIL", "actual_result": "actual temporary command returned 7", "evidence_refs": [ref("EVIDENCE", failed_proof["id"]) ]})
        bug = failure["defect_id"]
        with self.assertRaisesRegex(ValueError, "owner role does not match defect category"):
            self.runtime.execute("defect.classify", {"defect_id": bug, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "tester", "rationale": "invalid role", "classified_by": "tester", "evidence_refs": [ref("EVIDENCE", failed_proof["id"]) ]})
        self.runtime.execute("defect.classify", {"defect_id": bug, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer", "rationale": "actual temporary file implementation failure", "classified_by": "tester", "evidence_refs": [ref("EVIDENCE", failed_proof["id"]) ]})
        repair_stages = [w["repair_stage"] for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == bug]
        self.assertEqual(["triage", "fix", "retest", "review"], repair_stages)
        # A repeated classification is an idempotency/recovery path, not a
        # license to enqueue duplicate repairs for the same observed failure.
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.runtime.execute("defect.classify", {"defect_id": bug, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer", "rationale": "materially different repeat classification", "classified_by": "tester", "evidence_refs": [ref("EVIDENCE", failed_proof["id"]) ]})
        self.assertEqual(4, len([w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == bug]))

        application.write_text("FIXED", encoding="utf-8")
        passed_command = subprocess.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        self.assertEqual(0, passed_command.returncode)
        quality = self.runtime.execute("task.create", {"project_id": self.project, "title": "actual bounded repair", "why": "fix " + bug, "role": "developer", "requirements": [requirement["id"]], "dependencies": [], "inputs": {"fix_defect_id": bug, "lifecycle_task_ref": ref("TASK", "TASK-ACTUAL-LOCAL-001")}})
        fix_task = self.artifact("TASK-ACTUAL-LOCAL-001", "TASK", state="BASELINED", actor="developer", content={"defect_id": bug, "requirement_refs": [requirement["id"]], "quality_task_id": quality["id"], "actual_file_sha256": hashlib.sha256(application.read_bytes()).hexdigest()})
        for phase, actor in (("implementation", "developer"), ("unit", "tester"), ("integration", "tester"), ("review", "reviewer")):
            run = self.runtime.execute("run.start", {"task_id": quality["id"], "agent_id": actor, "phase": phase})
            self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "actual temporary local application command observed", "evidence": {"command": command, "exit_code": passed_command.returncode, "sha256": hashlib.sha256(application.read_bytes()).hexdigest(), "temporary_fixture": True}})
        fix_proof = self.evidence("document", "developer", {"artifact_refs": [ref("TASK", fix_task["id"])]})
        self.runtime.execute("defect.fix", {"defect_id": bug, "fix_task_id": fix_task["id"], "completion_task_id": quality["id"], "fixed_by": "developer", "evidence_refs": [ref("EVIDENCE", fix_proof["id"]) ]})
        with self.assertRaisesRegex(ValueError, "fresh independent passing retest"):
            self.runtime.execute("defect.resolve", {"defect_id": bug, "resolved_by": "tester", "execution_refs": [ref("TEST_EXECUTION", failed_execution["id"])]})

        retest = self.runtime.execute("test_execution.start", {"case_id": "TC-ACTUAL-LOCAL-001", "case_version": 1, "executor_id": "tester", "environment_ref": ref("EVIDENCE", environment["id"])})
        retest_proof = self.evidence("test_execution", "tester", {"execution_id": retest["id"], "result": "PASS", "artifact_refs": [ref("TEST_CASE", "TC-ACTUAL-LOCAL-001")], "command": command, "exit_code": passed_command.returncode})
        retest = self.runtime.execute("test_execution.finish", {"execution_id": retest["id"], "result": "PASS", "actual_result": "actual temporary command returned 0", "evidence_refs": [ref("EVIDENCE", retest_proof["id"]) ]})
        stale_review = self.evidence("review", "reviewer", {"subject_id": bug, "result": "PASS", "artifact_refs": [ref("BUG", bug)]})
        self.runtime.execute("defect.resolve", {"defect_id": bug, "resolved_by": "tester", "execution_refs": [ref("TEST_EXECUTION", retest["id"]) ]})
        with self.assertRaisesRegex(ValueError, "fresh defect review evidence"):
            self.runtime.execute("defect.close", {"defect_id": bug, "closed_by": "reviewer", "evidence_refs": [ref("EVIDENCE", stale_review["id"]) ]})
        fresh_review = self.evidence("review", "reviewer", {"subject_id": bug, "result": "PASS", "artifact_refs": [ref("BUG", bug)]})
        closed = self.runtime.execute("defect.close", {"defect_id": bug, "closed_by": "reviewer", "evidence_refs": [ref("EVIDENCE", fresh_review["id"]) ]})
        self.assertEqual("CLOSED", closed["status"])

    def test_same_case_repair_budget_escalates_fourth_failure_but_not_distinct_case(self):
        requirement, _ = self.model_case_and_pass_execution()
        environment = self.evidence("test_environment", "tester", {"artifact_refs": [ref("REQ", requirement["id"])]})
        defects = []
        for index in range(4):
            failed = self.execute_case("TC-POLICY-001", ref("EVIDENCE", environment["id"]), "FAIL", "same case failure " + str(index + 1))
            defects.append(failed["defect_id"])
            works = [w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == failed["defect_id"]]
            if index < 3:
                self.assertEqual(["triage"], [w["repair_stage"] for w in works])
                self.runtime.execute("defect.classify", {"defect_id": failed["defect_id"], "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer", "rationale": "temporary bounded cycle", "classified_by": "tester", "evidence_refs": failed["evidence_refs"]})
                chain = [w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == failed["defect_id"]]
                self.assertEqual({"triage", "fix", "retest", "review"}, {w["repair_stage"] for w in chain})
            else:
                self.assertEqual([], works)
                fourth = next(row for row in self.runtime.lifecycle_snapshot(self.project)["defects"] if row["id"] == failed["defect_id"])
                self.assertEqual("PENDING_HUMAN", fourth["repair_disposition"])
        self.assertEqual(4, len(defects))
        self.runtime.execute("test_case.create", {
            "project_id": self.project, "case_id": "TC-POLICY-002", "test_model_id": "TM-POLICY-001", "test_point_refs": ["TP-POLICY-001"], "requirement_refs": [requirement["id"]], "test_type": "FUNCTIONAL", "module": "policy", "priority": "P0", "risk": "HIGH", "preconditions": [], "test_data": {}, "steps": [{"order": 1, "action": "execute distinct case", "expected_observation": "failure is triaged independently"}], "expected_result": "failure is triaged independently", "automation": {"status": "MANUAL"}, "state": "BASELINED",
        })
        distinct = self.execute_case("TC-POLICY-002", ref("EVIDENCE", environment["id"]), "FAIL", "distinct case failure")
        distinct_works = [w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == distinct["defect_id"]]
        self.assertEqual(["triage"], [w["repair_stage"] for w in distinct_works])

    def test_repair_work_cannot_finish_early_and_completes_after_matching_domain_transitions(self):
        # G0..G9 are minimal isolated fixtures so a G7 repair work can be
        # claimed legitimately through the same strict host gate path as a
        # real post-development failure.
        self.complete_through_g9_with_temporary_approval()
        requirement = "REQ-POLICY-001"
        environment = self.evidence("test_environment", "tester", {"artifact_refs": [ref("REQ", requirement)]})
        failed = self.execute_case("TC-POLICY-001", ref("EVIDENCE", environment["id"]), "FAIL", "repair work fixture failure")
        bug = failed["defect_id"]
        self.runtime.execute("defect.classify", {"defect_id": bug, "category": "PRODUCT", "severity": "MAJOR", "owner_role": "developer", "rationale": "temporary repair-work classification", "classified_by": "tester", "evidence_refs": failed["evidence_refs"]})
        stages = {w["repair_stage"]: w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == bug}
        with self.assertRaises(ValueError):
            self.claim(stages["fix"], "tester")
        fix_claim = self.claim(stages["fix"], "developer")
        pre_fix = self.evidence("document", "developer", {"artifact_refs": [ref("REQ", requirement)]})
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_REPAIR_FIX_REQUIRES_DEFECT_FIX"):
            self.finish(stages["fix"], "developer", fix_claim, ref("EVIDENCE", pre_fix["id"]))
        quality = self.quality_task(bug, requirement, "TASK-REPAIR-WORK")
        task_artifact = self.artifact("TASK-REPAIR-WORK", "TASK", state="BASELINED", actor="developer", content={"defect_id": bug, "requirement_refs": [requirement], "quality_task_id": quality["id"]})
        self.finish_quality_task(quality)
        fix_proof = self.evidence("document", "developer", {"artifact_refs": [ref("TASK", task_artifact["id"]) ]})
        self.runtime.execute("defect.fix", {"defect_id": bug, "fix_task_id": task_artifact["id"], "completion_task_id": quality["id"], "fixed_by": "developer", "evidence_refs": [ref("EVIDENCE", fix_proof["id"]) ]})
        unrelated_fix = self.evidence("document", "developer", {"artifact_refs": [ref("TASK", task_artifact["id"]) ]})
        with self.assertRaisesRegex(ValueError, "REPAIR.*OUTPUT"):
            self.finish(stages["fix"], "developer", fix_claim, ref("EVIDENCE", unrelated_fix["id"]))
        self.finish(stages["fix"], "developer", fix_claim, ref("EVIDENCE", fix_proof["id"]))
        retest_claim = self.claim(stages["retest"], "tester")
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_REPAIR_RETEST_REQUIRES_INDEPENDENT_RESOLUTION"):
            self.finish(stages["retest"], "tester", retest_claim, ref("TEST_EXECUTION", failed["id"]))
        retest = self.execute_case("TC-POLICY-001", ref("EVIDENCE", environment["id"]), "PASS", "temporary repair retest pass")
        self.runtime.execute("defect.resolve", {"defect_id": bug, "resolved_by": "tester", "execution_refs": [ref("TEST_EXECUTION", retest["id"]) ]})
        with self.assertRaisesRegex(ValueError, "REPAIR.*OUTPUT"):
            self.finish(stages["retest"], "tester", retest_claim, ref("TEST_EXECUTION", failed["id"]))
        self.finish(stages["retest"], "tester", retest_claim, ref("TEST_EXECUTION", retest["id"]))
        review_claim = self.claim(stages["review"], "reviewer")
        early_review = self.evidence("review", "reviewer", {"subject_id": bug, "result": "PASS", "artifact_refs": [ref("BUG", bug)]})
        with self.assertRaisesRegex(ValueError, "STRICT_POLICY_REPAIR_REVIEW_REQUIRES_DEFECT_CLOSURE"):
            self.finish(stages["review"], "reviewer", review_claim, ref("EVIDENCE", early_review["id"]))
        fresh_review = self.evidence("review", "reviewer", {"subject_id": bug, "result": "PASS", "artifact_refs": [ref("BUG", bug)]})
        self.runtime.execute("defect.close", {"defect_id": bug, "closed_by": "reviewer", "evidence_refs": [ref("EVIDENCE", fresh_review["id"]) ]})
        with self.assertRaisesRegex(ValueError, "REPAIR.*OUTPUT"):
            self.finish(stages["review"], "reviewer", review_claim, ref("EVIDENCE", early_review["id"]))
        self.finish(stages["review"], "reviewer", review_claim, ref("EVIDENCE", fresh_review["id"]))
        current = {w["repair_stage"]: w for w in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if w.get("repair_defect_id") == bug}
        self.assertEqual({"fix": "DONE", "retest": "DONE", "review": "DONE"}, {stage: current[stage]["status"] for stage in ("fix", "retest", "review")})

    def test_existing_non_bootstrap_projects_remain_compatible(self):
        plain = Runtime(self.root / "plain.db")
        project = plain.execute("project.create", {"name": "legacy fixture", "idea": "compatibility"})["id"]
        plain.execute("agent.register", {"id": "legacy-developer", "role": "developer"})
        plain.execute("lifecycle.initialize", {"project_id": project, "repository_root": str(self.root), "mode": "active"})
        work = plain.execute("work.create", {"project_id": project, "gate_id": "G2", "activity": "legacy direct work", "required_role": "developer", "why": "existing projects did not opt into strict policy", "input_refs": [], "dependencies": [], "output_contract": {"required_types": ["DOC"], "min_outputs": 1}})
        claim = plain.execute("work.claim", {"work_order_id": work["id"], "agent_id": "legacy-developer", "lease_seconds": 60})
        self.assertEqual("CLAIMED", claim["status"])
        self.assertNotIn("strict_policy", claim)


if __name__ == "__main__":
    unittest.main()
