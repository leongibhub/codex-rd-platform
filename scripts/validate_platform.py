"""CLI orchestration for platform template and runtime checks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib
from pathlib import Path
import subprocess
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.platform_validation import (
    ValidationIssue,
    evaluated_gate_ids,
    load_manifest,
    validate_gate_contract,
    validate_manifest_contract,
    validate_rtm_contract,
    validate_runtime_prerequisites,
)


@dataclass
class ValidationReport:
    lifecycle_mode: str
    issues: list[ValidationIssue]
    warnings: list[str]
    runtime_executed: bool
    evaluated_gates: list[str]

    @property
    def ok(self) -> bool:
        return not self.issues


def validate_platform(root: Path, static_only: bool = False, strict: bool = False) -> ValidationReport:
    """Run platform contracts; only full mode starts the MCP stdio server."""
    root = Path(root)
    issues: list[ValidationIssue] = []
    warnings: list[str] = []
    lifecycle_mode = "unknown"
    evaluated_gates: list[str] = []
    try:
        manifest = load_manifest(root)
        lifecycle_mode = manifest.get("lifecycle_mode", "unknown")
        issues.extend(validate_manifest_contract(root))
        issues.extend(validate_gate_contract(root, manifest))
        issues.extend(validate_rtm_contract(root, manifest))
        evaluated_gates = evaluated_gate_ids(root, manifest)
    except Exception:
        issues.append(ValidationIssue("CONFIG_INVALID", "platform validation configuration is invalid"))

    git_issues, git_warnings = _validate_git(root, strict)
    issues.extend(git_issues)
    warnings.extend(git_warnings)

    prerequisite_issues = validate_runtime_prerequisites(root)
    issues.extend(prerequisite_issues)
    runtime_executed = False
    if not static_only and not prerequisite_issues:
        try:
            health_module = importlib.import_module("scripts.mcp_health_check")
        except Exception:
            issues.append(ValidationIssue("MCP_HEALTH_IMPORT_FAILED", "MCP health check could not be imported"))
        else:
            runtime_executed = True
            try:
                issues.extend(health_module.check_company_context(root))
            except Exception:
                issues.append(ValidationIssue("MCP_HEALTH_CHECK_FAILED", "MCP health check failed"))
    return ValidationReport(lifecycle_mode, issues, warnings, runtime_executed, evaluated_gates)


def _validate_git(root: Path, strict: bool) -> tuple[list[ValidationIssue], list[str]]:
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return [ValidationIssue("GIT_INVALID", "Git repository HEAD is unavailable")], []
    if head.returncode != 0:
        return [ValidationIssue("GIT_INVALID", "Git repository HEAD is unavailable")], []
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    if status.returncode != 0:
        return [ValidationIssue("GIT_INVALID", "Git repository status is unavailable")], []
    if status.stdout.strip():
        if strict:
            return [ValidationIssue("GIT_DIRTY", "Git working tree is dirty")], []
        return [], ["Git working tree is dirty"]
    return [], []


def _print_report(report: ValidationReport, static_only: bool) -> None:
    if report.ok and not static_only:
        suffix = " (TEMPLATE MODE)" if report.lifecycle_mode == "template" else ""
        print(f"PLATFORM VALIDATION: PASS{suffix}")
    elif report.ok:
        suffix = " (TEMPLATE MODE)" if report.lifecycle_mode == "template" else ""
        print(f"STATIC VALIDATION: PASS{suffix}")
    else:
        print("PLATFORM VALIDATION: FAIL")
    print("Lifecycle Mode:", report.lifecycle_mode.upper())
    print("Evaluated Gates:", ", ".join(report.evaluated_gates) if report.evaluated_gates else "NONE")
    print("RUNTIME CHECK:", "EXECUTED" if report.runtime_executed else "NOT EXECUTED")
    for issue in report.issues:
        print(f" - [{issue.code}] {issue.message}")
    for warning in report.warnings:
        print(f" - WARNING: {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate platform contracts and MCP runtime health.")
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = validate_platform(Path(__file__).resolve().parents[1], args.static_only, args.strict)
        _print_report(report, args.static_only)
        return 0 if report.ok else 1
    except Exception:
        print("PLATFORM VALIDATION: FAIL")
        print(" - [VALIDATION_INTERNAL_ERROR] platform validation encountered an internal error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
