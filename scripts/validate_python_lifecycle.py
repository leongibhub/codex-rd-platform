"""TASK-V3-008: real, resumable Python-app lifecycle evidence through public APIs.

Prepare records the actual developer; execute requires a distinct actual tester.
Finalize consumes existing independent review evidence and never signs a Gate.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from decimal import Decimal, DecimalException
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rd_platform.runtime import Runtime
from rd_platform.lifecycle_governance import POLICY, REVIEW_CRITERIA, TEST_CRITERIA
from rd_platform.lifecycle_reporting import lifecycle_report, lifecycle_report_from_runtime

APP_DIR = Path("examples/multistack/python_expenses")
DOC_DIR = Path("docs/platform-v3/python-lifecycle")
REQS = {
    "REQ-MATRIX-PY-01": "Valid UTF-8/BOM/reordered CSV accepted; malformed columns/rows rejected",
    "REQ-MATRIX-PY-02": "Sorted category totals and exact Decimal strings in success JSON",
    "REQ-MATRIX-PY-03": "Empty, malformed date/category/amount, negative and non-finite data rejected",
    "REQ-MATRIX-PY-04": "Data/path errors exit 1 without success stdout; argument errors exit 2",
    "NFR-MATRIX-PY-001": "Exact decimal value and JSON string representation inside supported limits",
    "NFR-MATRIX-PY-002": "1000 significant digits, exponent -1000..1000 and 100000 rows are exact limits",
    "NFR-MATRIX-PY-003": "Observed CLI input and application source remain unchanged; isolated build outputs",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(ident: str, kind: str | None = None, version: int = 1) -> dict:
    kind = kind or ("NFR" if ident.startswith("NFR-") else "REQ")
    return {"type": kind, "id": ident, "version": version}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def write_once(path: Path, text: str) -> None:
    data = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"immutable document already exists with different content: {path}")
    if not path.exists():
        path.write_bytes(data)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED_SECRET]" if k in {"lease_token", "lease_digest"} else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def case_catalog() -> list[dict]:
    """Separate observable partitions; data recipes are fixed before execution."""
    r1, r2, r3, r4, n1, n2, n3 = REQS
    cases: list[dict] = []

    def add(name, requirements, *, csv=None, expected=None, exit_code=0, test_type="FUNCTIONAL", **data):
        cases.append({"id": "TC-PLC-" + name, "requirements": requirements, "type": test_type,
            "data": dict(data, **({"csv": csv} if csv is not None else {})),
            "expected": expected, "exit_code": exit_code})

    header = "date,category,amount\n"
    add("UTF8", [r1], csv="\ufeffcategory,amount,date\n餐饮,0.10,2026-09-06\n餐饮,0.20,2026-09-06\n",
        expected={"categories": {"餐饮": "0.30"}, "total": "0.30"}, test_type="COMPATIBILITY")
    add("TOTAL", [r2, n1], csv=header + "2026-09-06,z,2.00\n2026-09-06,a,0.10\n2026-09-06,a,0.20\n",
        expected={"categories": {"a": "0.30", "z": "2.00"}, "total": "2.30"})
    add("LONG", [r2, n1], csv=header + "2026-09-06,a,9999999999999999999999999999\n2026-09-06,a,2\n",
        expected={"categories": {"a": "10000000000000000000000000001"}, "total": "10000000000000000000000000001"}, test_type="BOUNDARY")
    add("ZERO", [r2, r3], csv=header + "2026-09-06,a,0\n", expected={"categories": {"a": "0"}, "total": "0"}, test_type="BOUNDARY")
    for name, content in {
        "HEADER-MISSING": "date,amount\n2026-09-06,1\n",
        "HEADER-EXTRA": "date,category,amount,extra\n2026-09-06,a,1,x\n",
        "HEADER-DUPLICATE": "date,date,amount\n2026-09-06,a,1\n",
        "ROW-MISSING": header + "2026-09-06,a\n",
        "ROW-EXTRA": header + "2026-09-06,a,1,x\n",
    }.items():
        add(name, [r1, r4], csv=content, exit_code=1, test_type="NEGATIVE")
    add("ENCODING", [r1, r4], input_base64=base64.b64encode(header.encode() + b"2026-09-06,\xff,1\n").decode(), exit_code=1, test_type="NEGATIVE")
    invalid = {"EMPTY": "", "HEADER-ONLY": header, "DATE-EMPTY": header + ",a,1\n",
        "DATE-FORMAT": header + "2026-9-6,a,1\n", "DATE-CALENDAR": header + "2026-02-30,a,1\n",
        "CATEGORY": header + "2026-09-06, ,1\n"}
    for label, amount in [("AMOUNT-EMPTY", ""), ("AMOUNT-TEXT", "abc"), ("NEGATIVE", "-1"),
                          ("NAN", "NaN"), ("SNAN", "sNaN"), ("INFINITY", "Infinity"), ("NEG-INFINITY", "-Infinity")]:
        invalid[label] = header + f"2026-09-06,a,{amount}\n"
    for name, content in invalid.items():
        add(name, [r3, r4], csv=content, exit_code=1, test_type="NEGATIVE")
    add("MISSING-FILE", [r4], missing_file=True, exit_code=1, test_type="NEGATIVE")
    add("NO-ARG", [r4], no_args=True, exit_code=2, test_type="NEGATIVE")
    add("EXTRA-ARG", [r4], extra_arg=True, exit_code=2, test_type="NEGATIVE")
    add("DIGITS-1000", [n2], csv=header + "2026-09-06,a," + "9" * 1000 + "\n", decimal_expected="9" * 1000, test_type="BOUNDARY")
    add("DIGITS-1001", [n2], csv=header + "2026-09-06,a," + "9" * 1001 + "\n", exit_code=1, test_type="BOUNDARY")
    for name, value, accepted in [("EXP-PLUS-1000", "1E+1000", True), ("EXP-MINUS-1000", "1E-1000", True),
                                   ("EXP-PLUS-1001", "1E+1001", False), ("EXP-MINUS-1001", "1E-1001", False)]:
        add(name, [n2], csv=header + f"2026-09-06,a,{value}\n", decimal_expected=value if accepted else None,
            exit_code=0 if accepted else 1, test_type="BOUNDARY")
    add("ROWS-100000", [n2], rows=100000, decimal_expected="100000", test_type="BOUNDARY")
    add("ROWS-100001", [n2], rows=100001, exit_code=1, test_type="BOUNDARY")
    add("INPUT-UNCHANGED-OK", [n3], csv=header + "2026-09-06,a,1\n", expected={"categories": {"a": "1"}, "total": "1"}, test_type="DATA_CONSISTENCY")
    add("INPUT-UNCHANGED-ERROR", [n3], csv=header + "2026-09-06,a,-1\n", exit_code=1, test_type="DATA_CONSISTENCY")
    add("UNIT-SUITE", [r1, r2, r3, r4, n1, n2], unit_suite=True)
    return cases


class PythonLifecycle:
    def __init__(self, output_dir: Path, *, root: Path = ROOT):
        self.root = root.resolve()
        self.output = output_dir.resolve()
        if not self.output.is_relative_to(self.root) or self.output == self.root or self.output.is_relative_to(self.root / APP_DIR):
            raise ValueError("output directory must be an isolated descendant of repository, outside the application")
        self.output.mkdir(parents=True, exist_ok=True)
        self.runtime = Runtime(self.output / "state.db")
        self.index_path = self.output / "run.json"
        self.index = json.loads(self.index_path.read_text(encoding="utf-8")) if self.index_path.exists() else {}

    def api(self, command, data, label):
        entry = {"command": command, "data": redact(data), "started_at": now()}
        try:
            result = self.runtime.execute(command, data, request_id=self.index["run_id"] + ":" + label)
            entry.update(outcome="RETURNED", result=redact(result))
            return result
        except Exception as error:
            entry.update(outcome="REJECTED", error=f"{type(error).__name__}: {error}")
            raise
        finally:
            entry["finished_at"] = now()
            with (self.output / "api-journal.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")

    def save(self):
        write_json(self.index_path, self.index)

    def source(self, actor):
        return {"kind": "host", "actor": actor}

    def content(self, path):
        return {"path": path.resolve().relative_to(self.root).as_posix(), "sha256": sha(path)}

    def file_hashes(self):
        return {p.relative_to(self.root).as_posix(): sha(p) for p in (self.root / APP_DIR).rglob("*") if p.is_file()}

    def process(self, argv, *, timeout=60):
        started = now()
        try:
            result = subprocess.run(argv, cwd=self.root, env=dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1"),
                shell=False, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
            return {"argv": argv, "cwd": str(self.root), "started_at": started, "finished_at": now(),
                "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "timed_out": False}
        except subprocess.TimeoutExpired as error:
            return {"argv": argv, "cwd": str(self.root), "started_at": started, "finished_at": now(), "exit_code": None,
                "stdout": (error.stdout or b"").decode("utf-8", "replace") if isinstance(error.stdout, bytes) else error.stdout or "",
                "stderr": (error.stderr or b"").decode("utf-8", "replace") if isinstance(error.stderr, bytes) else error.stderr or "", "timed_out": True}

    def register_actor(self, actor, role, assignment):
        if not actor or not assignment:
            raise ValueError("actual actor and host assignment are required")
        agents = self.runtime.snapshot()["agents"]
        found = next((a for a in agents if a["id"] == actor), None)
        if found and found["role"] != role:
            raise ValueError("actual identity already has a different role; do not invent another identity")
        if not found:
            self.api("agent.register", {"id": actor, "role": role}, "actor-" + actor)

    def artifact(self, ident, kind, title, content, *, actor=None):
        return self.api("artifact.create", {"project_id": self.index["project_id"], "artifact_id": ident,
            "artifact_type": kind, "title": title, "state": "BASELINED", "content_ref": content,
            "source": self.source(actor or self.index["author"])}, ident)

    def evidence(self, ident, kind, locator, actor, metadata):
        existing = next((e for e in self.runtime.lifecycle_snapshot(self.index["project_id"], limit=500)["evidence"] if e["id"] == ident), None)
        if existing:
            same_locator = all(existing["locator"].get(k) == v for k, v in locator.items())
            if existing["kind"] != kind or existing["recorded_by"] != actor or existing["metadata"] != metadata or not same_locator:
                raise ValueError("existing immutable evidence differs; explicit recovery required")
            return existing
        return self.api("evidence.register", {"project_id": self.index["project_id"], "evidence_id": ident, "kind": kind,
            "status": "VERIFIED", "source": self.source(actor), "locator": locator, "observed_at": now(), "metadata": metadata}, ident)

    def link(self, first, last, relation):
        return self.api("trace.link", {"project_id": self.index["project_id"], "from": first, "to": last, "relation": relation},
            "link:" + first["id"] + ":" + last["id"] + ":" + relation)

    def prepare(self, actor, assignment, documents_dir):
        if not actor or not assignment:
            raise ValueError("actual actor and host assignment are required")
        snapshot = self.runtime.snapshot()
        if self.index.get("prepared"):
            if actor != self.index["author"] or self.file_hashes() != self.index["source_hashes"]:
                raise ValueError("resume actor or source baseline differs")
            return self.export()
        docs = documents_dir.resolve()
        if not docs.is_relative_to(self.root) or docs == self.root or docs.is_relative_to(self.root / APP_DIR):
            raise ValueError("documents directory must be confined outside the application")
        if not self.index:
            if snapshot["projects"]:
                raise ValueError("database already contains project facts without this run index; explicit recovery required")
            self.index = {"run_id": "python-lifecycle-" + uuid4().hex, "author": actor, "assignment": assignment,
                "observed_at": now(), "documents_dir": str(docs), "source_hashes": self.file_hashes()}
            self.save()
        if actor != self.index["author"]:
            raise ValueError("prepare must resume the original author")
        write_json(self.output / "initial-snapshot.json", snapshot)
        self.register_actor(actor, "developer", assignment)
        if "project_id" not in self.index:
            project = self.api("project.create", {"name": "Existing Python expense CLI per-requirement lifecycle",
                "idea": "TASK-V3-008: verify existing application, preserve source, actual independent tests and review, no generated approval"}, "project")
            self.index["project_id"] = project["id"]
            self.save()
        pid = self.index["project_id"]
        self.api("lifecycle.initialize", {"project_id": pid, "repository_root": str(self.root), "mode": "active"}, "initialize")
        preparation = self.api("work.create", {"project_id": pid, "gate_id": "G3", "activity": "Prepare current adopted-source requirements and risk model",
            "required_role": "developer", "why": assignment + "; allowed outputs are the selected isolated directory and current lifecycle documents; application read-only",
            "input_refs": [], "dependencies": [], "output_contract": {"required_types": ["REQ", "TEST_MODEL", "TEST_CASE"], "min_outputs": 3}}, "preparation-work")
        prepared_claim = self.api("work.claim", {"work_order_id": preparation["id"], "agent_id": actor, "lease_seconds": 600}, "prepare-claim")
        preparation_lease = {"work_order_id": preparation["id"], "agent_id": actor, "lease_token": prepared_claim["lease_token"]}
        probe = self.process([sys.executable, "-B", "-X", "utf8", "-m", "rd_platform", "stack-probe"])
        write_json(self.output / "tool-probe.json", probe)
        if probe["exit_code"] != 0 or json.loads(probe["stdout"])["python"]["status"] != "AVAILABLE":
            raise RuntimeError("Python probe unavailable; see actual tool-probe.json")
        commit = self.process(["git", "log", "-1", "--format=%H", "--", str(APP_DIR / "expense_analyzer.py")])
        blob = self.process(["git", "hash-object", str(APP_DIR / "expense_analyzer.py")])
        if commit["exit_code"] or blob["exit_code"] or not re.fullmatch(r"[0-9a-f]{40,64}", commit["stdout"].strip()):
            raise RuntimeError("actual source Git provenance unavailable")
        baseline = {"kind": "EXISTING_SOURCE_BASELINE", "original_task_id": "TASK-V3-003",
            "git_commit": commit["stdout"].strip(), "working_tree_blob": blob["stdout"].strip(),
            "source_hashes": self.index["source_hashes"], "observed_at": self.index["observed_at"],
            "current_author_is_original_developer": False, "new_application_code": False,
            "origin": "Current Git record and existing source, not reconstructed historic approvals"}
        write_once(docs / "source-baseline.json", json.dumps(baseline, ensure_ascii=False, indent=2) + "\n")
        self.artifact("BG-PLC-001", "BG", "核对既有费用工具并取得逐需可核查证据", self.content(self.root / DOC_DIR / "project-model.md"))
        self.artifact("PRD-PLC-001", "PRD", "Local CLI user journey and measurable acceptance", self.content(self.root / DOC_DIR / "project-model.md"))
        self.artifact("DES-PLC-001", "DES", "Observed current source architecture", self.content(self.root / DOC_DIR / "architecture.md"))
        self.artifact("ADR-PLC-001", "ADR", "Adopt fixed existing implementation and real-role evidence", self.content(self.root / DOC_DIR / "architecture.md"))
        self.artifact("TASK-V3-003", "TASK", "Observed historical Python application task", {"inline_json": {
            "observation": "Existing task reference in source and implementation.md, not work newly executed by this project",
            "original_document": "docs/platform-v3/apps/python_expenses/implementation.md", "baseline": baseline}})
        self.artifact("CODE-MATRIX-PYTHON-EXPENSES", "CODE_CHANGE", "Existing source baseline from actual Git", self.content(docs / "source-baseline.json"))
        self.artifact("CODE-PLC-HARNESS", "CODE_CHANGE", "TASK-V3-008 current harness; new commit PENDING", self.content(Path(__file__)))
        self.artifact("DOC-PLC-REVIEW-SCOPE", "DOC", "Independent review contract, conclusions pending", self.content(self.root / DOC_DIR / "review-contract.md"))
        for ident, acceptance in REQS.items():
            self.artifact(ident, "NFR" if ident.startswith("NFR") else "REQ", acceptance, {"inline_json": {
                "acceptance": acceptance, "source": "Existing DRAFT specification and initial model",
                "current_interpretation": "BASELINED for authorized verification; not human approval",
                "document": self.content(self.root / DOC_DIR / "requirements.md"), "human_approval": "PENDING"}})
            self.link(ref("BG-PLC-001", "BG"), ref(ident), "refines")
            self.link(ref("PRD-PLC-001", "PRD"), ref(ident), "refines")
            self.link(ref(ident), ref("DES-PLC-001", "DES"), "realized_by")
        self.link(ref("DES-PLC-001", "DES"), ref("TASK-V3-003", "TASK"), "planned_by")
        self.link(ref("TASK-V3-003", "TASK"), ref("CODE-MATRIX-PYTHON-EXPENSES", "CODE_CHANGE"), "implemented_by")
        for gate, filename in {"G0": "project-model.md", "G1": "project-model.md", "G2": "project-model.md",
                                "G3": "requirements.md", "G4": "architecture.md", "G5": "plan.md", "G6": "plan.md"}.items():
            document = self.artifact("DOC-PLC-" + gate, "DOC", gate + " current verification material", self.content(self.root / DOC_DIR / filename))
            criteria = sorted(set(POLICY[gate]) - REVIEW_CRITERIA - TEST_CRITERIA)
            self.evidence("EVD-PLC-DOC-" + gate, "document", self.content(self.root / DOC_DIR / filename), actor,
                {"gate_id": gate, "criteria": criteria, "artifact_refs": [ref(document["id"], "DOC"), ref("CODE-MATRIX-PYTHON-EXPENSES", "CODE_CHANGE")]})
        model = {"project_id": pid, "artifact_id": "TM-PLC-001", "title": "Per-requirement risk test model",
            "source": self.source(actor), "state": "BASELINED", "requirement_refs": [ref(i) for i in REQS],
            "function_tree": {"expense_cli": ["CSV decode and shape", "business validation", "exact totals", "errors", "resource boundaries", "input integrity"]},
            "objects": [{"object_id": "CLI", "description": "Unmodified public CLI and actual existing unit suite"}],
            "types": sorted({c["type"] for c in case_catalog()}),
            "risks": [{"risk_id": "RISK-" + ident, "description": acceptance, "likelihood": "MEDIUM", "impact": "HIGH", "priority": "P0", "requirement_refs": [ref(ident)]} for ident, acceptance in REQS.items()],
            "test_points": [{"point_id": "TP-" + c["id"], "object_id": "CLI", "type": c["type"], "rationale": "Observe the exact named input partition",
                "risk_refs": ["RISK-" + r for r in c["requirements"]], "requirement_refs": [ref(r) for r in c["requirements"]],
                "coverage_rule": c["id"] + ": " + json.dumps(c["data"], ensure_ascii=False)} for c in case_catalog()]}
        self.api("test_model.create", model, "model")
        for case in case_catalog():
            expected = json.dumps({"exit_code": case["exit_code"], "json": case["expected"],
                "decimal_value": case["data"].get("decimal_expected"), "error_stdout_empty": case["exit_code"] != 0,
                "input_and_source_unchanged": True}, ensure_ascii=False)
            self.api("test_case.create", {"project_id": pid, "case_id": case["id"], "test_model_id": "TM-PLC-001",
                "test_point_refs": ["TP-" + case["id"]], "requirement_refs": [ref(r) for r in case["requirements"]],
                "test_type": case["type"], "module": "python_expenses", "priority": "P1" if case["requirements"] == ["NFR-MATRIX-PY-002"] else "P0", "risk": "HIGH",
                "preconditions": ["Actual tester differs from harness developer", "Fixed existing source hash", "Synthetic local input", "No application modification"],
                "test_data": case["data"], "steps": [{"order": 1, "action": "Materialize the exact declared bytes or row recipe in isolated build fixtures", "expected_observation": "Input SHA-256 recorded before execution"},
                    {"order": 2, "action": "Execute declared public argv and capture exit/stdout/stderr", "expected_observation": expected},
                    {"order": 3, "action": "Compare input/source hashes and every declared assertion", "expected_observation": "Unchanged input and source; record actual result without default PASS"}],
                "expected_result": expected, "automation": {"status": "AUTOMATED", "method": "public CLI subprocess and explicit independent assertions", "tool": "Python standard library", "entrypoint": "scripts/validate_python_lifecycle.py execute"},
                "state": "BASELINED"}, case["id"])
        self.api("work.heartbeat", preparation_lease, "prepare-heartbeat")
        self.api("work.finish", dict(preparation_lease, status="DONE", output_refs=[ref(next(iter(REQS))), ref("TM-PLC-001", "TEST_MODEL"), ref(case_catalog()[0]["id"], "TEST_CASE")],
            summary="Actual prepared current documents, source provenance, 7 requirement/NFR artifacts and separately versioned test cases; no testing or approval fabricated"), "prepare-work-finish")
        self.index.update(prepared=True, preparation_work_id=preparation["id"], cases=[c["id"] for c in case_catalog()], baseline=baseline)
        self.save()
        return self.export()

    def run_case(self, case):
        build = self.output / "build"
        fixtures = build / "fixtures"
        fixtures.mkdir(parents=True, exist_ok=True)
        path = fixtures / (case["id"] + ".csv")
        data = case["data"]
        argv = [sys.executable, "-B", "-X", "utf8", str(self.root / APP_DIR / "expense_analyzer.py")]
        before = None
        if data.get("unit_suite"):
            argv = [sys.executable, "-X", "utf8", "-X", "pycache_prefix=" + str(build / "pycache"), "-m", "unittest", "discover", "-s", str(self.root / APP_DIR / "tests"), "-v"]
        elif not data.get("no_args"):
            if data.get("missing_file") or data.get("extra_arg"):
                if path.exists():
                    raise ValueError("expected absent test path already exists")
            else:
                if "input_base64" in data:
                    raw = base64.b64decode(data["input_base64"], validate=True)
                elif "rows" in data:
                    raw = ("date,category,amount\n" + "2026-09-06,a,1\n" * data["rows"]).encode()
                else:
                    raw = data["csv"].encode("utf-8")
                if path.exists() and path.read_bytes() != raw:
                    raise ValueError("existing fixture bytes differ; retain evidence and investigate")
                path.write_bytes(raw)
                before = sha(path)
            argv.append(str(path))
            if data.get("extra_arg"):
                argv.append("unexpected-second-path.csv")
        actual = self.process(argv)
        checks = {"expected_exit": actual["exit_code"] == case["exit_code"], "terminated": not actual["timed_out"],
            "input_unchanged": before is None or (path.exists() and sha(path) == before), "source_unchanged": self.file_hashes() == self.index["source_hashes"]}
        if data.get("unit_suite"):
            count = re.search(r"Ran (\d+) tests?\b", actual["stderr"])
            actual["test_count"] = int(count.group(1)) if count else 0
            checks.update(nonzero_test_collection=actual["test_count"] > 0, unittest_ok=bool(re.search(r"(?m)^OK\s*$", actual["stderr"])))
        elif case["exit_code"] == 0:
            try:
                parsed = json.loads(actual["stdout"])
                values = list(parsed["categories"].values()) + [parsed["total"]]
                checks.update(json_strings=all(isinstance(v, str) for v in values), categories_sorted=list(parsed["categories"]) == sorted(parsed["categories"]), stderr_empty=actual["stderr"] == "")
                if case["expected"] is not None:
                    checks["exact_json"] = parsed == case["expected"]
                if data.get("decimal_expected") is not None:
                    checks["exact_decimal"] = Decimal(parsed["total"]) == Decimal(data["decimal_expected"])
                    checks["exact_category"] = len(parsed["categories"]) == 1 and Decimal(values[0]) == Decimal(data["decimal_expected"])
            except (ValueError, KeyError, TypeError, AttributeError, DecimalException):
                checks["valid_json_contract"] = False
        else:
            checks.update(stdout_empty=actual["stdout"] == "", stderr_prefix=actual["stderr"].startswith("error:" if case["exit_code"] == 1 else "usage:"))
        return {"case_id": case["id"], "input_sha256": before, "actual": actual, "assertions": checks,
            "result": "PASS" if all(checks.values()) else "FAIL"}

    @staticmethod
    def stable_result_rows(rows):
        """Normalize only known additive annotations, never execution facts.

        Pre-freshness reports stored result as the observed result. The current
        report is separately revalidated from Runtime before this normalization;
        NOT_CHECKED is compatible historical syntax, not evidence of freshness.
        Unknown annotations and every identity/version/result/ref remain exact.
        """
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("execution report result rows must be objects")
        normalized = []
        for row in rows:
            if row.get("freshness", "NOT_CHECKED") not in {"NOT_CHECKED", "CURRENT", "NOT_APPLICABLE"} or row.get("freshness_reason") is not None:
                raise ValueError("current case/execution versions or evidence are stale or unverifiable")
            stable = dict(row)
            stable.setdefault("observed_result", row.get("result"))
            stable.pop("freshness", None)
            stable.pop("freshness_reason", None)
            normalized.append(stable)
        return normalized

    def execution_report(self, snapshot, actor, *, require_existing=False):
        """Reuse an immutable report only while its actual execution binding holds."""
        if any(snapshot.get("collections_truncated", {}).values()):
            raise ValueError("complete lifecycle snapshot required to bind the execution report")
        current = lifecycle_report(snapshot)
        # Raw snapshots retain history but do not revalidate path-backed EVD.
        # Use the formal current projection for validity, while retaining the
        # original unsanitized environment/source binding in the saved document.
        effective = lifecycle_report_from_runtime(self.runtime, self.index["project_id"])
        rows_fields = ("case_results", "execution_records")
        for field in rows_fields:
            if any(row.get("observed_result") in {"PASS", "FAIL"} and row.get("freshness") != "CURRENT" for row in effective[field]):
                raise ValueError("current case/execution versions or evidence are not verified current")
            if self.stable_result_rows(current[field]) != self.stable_result_rows(effective[field]):
                raise ValueError("current case/execution versions or evidence no longer verify")
        if any(current[field] != effective[field] for field in ("counts", "total", "executed", "conclusion", "complete_snapshot")):
            raise ValueError("current case/execution results or evidence no longer verify")
        path = Path(self.index["documents_dir"]) / "test-report.md"
        prefix = "# 实际逐需求测试报告\n\n本次实际Tester: " + actor + "\n\n```json\n"
        suffix = "\n```\n"
        registered = next((a for a in snapshot["artifacts"] if a["id"] == "DOC-PLC-TEST-REPORT"), None)
        if not path.exists():
            if require_existing or registered:
                raise ValueError("persisted execution report is missing; explicit recovery required")
            write_once(path, prefix + json.dumps(current, ensure_ascii=False, indent=2) + suffix)
            return current
        text = path.read_text(encoding="utf-8")
        if not text.startswith(prefix) or not text.endswith(suffix):
            raise ValueError("persisted execution report format or actual tester differs")
        try:
            saved = json.loads(text[len(prefix):-len(suffix)], parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (ValueError, TypeError) as error:
            raise ValueError("persisted execution report JSON is invalid") from error
        if not isinstance(saved, dict):
            raise ValueError("persisted execution report must contain an object")
        if registered and (registered["content_ref"] != self.content(path) or registered["created_by"] != actor):
            raise ValueError("persisted execution report content or registered source differs")
        # These facts bind the report to exact current subjects and real results.
        # generated_at, Gate status and collection counts may legitimately differ
        # because the report artifact/EVD were registered after report generation.
        fields = ("project_id", "report_scope", "counts",
                  "total", "executed", "conclusion", "test_types", "defects", "complete_snapshot")
        if (any(saved.get(field) != current.get(field) for field in fields)
                or any(self.stable_result_rows(saved.get(field)) != self.stable_result_rows(current[field]) for field in rows_fields)):
            raise ValueError("persisted execution report no longer matches current case/execution versions or results")
        environment_ids = {e["environment_ref"]["id"] for e in snapshot["test_executions"]}
        saved_environments = {e["id"]: e for e in saved.get("test_environment", [])}
        current_environments = {e["id"]: e for e in current["test_environment"]}
        for ident in environment_ids:
            saved_environment = saved_environments.get(ident)
            if not saved_environment or saved_environment != current_environments.get(ident):
                raise ValueError("persisted execution report environment differs")
            source_hashes = saved_environment["locator"].get("inline_json", {}).get("source_hashes")
            if source_hashes != self.index["source_hashes"]:
                raise ValueError("persisted execution report source baseline differs")
        return saved

    def execute(self, actor, assignment):
        if not self.index.get("prepared"):
            raise ValueError("prepare must complete first")
        if actor == self.index["author"]:
            raise ValueError("harness developer cannot act as independent tester")
        if self.index.get("tester") and actor != self.index["tester"]:
            raise ValueError("resume must use the recorded actual tester identity")
        if self.file_hashes() != self.index["source_hashes"]:
            raise ValueError("source baseline drift; explicit change/review required")
        self.register_actor(actor, "tester", assignment)
        pid = self.index["project_id"]
        snap = self.runtime.lifecycle_snapshot(pid, limit=500)
        if any(e["status"] == "ACTIVE" for e in snap["test_executions"]):
            raise ValueError("active execution needs explicit host recovery; cannot silently replay")
        if self.index.get("executed"):
            self.execution_report(snap, actor, require_existing=True)
            return self.export()
        self.index["tester"] = actor
        self.save()
        work = self.api("work.create", {"project_id": pid, "gate_id": "G7", "activity": "Independent per-requirement execution of existing Python CLI",
            "required_role": "tester", "why": assignment, "input_refs": [ref(i) for i in REQS] + [ref("TM-PLC-001", "TEST_MODEL")],
            "dependencies": [self.index["preparation_work_id"]], "output_contract": {"required_types": ["TEST_EXECUTION", "EVIDENCE"], "min_outputs": 2}}, "execution-work")
        durable_work = next(w for w in snap["work_orders"] if w["id"] == work["id"]) if any(w["id"] == work["id"] for w in snap["work_orders"]) else work
        if durable_work["status"] in {"DONE", "FAILED"}:
            report = self.execution_report(snap, actor, require_existing=True)
            expected_status = "DONE" if report["conclusion"] == "PASS" else "FAILED"
            expected_executions = {(e["id"], e.get("version", 1)) for e in snap["test_executions"]}
            recorded_executions = {(r["id"], r["version"]) for r in durable_work.get("output_refs", []) if r["type"] == "TEST_EXECUTION"}
            if durable_work["agent_id"] != actor or durable_work["status"] != expected_status or expected_executions != recorded_executions:
                raise ValueError("completed work conflicts with the persisted execution report")
            self.index.update(executed=True, work_id=work["id"], executed_at=durable_work["finished_at"])
            self.save()
            return self.export()
        claimed = self.api("work.claim", {"work_order_id": work["id"], "agent_id": actor, "lease_seconds": 600}, "claim")
        lease = {"work_order_id": work["id"], "agent_id": actor, "lease_token": claimed["lease_token"]}
        env = self.evidence("EVD-PLC-ENV", "test_environment", {"inline_json": {"python": sys.version, "platform": sys.platform,
            "source_hashes": self.index["source_hashes"], "host_assignment": assignment, "build_directory": str(self.output / "build")}}, actor,
            {"gate_id": "G7", "criteria": ["test_environment"], "artifact_refs": [ref("CODE-MATRIX-PYTHON-EXPENSES", "CODE_CHANGE")]})
        outputs, results = [], []
        for case in case_catalog():
            prior = [e for e in snap["test_executions"] if e["case_id"] == case["id"] and e["case_version"] == 1 and e["status"] == "FINISHED"]
            if prior:
                outputs.extend([ref(prior[-1]["id"], "TEST_EXECUTION")] + prior[-1]["evidence_refs"])
                continue
            execution = self.api("test_execution.start", {"case_id": case["id"], "case_version": 1, "executor_id": actor,
                "environment_ref": ref(env["id"], "EVIDENCE")}, case["id"] + ":start")
            result = self.run_case(case)
            result.update(execution_id=execution["id"], case_version=1, executor=actor,
                registration_timing="start precedes actual subprocess; evidence follows process completion")
            path = self.output / "results" / (execution["id"] + ".json")
            write_json(path, result)
            unit = case["data"].get("unit_suite")
            evidence = self.evidence("EVD-" + execution["id"], "test_execution", self.content(path), actor,
                {"execution_id": execution["id"], "result": result["result"], "gate_id": "G6" if unit else "G7",
                    "criteria": ["unit_tests", "local_verification"] if unit else ["test_results"],
                    "artifact_refs": [ref(case["id"], "TEST_CASE")] + [ref(r) for r in case["requirements"]]})
            self.api("test_execution.finish", {"execution_id": execution["id"], "result": result["result"],
                "actual_result": json.dumps(result["assertions"]), "evidence_refs": [ref(evidence["id"], "EVIDENCE")]}, case["id"] + ":finish")
            self.link(ref(execution["id"], "TEST_EXECUTION"), ref(evidence["id"], "EVIDENCE"), "evidenced_by")
            outputs.extend([ref(execution["id"], "TEST_EXECUTION"), ref(evidence["id"], "EVIDENCE")])
            results.append(result)
            self.api("work.heartbeat", lease, case["id"] + ":heartbeat")
        snap = self.runtime.lifecycle_snapshot(pid, limit=500)
        report = self.execution_report(snap, actor)
        docs = Path(self.index["documents_dir"])
        report_artifact = self.artifact("DOC-PLC-TEST-REPORT", "DOC", "Actual current per-requirement execution report", self.content(docs / "test-report.md"), actor=actor)
        report_ref = ref(report_artifact["id"], "DOC")
        self.evidence("EVD-PLC-G7-DOC", "document", self.content(docs / "test-report.md"), actor,
            {"gate_id": "G7", "criteria": ["test_plan", "executable_cases", "defect_summary"], "artifact_refs": [report_ref, ref("TM-PLC-001", "TEST_MODEL")]})
        last = snap["test_executions"][-1]
        if report["conclusion"] == "PASS":
            conclusion = self.evidence("EVD-PLC-CONCLUSION", "test_execution", self.content(docs / "test-report.md"), actor,
                {"execution_id": last["id"], "result": "PASS", "gate_id": "G7", "criteria": ["regression", "test_conclusion"],
                    "artifact_refs": [ref(last["case_id"], "TEST_CASE", last["case_version"]), report_ref],
                    "consolidates_actual_execution_ids": [e["id"] for e in snap["test_executions"]]})
            outputs.append(ref(conclusion["id"], "EVIDENCE"))
        self.api("work.finish", dict(lease, status="DONE" if report["conclusion"] == "PASS" else "FAILED", output_refs=outputs,
            summary=f"Actual current scope {report['counts']}; no independent review or human approval synthesized"), "execution-work-finish")
        self.index.update(executed=True, work_id=work["id"], executed_at=now())
        self.save()
        return self.export()

    def export(self):
        if "project_id" not in self.index:
            raise ValueError("project not prepared")
        snap = self.runtime.lifecycle_snapshot(self.index["project_id"], limit=500)
        report = lifecycle_report_from_runtime(self.runtime, self.index["project_id"])
        write_json(self.output / "lifecycle.json", snap)
        write_json(self.output / "test-report.json", report)
        coverage = [{"requirement_id": ident, "cases": [c for c in report["case_results"] if any(r["id"] == ident for r in c["requirement_refs"])]} for ident in REQS]
        write_json(self.output / "requirement-coverage.json", coverage)
        subjects = [ref(i) for i in REQS] + [ref("DES-PLC-001", "DES"), ref("CODE-MATRIX-PYTHON-EXPENSES", "CODE_CHANGE"), ref("CODE-PLC-HARNESS", "CODE_CHANGE"), ref("DOC-PLC-REVIEW-SCOPE", "DOC")]
        current_versions = {a["id"]: a["version"] for a in snap["artifacts"]}
        subjects = [dict(subject, version=current_versions[subject["id"]]) for subject in subjects]
        plan = {"fact_status": "REQUEST_TEMPLATES_ONLY_NOT_APPROVAL", "project_id": self.index["project_id"],
            "db": str(self.output / "state.db"), "independent_review_required": {g: sorted(set(POLICY[g]) & REVIEW_CRITERIA) for g in ("G3", "G4", "G8")},
            "review_subject_refs": subjects,
            "ordered_gates": [{"gate_id": f"G{i}", "assess": {"command": "gate.assess", "data": {"project_id": self.index["project_id"], "gate_id": f"G{i}"}},
                "decision": {"command": "gate.decide", "data": {"assessment_id": "ACTUAL_CURRENT_ASSESSMENT_ID", "status": "ACTUAL_REVIEWER_DECISION", "decided_by": "ACTUAL_INDEPENDENT_REVIEWER", "decision_evidence_refs": [ref("ACTUAL_REGISTERED_DECISION_EVIDENCE", "EVIDENCE")]}}} for i in range(9)],
            "G9": "PENDING actual human acceptance; default approval provider NOT_AVAILABLE"}
        write_json(self.output / "promotion-plan.json", plan)
        return {"project_id": self.index["project_id"], "output_dir": str(self.output), "documents_dir": self.index["documents_dir"],
            "prepared": self.index.get("prepared", False), "executed": self.index.get("executed", False), "case_count": report["total"],
            "counts": report["counts"], "traceability": snap["traceability"], "gates": [{"gate_id": g["gate_id"], "status": g["gate_status"]} for g in snap["gates"]],
            "recommend_release": False, "review": "PENDING unless separately recorded by independent reviewer", "human_acceptance": "PENDING"}

    def finalize(self, review_bundle: Path | None):
        if review_bundle is None:
            raise ValueError("finalize requires externally registered real review evidence IDs; no default PASS")
        bundle = json.loads(review_bundle.read_text(encoding="utf-8"))
        reviewer = bundle.get("reviewer_id")
        ids = bundle.get("evidence_ids")
        if not reviewer or not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
            raise ValueError("reviewer_id and unique non-empty evidence_ids required")
        snap = self.runtime.lifecycle_snapshot(self.index["project_id"], limit=500)
        if reviewer == self.index["author"] or reviewer in {e["executor_id"] for e in snap["test_executions"]}:
            raise ValueError("reviewer must differ from actual developer and all testers")
        agent = next((a for a in self.runtime.snapshot()["agents"] if a["id"] == reviewer), None)
        if not agent or agent["role"] != "reviewer":
            raise ValueError("already registered independent reviewer required")
        evidence = [e for e in snap["evidence"] if e["id"] in ids]
        if len(evidence) != len(ids):
            raise ValueError("review evidence ID absent from this project")
        required_subjects = {i for i in REQS} | {"DES-PLC-001", "CODE-MATRIX-PYTHON-EXPENSES", "CODE-PLC-HARNESS", "DOC-PLC-REVIEW-SCOPE"}
        subjects = set()
        coverage = {g: set() for g in ("G3", "G4", "G8")}
        for e in evidence:
            if e["kind"] != "review" or e["status"] != "VERIFIED" or e["recorded_by"] != reviewer or e["recorded_role"] != "reviewer" or e["metadata"].get("result") != "PASS":
                raise ValueError("actual verified passing independent review evidence required")
            locator = e["locator"]
            if "path" in locator and sha(self.root / locator["path"]) != locator["sha256"]:
                raise ValueError("review content changed")
            for subject in e["metadata"].get("artifact_refs", []):
                current = next((a for a in snap["artifacts"] if a["id"] == subject["id"]), None)
                if current and current["version"] != subject["version"]:
                    raise ValueError("review references stale subject version")
                subjects.add(subject["id"])
            gates = e["metadata"].get("gate_ids", []) + [e["metadata"].get("gate_id")]
            for gate in coverage:
                if gate in gates:
                    coverage[gate].update(e["metadata"].get("criteria", []))
        if required_subjects - subjects or any((set(POLICY[g]) & REVIEW_CRITERIA) - criteria for g, criteria in coverage.items()):
            raise ValueError("review subjects or G3/G4/G8 criteria are incomplete")
        result = self.export()
        missing = [g["gate_id"] for g in snap["gates"] if int(g["gate_id"][1:]) <= 8 and g["gate_status"] != "PASS"]
        result.update(finalization="PENDING_GATE_DECISIONS" if missing else "G0_G8_COMPLETE_G9_PENDING", missing_gate_decisions=missing,
            review_evidence_ids=ids, independent_reviewer=reviewer, human_acceptance="PENDING", recommend_release=False)
        write_json(self.output / "finalization.json", result)
        return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute", "finalize"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--documents-dir", type=Path)
    parser.add_argument("--actor")
    parser.add_argument("--host-assignment")
    parser.add_argument("--review-evidence", type=Path)
    args = parser.parse_args(argv)
    try:
        harness = PythonLifecycle(args.output_dir)
        if args.mode == "prepare":
            if args.documents_dir is None:
                parser.error("prepare requires --documents-dir")
            result = harness.prepare(args.actor, args.host_assignment, args.documents_dir)
        elif args.mode == "execute":
            result = harness.execute(args.actor, args.host_assignment)
        else:
            result = harness.finalize(args.review_evidence)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 2 if result.get("finalization") == "PENDING_GATE_DECISIONS" else 1 if result["counts"]["FAIL"] else 0
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({"status": "PENDING", "reason": str(error), "recommend_release": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
