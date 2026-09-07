"""Host-enforced policy for projects bootstrapped by ``orchestrate-start``.

This is deliberately a small policy layer over the versioned lifecycle store.
It does not decide a Gate and it does not manufacture evidence.  Its purpose is
to make the bootstrap workflow fail closed even when a caller invokes the raw
``work.*`` Runtime commands instead of a worker service.
"""
from __future__ import annotations

from .lifecycle_governance import POLICY
from .store import Store


STRICT_POLICY = "orchestration-v1"
# A deterministic host-side circuit breaker.  More failures remain immutable
# defects, but must be escalated to a human rather than spending unbounded
# worker/API cost on automatically-created repair work.
MAX_AUTOMATED_REPAIR_CYCLES = 3

# ``lc_test_case_versions.data`` is a structured record rather than an
# artifact/content-ref pair.  Keep this allow-list intentionally complete:
# a newly-added case field must be classified here before it can become part
# of an adopted stage handoff.  Dropping unknown fields would silently permit
# semantic drift when the test-case schema grows.
TEST_CASE_SEMANTIC_FIELDS = frozenset((
    "id", "case_id", "project_id", "test_model_id", "test_model_version",
    "test_point_refs", "requirement_refs", "test_type", "module", "priority",
    "risk", "preconditions", "test_data", "steps", "expected_result", "automation",
))
TEST_CASE_GOVERNANCE_FIELDS = frozenset((
    "version", "state", "status", "created_at", "reason", "change_id",
))
TEST_CASE_FIELDS = TEST_CASE_SEMANTIC_FIELDS | TEST_CASE_GOVERNANCE_FIELDS


def strict_project(service, connection, project_id: str) -> bool:
    """Whether a durable bootstrap work order opted this project into policy.

    Work records are append-only operational history.  Looking for the marker
    there means a later draft revision of the initial idea cannot silently turn
    the policy off, and subsequent manually-created work inherits the policy.
    """
    return any(
        work.get("strict_policy") == STRICT_POLICY
        for work in service.rows(connection, "work_orders", project_id)
    )


def apply_create_policy(service, connection, project_id: str, data: dict) -> str | None:
    """Return the persisted marker a new work order must carry, if any."""
    requested = data.get("strict_policy")
    if requested not in {None, STRICT_POLICY}:
        raise ValueError("unknown strict_policy")
    if requested == STRICT_POLICY or strict_project(service, connection, project_id):
        return STRICT_POLICY
    return None


def _fresh_pass(service, connection, project_id: str, gate_id: str) -> None:
    gate = service.get(connection, "gates", project_id + ":" + gate_id)
    if gate.get("gate_status") != "PASS" or not gate.get("current_assessment_id"):
        raise ValueError("STRICT_POLICY_PREDECESSOR_GATE_NOT_PASS:" + gate_id)
    assessment = service.get(connection, "gate_assessments", gate["current_assessment_id"])
    if assessment.get("status") != "CURRENT" or assessment.get("input_digest") != service.digest(
        service.policy_inputs(connection, project_id, gate_id)
    ):
        raise ValueError("STRICT_POLICY_PREDECESSOR_GATE_STALE:" + gate_id)
    # ``evaluate`` also catches a changed file-backed artifact and stale human
    # approval binding.  A recorded PASS by itself is never authority.
    if service.evaluate(connection, project_id, gate_id)[1]:
        raise ValueError("STRICT_POLICY_PREDECESSOR_GATE_STALE:" + gate_id)


def _artifact_version(service, connection, artifact_id: str, version: int) -> dict:
    row = connection.execute("SELECT data FROM lc_artifact_versions WHERE artifact_id=? AND version=?", (artifact_id, version)).fetchone()
    if not row:
        raise ValueError("STRICT_POLICY_STAGE_OUTPUT_VERSION_MISSING:" + artifact_id)
    return Store.loads(row["data"])


def _test_case_version(connection, case_id: str, version: int) -> dict:
    row = connection.execute(
        "SELECT data FROM lc_test_case_versions WHERE case_id=? AND version=?",
        (case_id, version),
    ).fetchone()
    if not row:
        raise ValueError("STRICT_POLICY_STAGE_OUTPUT_VERSION_MISSING:" + case_id)
    return Store.loads(row["data"])


