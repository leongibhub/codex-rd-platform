from dataclasses import dataclass
from pathlib import Path
import json
import re
import tomllib


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


GATE_TABLE_COLUMNS = [
    "Gate ID",
    "Gate Name",
    "Gate Status",
    "Evaluation State",
    "Baseline",
    "Evaluated At",
    "Evaluator Role",
    "Recorder",
    "Criteria Result",
    "Evidence IDs",
    "Blockers/Links",
    "Rationale",
    "Next Action",
    "Owner",
    "Target Date",
    "Human Approval Evidence",
]
RTM_TABLE_COLUMNS = [
    "Trace ID",
    "Scope Status",
    "BG",
    "PRD",
    "REQ/NFR",
    "Acceptance Criteria",
    "DES/ADR",
    "TASK",
    "CR",
    "Commit/MR",
    "TC",
    "Test Execution/Evidence",
    "Verification Result",
    "BUG",
    "Defect Disposition",
    "REL",
    "Traceability Status",
    "Evidence Status",
    "Last Verified",
]
GATE_STATUSES = {"PASS", "FAIL", "BLOCKED"}
EVALUATION_STATES = {"NOT_EVALUATED", "IN_REVIEW", "DECIDED"}
SCOPE_STATUSES = {"IN_SCOPE", "OUT_OF_SCOPE", "DEFERRED"}
TRACEABILITY_STATUSES = {"COMPLETE", "PARTIAL", "GAP", "NOT_APPLICABLE"}
EVIDENCE_STATUSES = {
    "PENDING",
    "NOT_AVAILABLE",
    "NOT_EXECUTED",
    "INFERRED",
    "OBSERVED",
    "VERIFIED",
}
VERIFICATION_RESULTS = {"PASS", "FAIL", "BLOCKED", "NOT_EXECUTED"}
UNUSABLE_EVIDENCE_STATUSES = {"PENDING", "NOT_AVAILABLE", "NOT_EXECUTED", "INFERRED"}
GATE_STATUS_TOKEN = "{{PASS|FAIL|BLOCKED}}"
EVALUATION_STATE_TOKEN = "{{NOT_EVALUATED|IN_REVIEW|DECIDED}}"
DEFAULT_RTM_PATH = "docs/03-requirements/requirement-traceability-matrix.md"


def load_manifest(root: Path) -> dict:
    return json.loads((root / "platform-manifest.json").read_text(encoding="utf-8"))


def collect_agent_ids(root: Path) -> set[str]:
    return {
        tomllib.loads(path.read_text(encoding="utf-8"))["name"]
        for path in (root / ".codex" / "agents").glob("*.toml")
    }


def collect_skill_ids(root: Path) -> set[str]:
    result = set()
    for path in (root / ".agents" / "skills").glob("*/SKILL.md"):
        name = _frontmatter_name(path.read_text(encoding="utf-8"))
        if name:
            result.add(name)
    return result


def _frontmatter_name(contents: str) -> str | None:
    lines = contents.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        return None

    for line in lines[1:closing_index]:
        key, separator, value = line.partition(":")
        if separator and key.strip() == "name":
            return _parse_simple_yaml_scalar(value.strip())
    return None


def _parse_simple_yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
        return value[1:-1]
    return value


def validate_manifest_contract(root: Path) -> list[ValidationIssue]:
    manifest = load_manifest(root)
    issues = []

    if set(manifest.get("agents", [])) != collect_agent_ids(root):
        issues.append(
            ValidationIssue(
                "MANIFEST_AGENTS_MISMATCH",
                "manifest agents do not match runtime agent identifiers",
            )
        )
    if set(manifest.get("skills", [])) != collect_skill_ids(root):
        issues.append(
            ValidationIssue(
                "MANIFEST_SKILLS_MISMATCH",
                "manifest skills do not match runtime skill identifiers",
            )
        )
    if manifest.get("gates") != [f"G{i}" for i in range(12)]:
        issues.append(
            ValidationIssue(
                "MANIFEST_GATES_INVALID",
                "manifest gates must be G0 through G11",
            )
        )
    if manifest.get("lifecycle_mode") not in {"template", "active"}:
        issues.append(
            ValidationIssue(
                "MANIFEST_LIFECYCLE_MODE_INVALID",
                "manifest lifecycle_mode must be template or active",
            )
        )

    return issues


def validate_gate_contract(root: Path, manifest: dict) -> list[ValidationIssue]:
    issues = []
    template_path = _manifest_path(manifest, "gate_register_template")
    if template_path is None or not _valid_gate_template(root / template_path, manifest):
        issues.append(
            ValidationIssue(
                "GOVERNANCE_GATE_TEMPLATE_INVALID",
                "gate register template must define the controlled G0 through G11 structure",
            )
        )

    if manifest.get("lifecycle_mode") != "active":
        return issues

    active_path = _manifest_path(manifest, "active_gate_register")
    if active_path is None or not (root / active_path).is_file():
        issues.append(
            ValidationIssue(
                "GOVERNANCE_ACTIVE_REGISTER_MISSING",
                "active lifecycle mode requires the central gate register",
            )
        )
    elif not _valid_active_gate_register(root / active_path, manifest):
        issues.append(
            ValidationIssue(
                "GOVERNANCE_ACTIVE_REGISTER_INVALID",
                "active gate register must contain unique controlled G0 through G11 records",
            )
        )
    return issues


