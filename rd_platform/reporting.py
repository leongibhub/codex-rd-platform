"""Truthful test-execution and traceability reporting from a runtime snapshot."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_TEST_PHASES = ("unit", "integration")
_NON_PASS_STATUSES = {"FAIL", "SKIPPED", "BLOCKED", "NOT_EXECUTED"}
_EXECUTED_STATUSES = {"PASS", "FAIL"}


def _records(snapshot: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    value = snapshot.get(name, [])
    if not isinstance(value, list):
        raise ValueError(f"snapshot {name} must be a list")
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _current_attempt(task: Mapping[str, Any], runs: list[dict[str, Any]]) -> int:
    specified = task.get("attempt")
    if isinstance(specified, int):
        return specified
    attempts = [run.get("attempt") for run in runs if isinstance(run.get("attempt"), int)]
    return max(attempts, default=1)


def _run_statuses(task: Mapping[str, Any], all_runs: list[dict[str, Any]]) -> dict[str, str]:
    revision = task.get("revision", 1)
    task_runs = [
        run
        for run in all_runs
        if run.get("task_id") == task.get("id") and run.get("revision", 1) == revision
    ]
    attempt = _current_attempt(task, task_runs)
    task_runs = [run for run in task_runs if run.get("attempt", 1) == attempt]
    by_phase: dict[str, str] = {}
    for phase in _TEST_PHASES:
        phase_runs = [run for run in task_runs if run.get("phase") == phase]
        if not phase_runs:
            by_phase[phase] = "NOT_EXECUTED"
            continue
        # The latest snapshot record for a phase is authoritative for this attempt.
        latest = phase_runs[-1]
        status = latest.get("status")
        evidence = latest.get("evidence")
        by_phase[phase] = (
            status
            if isinstance(status, str) and (status != "PASS" or isinstance(evidence, Mapping) and bool(evidence))
            else "NOT_EXECUTED"
        )
    return by_phase


def _task_result(task: Mapping[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    phase_statuses = _run_statuses(task, runs)
    statuses = set(phase_statuses.values())
    task_state = task.get("status")
    if task_state == "SKIPPED":
        status = "SKIPPED"
    elif task_state in {"REJECTED", "PAUSED"}:
        status = "BLOCKED"
    elif task_state == "FAILED":
        status = "FAIL"
    elif "FAIL" in statuses:
        status = "FAIL"
    elif "BLOCKED" in statuses:
        status = "BLOCKED"
    elif "SKIPPED" in statuses:
        status = "SKIPPED"
    elif "NOT_EXECUTED" in statuses:
        status = "NOT_EXECUTED"
    elif statuses == {"PASS"}:
        status = "PASS"
    else:
        status = "NOT_EXECUTED"
    return {
        "task_id": task.get("id"),
        "project_id": task.get("project_id"),
        "revision": task.get("revision", 1),
        "attempt": _current_attempt(task, [run for run in runs if run.get("task_id") == task.get("id")]),
        "required_phases": list(_TEST_PHASES),
        "phase_statuses": phase_statuses,
        "status": status,
    }


def _phase_counts(results: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    statuses = [result["phase_statuses"][phase] for result in results]
    executed = sum(status in _EXECUTED_STATUSES for status in statuses)
    passed = sum(status == "PASS" for status in statuses)
    return {
        "total": len(statuses),
        "executed": executed,
        "passed": passed,
        "failed": sum(status == "FAIL" for status in statuses),
        "not_executed": sum(status == "NOT_EXECUTED" for status in statuses),
        "blocked": sum(status == "BLOCKED" for status in statuses),
        "skipped": sum(status == "SKIPPED" for status in statuses),
        "pass_rate": {
            "numerator": passed,
            "denominator": executed,
            "value": passed / executed if executed else None,
        },
    }


def report(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Create a report from recorded runtime facts without fabricating a PASS."""
    if not isinstance(snapshot, Mapping):
        raise ValueError("snapshot must be a mapping")
    tasks = _records(snapshot, "tasks")
    runs = _records(snapshot, "runs")
    defects = _records(snapshot, "defects")
    results = [_task_result(task, runs) for task in tasks]
    counts = {status.lower(): sum(item["status"] == status for item in results) for status in (*_NON_PASS_STATUSES, "PASS")}
    total = len(results)
    executed = counts["pass"] + counts["fail"]
    if counts["fail"]:
        execution_status = "FAIL"
    elif counts["blocked"]:
        execution_status = "BLOCKED"
    elif total == 0 or counts["not_executed"]:
        execution_status = "NOT_EXECUTED"
    elif counts["skipped"]:
        execution_status = "NOT_EXECUTED"
    elif counts["pass"] == total:
        execution_status = "PASS"
    else:
        execution_status = "NOT_EXECUTED"

    requirement_rows: list[dict[str, Any]] = []
    result_by_task = {item["task_id"]: item for item in results}
    for task in tasks:
        requirements = task.get("requirements", [])
        if not isinstance(requirements, list):
            continue
        for requirement_id in requirements:
            if not isinstance(requirement_id, str):
                continue
            test_result = result_by_task[task.get("id")]["status"]
            requirement_rows.append(
                {
                    "requirement_id": requirement_id,
                    "task_id": task.get("id"),
                    "test_status": test_result,
                    "traceability_status": "PARTIAL",
                    "missing_mappings": ["design", "code_change", "release"],
                }
            )
    trace_total = len(requirement_rows)
    trace_complete = 0
    trace_partial = trace_total
    trace_status = "PARTIAL"

    open_defects = [defect for defect in defects if defect.get("status") != "CLOSED"]
    reasons: list[str] = []
    if execution_status != "PASS":
        reasons.append(f"test execution status is {execution_status}")
    if trace_status != "COMPLETE":
        reasons.append("requirement traceability is incomplete")
    if open_defects:
        reasons.append(f"{len(open_defects)} unresolved defect(s)")
    incomplete_tasks = [
        task for task in tasks if isinstance(task.get("status"), str) and task["status"] != "DONE"
    ]
    if incomplete_tasks:
        reasons.append(f"{len(incomplete_tasks)} task(s) lack final review completion")
    if execution_status in {"FAIL", "BLOCKED"} or open_defects or incomplete_tasks:
        release_status = "DO_NOT_RELEASE"
    else:
        release_status = "NO_RELEASE_EVIDENCE"
        reasons.append("deployment and human acceptance evidence were not executed in this module-quality report")
    module_coverage = {
        "status": execution_status,
        "scope": "unit",
        "denominator": "task",
        "total": total,
        "executed": executed,
        "passed": counts["pass"],
        "failed": counts["fail"],
        "not_executed": counts["not_executed"],
        "blocked": counts["blocked"],
        "skipped": counts["skipped"],
        "pass_rate": {
            "numerator": counts["pass"],
            "denominator": executed,
            "value": counts["pass"] / executed if executed else None,
        },
        "checks": {phase: _phase_counts(results, phase) for phase in _TEST_PHASES},
        "results": results,
    }
    return {
        "report_scope": "MODULE_QUALITY",
        "module_quality": {"status": execution_status, "scope": "unit"},
        "module_test_coverage": module_coverage,
        "test_execution": module_coverage,
        "traceability": {
            "status": trace_status,
            "total": trace_total,
            "covered": trace_complete,
            "partial": trace_partial,
            "gap": 0,
            "rows": requirement_rows,
        },
        "defects": {
            "total": len(defects),
            "open": len(open_defects),
            "closed": len(defects) - len(open_defects),
            "items": defects,
        },
        "release_recommendation": {
            "status": release_status,
            "reasons": reasons,
        },
        "human_acceptance": "NOT_EXECUTED",
        "deployment": "NOT_EXECUTED",
    }


build_report = report