def _test_case_semantics(case: dict) -> dict:
    """Return the complete declared semantic TEST_CASE schema or fail closed."""
    unknown = set(case) - TEST_CASE_FIELDS
    missing = TEST_CASE_SEMANTIC_FIELDS - set(case)
    if unknown or missing:
        raise ValueError("STRICT_POLICY_TEST_CASE_SCHEMA_UNSUPPORTED:" + case.get("id", "unknown"))
    return {field: case[field] for field in sorted(TEST_CASE_SEMANTIC_FIELDS)}


def _adopted_stage_outputs(service, connection, work: dict, predecessor: str) -> list[dict]:
    """Resolve predecessor DRAFT candidates to exact adopted current versions."""
    gate = service.get(connection, "gates", work["project_id"] + ":" + predecessor)
    assessment = service.get(connection, "gate_assessments", gate["current_assessment_id"])
    assessment_refs = {(ref["type"], ref["id"], ref["version"]) for ref in assessment["input_refs"]}
    candidates = []
    for dependency in work["dependencies"]:
        prior = service.get(connection, "work_orders", dependency)
        if prior["gate_id"] != predecessor:
            continue
        for output in prior.get("output_refs", []):
            if output["type"] in {"EVIDENCE", "TEST_EXECUTION", "BUG", "REL"}:
                continue
            candidates.append(output)
    if not candidates:
        raise ValueError("STRICT_POLICY_STAGE_OUTPUT_MISSING:" + predecessor)
    resolved = []
    for candidate in candidates:
        if candidate["type"] == "TEST_MODEL":
            current = service.get(connection, "test_models", candidate["id"])
            companion = service.get(connection, "artifacts", candidate["id"])
            historical = _artifact_version(service, connection, candidate["id"], candidate["version"])
            if companion["artifact_type"] != "TEST_MODEL" or companion["version"] != current["version"]:
                raise ValueError("STRICT_POLICY_STAGE_OUTPUT_MODEL_PROVENANCE:" + candidate["id"])
            current_content = companion["content_ref"]
        elif candidate["type"] == "TEST_CASE":
            current = service.get(connection, "test_cases", candidate["id"])
            historical = _test_case_version(connection, candidate["id"], candidate["version"])
            # Case versions have no companion artifact/content hash.  Compare
            # every declared semantic field instead, allowing only lifecycle
            # governance fields (state/version/reason/timestamps) to change.
            if Store.dumps(_test_case_semantics(current)) != Store.dumps(_test_case_semantics(historical)):
                raise ValueError("STRICT_POLICY_STAGE_OUTPUT_ADOPTION_DRIFT:" + candidate["id"])
            current_content = None
        else:
            current = service.get(connection, "artifacts", candidate["id"])
            historical = _artifact_version(service, connection, candidate["id"], candidate["version"])
            current_content = current["content_ref"]
        if current.get("state") not in {"BASELINED", "APPROVED"}:
            raise ValueError("STRICT_POLICY_STAGE_OUTPUT_NOT_ADOPTED:" + candidate["id"])
        if current_content is not None and historical is not None and current_content["sha256"] != historical["content_ref"]["sha256"]:
            raise ValueError("STRICT_POLICY_STAGE_OUTPUT_ADOPTION_DRIFT:" + candidate["id"])
        adopted = {"type": candidate["type"], "id": candidate["id"], "version": current["version"]}
        if (adopted["type"], adopted["id"], adopted["version"]) not in assessment_refs:
            raise ValueError("STRICT_POLICY_GATE_EVIDENCE_MISSING_STAGE_OUTPUT:" + candidate["id"])
        resolved.append(adopted)
    if not resolved:
        raise ValueError("STRICT_POLICY_STAGE_OUTPUT_MISSING:" + predecessor)
    return resolved


def recovery_dependencies(service, connection, project_id: str, gate_id: str) -> list[str]:
    """Bind host-created recovery work to a real adopted predecessor handoff.

    Internal Gate-fail and rollback work is still ordinary strict work; it does
    not get a public bypass flag.  G0 has no predecessor.  For every later
    Gate, select a completed predecessor work only when its candidate resolves
    to the version already adopted by the current predecessor assessment.
    """
    ordinal = int(gate_id[1:])
    if not strict_project(service, connection, project_id) or ordinal == 0:
        return []
    predecessor = "G" + str(ordinal - 1)
    _fresh_pass(service, connection, project_id, predecessor)
    for prior in service.rows(connection, "work_orders", project_id):
        if prior.get("gate_id") != predecessor or prior.get("status") != "DONE":
            continue
        try:
            _adopted_stage_outputs(service, connection, {
                "project_id": project_id, "dependencies": [prior["id"]],
            }, predecessor)
        except ValueError:
            continue
        return [prior["id"]]
    raise ValueError("STRICT_POLICY_RECOVERY_PREDECESSOR_HANDOFF_MISSING:" + predecessor)