def validate_rtm_contract(root: Path, manifest: dict) -> list[ValidationIssue]:
    rtm_path = _manifest_path(manifest, "requirement_traceability_matrix") or DEFAULT_RTM_PATH
    table = _read_markdown_table(root / rtm_path)
    if table is None or table[0] != RTM_TABLE_COLUMNS:
        return [
            ValidationIssue(
                "GOVERNANCE_RTM_HEADER_INVALID",
                "RTM must use the canonical 19-column auditable header",
            )
        ]

    rows = table[1]
    if manifest.get("lifecycle_mode") != "active":
        if rows:
            return [
                ValidationIssue(
                    "GOVERNANCE_RTM_TEMPLATE_ROWS_INVALID",
                    "template mode RTM must not contain requirement data rows",
                )
            ]
        return []

    if not rows:
        return [
            ValidationIssue(
                "GOVERNANCE_ACTIVE_RTM_ROWS_MISSING",
                "active lifecycle mode requires RTM rows for its REQ/NFR records",
            )
        ]
    if not all(_valid_active_rtm_row(row) for row in rows):
        return [
            ValidationIssue(
                "GOVERNANCE_ACTIVE_RTM_ROW_INVALID",
                "active RTM rows must use controlled states and evidence-backed combinations",
            )
        ]
    return []


def _manifest_path(manifest: dict, key: str) -> Path | None:
    value = manifest.get(key)
    if not isinstance(value, str) or not value:
        return None
    return Path(value)


def _valid_gate_template(path: Path, manifest: dict) -> bool:
    if not path.is_file():
        return False
    contents = path.read_text(encoding="utf-8")
    table = _read_markdown_table(path)
    if table is None or table[0] != GATE_TABLE_COLUMNS:
        return False
    if "Artifact Type: TEMPLATE" not in contents or "不得作为项目 Gate 证据" not in contents:
        return False
    return _valid_gate_rows(table[1], manifest, template=True)


def _valid_active_gate_register(path: Path, manifest: dict) -> bool:
    table = _read_markdown_table(path)
    return table is not None and table[0] == GATE_TABLE_COLUMNS and _valid_gate_rows(
        table[1], manifest, template=False
    )


def _valid_gate_rows(rows: list[list[str]], manifest: dict, *, template: bool) -> bool:
    expected_gates = manifest.get("gates")
    if expected_gates != [f"G{index}" for index in range(12)] or len(rows) != 12:
        return False
    if [row[0] for row in rows] != expected_gates or any(len(row) != len(GATE_TABLE_COLUMNS) for row in rows):
        return False

    gate_status_index = GATE_TABLE_COLUMNS.index("Gate Status")
    evaluation_index = GATE_TABLE_COLUMNS.index("Evaluation State")
    evidence_index = GATE_TABLE_COLUMNS.index("Evidence IDs")
    if template:
        return all(
            row[gate_status_index] == GATE_STATUS_TOKEN
            and row[evaluation_index] == EVALUATION_STATE_TOKEN
            for row in rows
        )
    return all(
        row[gate_status_index] in GATE_STATUSES
        and row[evaluation_index] in EVALUATION_STATES
        and (row[gate_status_index] != "PASS" or _is_actual_evidence(row[evidence_index]))
        for row in rows
    )


def _valid_active_rtm_row(row: list[str]) -> bool:
    if len(row) != len(RTM_TABLE_COLUMNS):
        return False
    values = dict(zip(RTM_TABLE_COLUMNS, row, strict=True))
    requirement_id = values["REQ/NFR"]
    if not re.fullmatch(r"(?:REQ|NFR)-[A-Za-z0-9._-]+", requirement_id):
        return False
    if values["Scope Status"] not in SCOPE_STATUSES:
        return False
    if values["Traceability Status"] not in TRACEABILITY_STATUSES:
        return False
    if values["Evidence Status"] not in EVIDENCE_STATUSES:
        return False
    if values["Verification Result"] not in VERIFICATION_RESULTS:
        return False
    if values["Scope Status"] == "IN_SCOPE" and not values["Acceptance Criteria"]:
        return False
    if values["Commit/MR"] and not all(values[field] for field in ("DES/ADR", "TASK")):
        return False
    if values["Verification Result"] == "PASS":
        if values["Evidence Status"] in UNUSABLE_EVIDENCE_STATUSES:
            return False
        if not all(values[field] for field in ("Test Execution/Evidence", "REL")):
            return False
    return True


def _is_actual_evidence(value: str) -> bool:
    return bool(value) and not value.startswith("{{")


def _read_markdown_table(path: Path) -> tuple[list[str], list[list[str]]] | None:
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines[:-1]):
        if not line.lstrip().startswith("|"):
            continue
        header = _table_cells(line)
        separator = _table_cells(lines[index + 1])
        if not header or len(header) != len(separator) or not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separator
        ):
            continue
        rows = []
        for row_line in lines[index + 2 :]:
            if not row_line.lstrip().startswith("|"):
                break
            row = _table_cells(row_line)
            if len(row) != len(header):
                return None
            rows.append(row)
        return header, rows
    return None


def _table_cells(line: str) -> list[str]:
    return [
        cell.strip().replace("\\|", "|")
        for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
    ]