def validate_claim(service, connection, work: dict) -> list[dict]:
    """Require a fresh predecessor Gate for strict bootstrapped work.

    G0 is intentionally claimable: it produces candidate discovery material.
    Later work may still be *prepared* as DRAFT, but cannot be claimed until
    the preceding lifecycle Gate has independently assessed and decided PASS.
    G9 approval is therefore required to claim G10, not to prepare the G9
    acceptance package (which would be circular).
    """
    if work.get("strict_policy") != STRICT_POLICY:
        return
    if work.get("repair_stage"):
        # A repair chain is admitted by an already-recorded failed execution,
        # not by a hypothetical later G7 PASS.  Requiring that PASS here would
        # make the very loop needed to repair the failed test impossible.
        defect = service.get(connection, "defects", work.get("repair_defect_id"))
        source = service.get(connection, "test_executions", defect.get("source_execution"))
        if defect["project_id"] != work["project_id"] or source.get("result") != "FAIL":
            raise ValueError("STRICT_POLICY_REPAIR_SOURCE_FAILURE_REQUIRED")
        service.validate_repair_work(connection, work["project_id"], work, existing_work_id=work["id"])
        return []
    ordinal = int(work["gate_id"][1:])
    if ordinal == 0:
        return []
    predecessor = "G" + str(ordinal - 1)
    _fresh_pass(service, connection, work["project_id"], predecessor)
    resolved = _adopted_stage_outputs(service, connection, work, predecessor)
    # G7's own work creates test cases/executions, so requiring a complete RTM
    # before it starts would deadlock.  From G8 onward the prior G7 decision
    # already requires complete current traceability; make that explicit here.
    if ordinal >= 8:
        trace = service.trace_summary(connection, work["project_id"])
        if not trace or any(row["status"] != "COMPLETE" for row in trace):
            raise ValueError("STRICT_POLICY_RTM_NOT_COMPLETE")
    return resolved


def validate_finish(service, connection, work: dict, status: str, output_refs: list[dict]) -> None:
    """Keep agent/model work outputs as candidates, never lifecycle authority."""
    if work.get("strict_policy") != STRICT_POLICY or status != "DONE":
        return
    project_id = work["project_id"]
    for ref in output_refs:
        if ref["type"] in {"EVIDENCE", "TEST_EXECUTION", "BUG", "REL"}:
            continue
        if ref["type"] == "TEST_CASE":
            row = service.get(connection, "test_cases", ref["id"])
            state = row.get("state")
        elif ref["type"] == "TEST_MODEL":
            row = service.get(connection, "test_models", ref["id"])
            state = row.get("state")
        else:
            row = service.get(connection, "artifacts", ref["id"])
            state = row.get("state")
        if state != "DRAFT":
            raise ValueError("STRICT_POLICY_WORK_OUTPUT_MUST_REMAIN_DRAFT:" + ref["id"])
    repair_stage = work.get("repair_stage")
    if repair_stage:
        _validate_repair_finish(service, connection, work, repair_stage, output_refs)
    # Deliberately do not alter Gate state here.  A DONE work order is a
    # candidate handoff; only gate.assess + independent gate.decide can pass.


def _exact_output_refs(expected: list[dict], actual: list[dict], stage: str) -> None:
    """A repair handoff records the exact domain proof, not just its type."""
    normalize = lambda refs: sorted(Store.dumps(ref) for ref in refs)
    if not expected or normalize(expected) != normalize(actual):
        raise ValueError("STRICT_POLICY_REPAIR_" + stage.upper() + "_OUTPUT_BINDING_REQUIRED")


def _validate_repair_finish(service, connection, work: dict, stage: str, output_refs: list[dict]) -> None:
    """A repair handoff cannot be completed with an unrelated output ref."""
    defect = service.get(connection, "defects", work["repair_defect_id"])
    if defect["project_id"] != work["project_id"]:
        raise ValueError("STRICT_POLICY_REPAIR_DEFECT_PROJECT_MISMATCH")
    if stage == "triage":
        if defect.get("category") == "UNCLASSIFIED" or defect.get("classified_by") != work.get("agent_id"):
            raise ValueError("STRICT_POLICY_REPAIR_TRIAGE_REQUIRES_CLASSIFICATION")
        return
    if stage == "fix":
        if defect.get("status") not in {"FIXED", "RESOLVED", "CLOSED"} or defect.get("fixed_by") != work.get("agent_id"):
            raise ValueError("STRICT_POLICY_REPAIR_FIX_REQUIRES_DEFECT_FIX")
        _exact_output_refs(defect.get("fix_evidence_refs", []), output_refs, stage)
        return
    if stage == "retest":
        if defect.get("status") not in {"RESOLVED", "CLOSED"} or defect.get("resolved_by") != work.get("agent_id"):
            raise ValueError("STRICT_POLICY_REPAIR_RETEST_REQUIRES_INDEPENDENT_RESOLUTION")
        _exact_output_refs(defect.get("retest_execution_refs", []), output_refs, stage)
        return
    if stage == "review":
        if defect.get("status") != "CLOSED" or defect.get("closed_by") != work.get("agent_id"):
            raise ValueError("STRICT_POLICY_REPAIR_REVIEW_REQUIRES_DEFECT_CLOSURE")
        _exact_output_refs(defect.get("closure_evidence_refs", []), output_refs, stage)
        return
    raise ValueError("STRICT_POLICY_UNKNOWN_REPAIR_STAGE")


def create_repair_chain(service, connection, defect: dict) -> dict | None:
    """Create one bounded, role-separated remediation chain after G7 failure.

    A failed execution initially opens an UNCLASSIFIED defect.  Classification
    is evidence-led and chooses the owner role, so this function creates only
    independent triage at that point.  Once classification happens, it creates
    exactly one owner-fix -> tester-retest -> reviewer-review chain.  Repeated
    calls return the original chain; repeated test failures create their own
    defect history instead of an unbounded retry loop.
    """
    project_id = defect["project_id"]
    existing = [
        work for work in service.rows(connection, "work_orders", project_id)
        if work.get("repair_defect_id") == defect["id"] and work.get("repair_stage") != "triage"
    ]
    if existing:
        return {"created": False, "work_order_ids": [work["id"] for work in existing]}
    source = service.get(connection, "test_executions", defect["source_execution"])
    prior_cycles = _prior_repair_cycles(service, connection, defect, source)
    if prior_cycles >= MAX_AUTOMATED_REPAIR_CYCLES:
        if defect.get("repair_disposition") != "PENDING_HUMAN":
            defect.update(repair_disposition="PENDING_HUMAN", repair_budget_limit=MAX_AUTOMATED_REPAIR_CYCLES,
                          repair_budget_case_id=source["case_id"], repair_budget_case_version=source["case_version"])
            service.put(connection, "defects", defect)
            service.event(connection, project_id, "defect.repair_escalated", defect["id"], {
                "reason": "AUTOMATED_REPAIR_BUDGET_EXHAUSTED", "limit": MAX_AUTOMATED_REPAIR_CYCLES,
                "case_id": source["case_id"], "case_version": source["case_version"],
            })
        return {"created": False, "work_order_ids": [], "escalated": True,
                "reason": "AUTOMATED_REPAIR_BUDGET_EXHAUSTED"}
    if defect.get("category") == "UNCLASSIFIED":
        triage = service.work_create_repair(connection, {
            "project_id": project_id, "gate_id": "G7",
            "activity": "triage failed execution " + defect["id"],
            "required_role": "tester",
            "why": "Classify the observed failure with evidence before assigning repair ownership.",
            "input_refs": [{"type": "BUG", "id": defect["id"]}],
            "dependencies": [],
            "output_contract": {"required_types": ["EVIDENCE"], "min_outputs": 1},
            "repair_defect_id": defect["id"], "repair_stage": "triage", "source_execution": defect["source_execution"],
        })
        service.event(connection, project_id, "defect.repair_triage_created", defect["id"], {"work_order_id": triage["id"]})
        return {"created": True, "work_order_ids": [triage["id"]]}
    owner = defect.get("owner_role")
    if owner not in {"developer", "tester", "architect", "requirement_analyst"}:
        raise ValueError("classified defect owner is required for remediation")
    common = {"fix_defect_id": defect["id"], "source_execution": defect["source_execution"]}
    fix = service.work_create_repair(connection, {
        "project_id": project_id, "gate_id": "G7", "activity": "repair defect " + defect["id"],
        "required_role": owner, "why": "Evidence-classified defect repair; preserve original failed execution.",
        "input_refs": [{"type": "BUG", "id": defect["id"]}], "dependencies": [],
        "output_contract": {"required_types": ["EVIDENCE"], "min_outputs": 1},
        "repair_defect_id": defect["id"], "repair_stage": "fix", **common,
    })
    retest = service.work_create_repair(connection, {
        "project_id": project_id, "gate_id": "G7", "activity": "independent retest defect " + defect["id"],
        "required_role": "tester", "why": "Execute the bounded regression set after the assigned repair.",
        "input_refs": [{"type": "BUG", "id": defect["id"]}], "dependencies": [fix["id"]],
        "output_contract": {"required_types": ["TEST_EXECUTION"], "min_outputs": 1},
        "repair_defect_id": defect["id"], "repair_stage": "retest", **common,
    })
    review = service.work_create_repair(connection, {
        # This review is part of repairing G7 evidence.  Assigning it to G8
        # would require a G7 PASS first and make the repair loop circular.
        "project_id": project_id, "gate_id": "G7", "activity": "independent defect review " + defect["id"],
        "required_role": "reviewer", "why": "Review repair and retest evidence before closure.",
        "input_refs": [{"type": "BUG", "id": defect["id"]}], "dependencies": [retest["id"]],
        "output_contract": {"required_types": ["EVIDENCE"], "min_outputs": 1},
        "repair_defect_id": defect["id"], "repair_stage": "review", **common,
    })
    service.event(connection, project_id, "defect.repair_chain_created", defect["id"], {"work_order_ids": [fix["id"], retest["id"], review["id"]]})
    return {"created": True, "work_order_ids": [fix["id"], retest["id"], review["id"]]}


def _prior_repair_cycles(service, connection, defect: dict, source: dict) -> int:
    """Count distinct earlier defect cycles for the exact current case scope."""
    requirement_ids = {ref["id"] for ref in defect["requirement_refs"]}
    repaired = set()
    for prior in service.rows(connection, "defects", defect["project_id"]):
        if prior["id"] == defect["id"] or {ref["id"] for ref in prior["requirement_refs"]} != requirement_ids:
            continue
        prior_source = service.get(connection, "test_executions", prior["source_execution"])
        if prior_source["case_id"] != source["case_id"] or prior_source["case_version"] != source["case_version"]:
            continue
        if any(work.get("repair_defect_id") == prior["id"] for work in service.rows(connection, "work_orders", defect["project_id"])):
            repaired.add(prior["id"])
    return len(repaired)


def after_defect_classified(service, connection, defect: dict) -> dict | None:
    """Replace the sole triage placeholder with the bounded owner chain."""
    triage = [
        work for work in service.rows(connection, "work_orders", defect["project_id"])
        if work.get("repair_defect_id") == defect["id"] and work.get("repair_stage") == "triage"
    ]
    # Keep triage history visible.  It cannot be a dependency because
    # classification may be recorded by a distinct independent reviewer.
    for work in triage:
        if work["status"] in {"READY", "CLAIMED", "REVIEW_REQUIRED"}:
            # Classification can come from a reviewer or another verified
            # channel.  Do not leave a now-redundant triage work executable.
            work.update(status="REVIEW_REQUIRED", lease_digest=None, lease_until=None,
                        agent_id=None, version=work["version"] + 1)
            service.put(connection, "work_orders", work)
            # Use the established invalidation event consumed by the worker
            # service.  It only cancels the service's own process tree; an
            # external host remains responsible for observing this state.
            service.event(connection, defect["project_id"], "work.invalidated", work["id"], {
                "reason": "defect classification superseded triage", "external_process_cancelled": False,
            })
            service.event(connection, defect["project_id"], "defect.repair_triage_invalidated", defect["id"], {"work_order_id": work["id"]})
    if triage:
        service.event(connection, defect["project_id"], "defect.repair_classification_recorded", defect["id"], {"work_order_ids": [w["id"] for w in triage]})
    return create_repair_chain(service, connection, defect)
