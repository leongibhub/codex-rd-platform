from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
import json
import re
import subprocess
import sys
import tomllib


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def validate_runtime_prerequisites(root: Path) -> list[ValidationIssue]:
    """Validate the local interpreter and MCP dependency range before stdio starts."""
    if tuple(sys.version_info[:2]) < (3, 11):
        return [ValidationIssue("PYTHON_VERSION_UNSUPPORTED", "Python 3.11 or later is required")]
    try:
        installed_version = importlib_metadata.version("mcp")
    except importlib_metadata.PackageNotFoundError:
        return [ValidationIssue("MCP_VERSION_UNSUPPORTED", "installed MCP version is unsupported")]
    except Exception:
        return [ValidationIssue("MCP_VERSION_UNSUPPORTED", "installed MCP version is unsupported")]
    parsed_version = _parse_version(installed_version)
    if parsed_version is None or not (
        _compare_versions(parsed_version, (2, 0, 0)) >= 0
        and _compare_versions(parsed_version, (3, 0, 0)) < 0
    ):
        return [ValidationIssue("MCP_VERSION_UNSUPPORTED", "installed MCP version is unsupported")]
    try:
        requirements = (root / "tools" / "mcp" / "company-context" / "requirements.txt").read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return [ValidationIssue("MCP_REQUIREMENT_INVALID", "MCP dependency requirement is invalid")]
    if not _has_mcp_v2_bounds(requirements):
        return [ValidationIssue("MCP_REQUIREMENT_INVALID", "MCP dependency requirement is invalid")]
    return []


def _parse_version(value: str) -> tuple[int, ...] | None:
    match = re.fullmatch(
        r"(?i)(\d+(?:\.\d+)*)(?:\.post\d+)?(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?",
        value.strip(),
    )
    if match is None:
        return None
    release_parts = match.group(1).split(".")
    if len(release_parts) > 8 or any(len(part) > 32 for part in release_parts):
        return None
    post_match = re.search(r"(?i)\.post(\d+)", value)
    if post_match is not None and len(post_match.group(1)) > 32:
        return None
    try:
        return tuple(int(part) for part in release_parts)
    except (TypeError, ValueError):
        return None


def _has_mcp_v2_bounds(requirements: str) -> bool:
    if any(
        re.match(
            r"^\s*(?:-(?:r|c)(?:\s|=|\S)|--(?:requirement|constraint)(?:\s|=))",
            line,
            flags=re.IGNORECASE,
        )
        for line in requirements.splitlines()
    ):
        return False
    constraints: list[tuple[str, tuple[int, ...]]] = []
    has_minimum = False
    has_maximum = False
    for raw_line in requirements.splitlines():
        line = raw_line.split("#", maxsplit=1)[0].strip()
        if not line:
            continue
        match = re.match(
            r"(?i)^mcp(?=$|\s|\[|[<>=!~])(?:\[[a-z0-9_.-]+(?:\s*,\s*[a-z0-9_.-]+)*\])?\s*(.*)$",
            line,
        )
        if match is None:
            continue
        for raw_constraint in match.group(1).split(","):
            constraint = re.fullmatch(r"\s*(>=|>|<=|<|==)\s*(\S+)\s*", raw_constraint)
            if constraint is None:
                return False
            version = _parse_version(constraint.group(2))
            if version is None:
                return False
            operator = constraint.group(1)
            constraints.append((operator, version))
            has_minimum |= operator == ">=" and _compare_versions(version, (2, 0, 0)) == 0
            has_maximum |= operator == "<" and _compare_versions(version, (3, 0, 0)) == 0
    return bool(constraints) and has_minimum and has_maximum and _constraints_are_satisfiable(constraints)


def _compare_versions(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    length = max(len(left), len(right), 3)
    left_normalized = left + (0,) * (length - len(left))
    right_normalized = right + (0,) * (length - len(right))
    return (left_normalized > right_normalized) - (left_normalized < right_normalized)


def _constraints_are_satisfiable(constraints: list[tuple[str, tuple[int, ...]]]) -> bool:
    lower: tuple[tuple[int, ...], bool] | None = None
    upper: tuple[tuple[int, ...], bool] | None = None
    for operator, version in constraints:
        if operator == "==":
            candidates = ((">=", version), ("<=", version))
        else:
            candidates = ((operator, version),)
        for bound_operator, bound_version in candidates:
            if bound_operator in {">", ">="}:
                inclusive = bound_operator == ">="
                if lower is None or _compare_versions(bound_version, lower[0]) > 0 or (
                    _compare_versions(bound_version, lower[0]) == 0 and not inclusive
                ):
                    lower = (bound_version, inclusive)
            else:
                inclusive = bound_operator == "<="
                if upper is None or _compare_versions(bound_version, upper[0]) < 0 or (
                    _compare_versions(bound_version, upper[0]) == 0 and not inclusive
                ):
                    upper = (bound_version, inclusive)
    if lower is None or upper is None:
        return True
    comparison = _compare_versions(lower[0], upper[0])
    return comparison < 0 or (comparison == 0 and lower[1] and upper[1])


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
DEFECT_DISPOSITIONS = {
    "OPEN",
    "IN_PROGRESS",
    "RESOLVED",
    "CLOSED",
    "ACCEPTED_RISK",
    "NOT_APPLICABLE",
}
UNUSABLE_EVIDENCE_STATUSES = {"PENDING", "NOT_AVAILABLE", "NOT_EXECUTED", "INFERRED"}
GATE_STATUS_TOKEN = "{{PASS|FAIL|BLOCKED}}"
EVALUATION_STATE_TOKEN = "{{NOT_EVALUATED|IN_REVIEW|DECIDED}}"
DEFAULT_RTM_PATH = "docs/03-requirements/requirement-traceability-matrix.md"
GATE_DECISION_REQUIRED_FIELDS = (
    "Baseline",
    "Evaluated At",
    "Evaluator Role",
    "Recorder",
    "Criteria Result",
    "Evidence IDs",
    "Rationale",
    "Next Action",
    "Owner",
    "Target Date",
)
COMPLETE_TRACEABILITY_FIELDS = (
    "BG",
    "PRD",
    "REQ/NFR",
    "Acceptance Criteria",
    "DES/ADR",
    "TASK",
    "Commit/MR",
    "TC",
)
PLACEHOLDER_VALUES = {
    "-",
    "tbd",
    "todo",
    "pending",
    "not_available",
    "not available",
    "not_executed",
    "not executed",
    "inferred",
    "n/a",
    "na",
}


def load_manifest(root: Path) -> dict:
    return json.loads((root / "platform-manifest.json").read_text(encoding="utf-8"))


def collect_agent_ids(root: Path) -> set[str]:
    return set(_collect_agent_declarations(root))


def _collect_agent_declarations(root: Path) -> list[str]:
    return [
        tomllib.loads(path.read_text(encoding="utf-8"))["name"]
        for path in sorted((root / ".codex" / "agents").glob("*.toml"))
    ]


def collect_skill_ids(root: Path) -> set[str]:
    return set(_collect_skill_declarations(root))


def _collect_skill_declarations(root: Path) -> list[str]:
    result = []
    for path in sorted((root / ".agents" / "skills").glob("*/SKILL.md")):
        name = _frontmatter_name(path.read_text(encoding="utf-8"))
        if name:
            result.append(name)
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
    manifest_agents = manifest.get("agents", [])
    manifest_skills = manifest.get("skills", [])
    agent_declarations = _collect_agent_declarations(root)
    skill_declarations = _collect_skill_declarations(root)

    if not isinstance(manifest_agents, list) or len(manifest_agents) != len(set(manifest_agents)):
        issues.append(ValidationIssue("MANIFEST_AGENT_IDS_DUPLICATE", "manifest agent identifiers must be unique"))
    elif len(agent_declarations) != len(set(agent_declarations)):
        issues.append(ValidationIssue("RUNTIME_AGENT_IDS_DUPLICATE", "runtime agent identifiers must be unique"))
    elif set(manifest_agents) != set(agent_declarations):
        issues.append(
            ValidationIssue(
                "MANIFEST_AGENTS_MISMATCH",
                "manifest agents do not match runtime agent identifiers",
            )
        )
    if not isinstance(manifest_skills, list) or len(manifest_skills) != len(set(manifest_skills)):
        issues.append(ValidationIssue("MANIFEST_SKILL_IDS_DUPLICATE", "manifest skill identifiers must be unique"))
    elif len(skill_declarations) != len(set(skill_declarations)):
        issues.append(ValidationIssue("RUNTIME_SKILL_IDS_DUPLICATE", "runtime skill identifiers must be unique"))
    elif set(manifest_skills) != set(skill_declarations):
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
    elif not _valid_active_gate_register(root, root / active_path, manifest):
        issues.append(
            ValidationIssue(
                "GOVERNANCE_ACTIVE_REGISTER_INVALID",
                "active gate register must contain unique controlled G0 through G11 records",
            )
        )
    return issues


def validate_rtm_contract(root: Path, manifest: dict) -> list[ValidationIssue]:
    rtm_path = _manifest_path(manifest, "requirement_traceability_matrix") or DEFAULT_RTM_PATH
    rtm_document = root / rtm_path
    tables = _read_markdown_tables(rtm_document)
    if tables is None or len(tables) != 1 or tables[0][0] != RTM_TABLE_COLUMNS:
        return [
            ValidationIssue(
                "GOVERNANCE_RTM_HEADER_INVALID",
                "RTM must use the canonical 19-column auditable header",
            )
        ]

    rows = tables[0][1]
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
    if not _valid_active_rtm_rows(
        rows, root, (rtm_document, root / _manifest_path(manifest, "active_gate_register"))
    ):
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
    tables = _read_markdown_tables(path)
    if tables is None or len(tables) != 1 or tables[0][0] != GATE_TABLE_COLUMNS:
        return False
    if _metadata_value(contents, "Artifact Type") != "TEMPLATE" or "不得作为项目 Gate 证据" not in contents:
        return False
    return _valid_gate_rows(tables[0][1], manifest, template=True)


def _valid_active_gate_register(root: Path, path: Path, manifest: dict) -> bool:
    tables = _read_markdown_tables(path)
    return tables is not None and len(tables) == 1 and tables[0][0] == GATE_TABLE_COLUMNS and _valid_gate_rows(
        tables[0][1],
        manifest,
        template=False,
        root=root,
        excluded_paths=(path, root / _rtm_path(manifest)),
        evidence_source_path=path,
    )


def evaluated_gate_ids(root: Path, manifest: dict) -> list[str]:
    """Return only decided Gates from the active register's parsed canonical table."""
    if manifest.get("lifecycle_mode") != "active":
        return []
    active_path = _manifest_path(manifest, "active_gate_register")
    if active_path is None:
        return []
    tables = _read_markdown_tables(root / active_path)
    if tables is None or len(tables) != 1 or tables[0][0] != GATE_TABLE_COLUMNS:
        return []
    expected_gates = manifest.get("gates")
    rows = tables[0][1]
    if expected_gates != [f"G{index}" for index in range(12)] or [row[0] for row in rows] != expected_gates:
        return []
    evaluation_index = GATE_TABLE_COLUMNS.index("Evaluation State")
    return [row[0] for row in rows if row[evaluation_index] == "DECIDED"]


def _valid_gate_rows(
    rows: list[list[str]],
    manifest: dict,
    *,
    template: bool,
    root: Path | None = None,
    excluded_paths: tuple[Path, ...] = (),
    evidence_source_path: Path | None = None,
) -> bool:
    expected_gates = manifest.get("gates")
    if expected_gates != [f"G{index}" for index in range(12)] or len(rows) != 12:
        return False
    if [row[0] for row in rows] != expected_gates or any(len(row) != len(GATE_TABLE_COLUMNS) for row in rows):
        return False

    gate_status_index = GATE_TABLE_COLUMNS.index("Gate Status")
    evaluation_index = GATE_TABLE_COLUMNS.index("Evaluation State")
    if template:
        return all(
            row[gate_status_index] == GATE_STATUS_TOKEN
            and row[evaluation_index] == EVALUATION_STATE_TOKEN
            for row in rows
        )
    for row in rows:
        status = row[gate_status_index]
        evaluation = row[evaluation_index]
        if status not in GATE_STATUSES or evaluation not in EVALUATION_STATES:
            return False
        if status in {"PASS", "FAIL"} and evaluation != "DECIDED":
            return False
        if status == "BLOCKED" and evaluation == "IN_REVIEW":
            return False
        if evaluation == "DECIDED":
            if not all(_is_actual_value(row[GATE_TABLE_COLUMNS.index(field)]) for field in GATE_DECISION_REQUIRED_FIELDS):
                return False
            if not _is_actual_evidence(
                row[GATE_TABLE_COLUMNS.index("Evidence IDs")], root, excluded_paths, evidence_source_path
            ):
                return False
    return True


def _valid_active_rtm_rows(
    rows: list[list[str]], root: Path, excluded_paths: tuple[Path, ...]
) -> bool:
    if not all(_valid_active_rtm_row(row, root, excluded_paths) for row in rows):
        return False
    values = [dict(zip(RTM_TABLE_COLUMNS, row, strict=True)) for row in rows]
    return len({row["Trace ID"] for row in values}) == len(values) and len(
        {row["REQ/NFR"] for row in values}
    ) == len(values)


def _valid_active_rtm_row(row: list[str], root: Path, excluded_paths: tuple[Path, ...]) -> bool:
    if len(row) != len(RTM_TABLE_COLUMNS):
        return False
    values = dict(zip(RTM_TABLE_COLUMNS, row, strict=True))
    requirement_id = values["REQ/NFR"]
    if not re.fullmatch(r"TRACE-[A-Za-z0-9._-]+", values["Trace ID"]):
        return False
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
    if values["Defect Disposition"] and values["Defect Disposition"] not in DEFECT_DISPOSITIONS:
        return False
    if not _typed_links_are_valid(values, root):
        return False
    if values["Scope Status"] == "IN_SCOPE" and not _is_actual_value(values["Acceptance Criteria"]):
        return False
    if _is_actual_value(values["Commit/MR"]) and not all(
        _is_actual_value(values[field]) for field in ("DES/ADR", "TASK")
    ):
        return False
    result = values["Verification Result"]
    requires_release_evidence = result == "PASS" or _is_actual_value(values["REL"])
    requires_execution_evidence = result in {"PASS", "FAIL", "BLOCKED"} or _is_actual_value(values["REL"])
    if requires_execution_evidence:
        if values["Evidence Status"] != "VERIFIED":
            return False
        if not all(_is_actual_value(values[field]) for field in ("TC", "Test Execution/Evidence")):
            return False
        if not _has_resolved_evidence_ids(values["Test Execution/Evidence"], root, excluded_paths):
            return False
    if requires_release_evidence and not _is_actual_value(values["REL"]):
        return False
    if values["Defect Disposition"] == "CLOSED":
        if not _has_typed_references(values["BUG"], "BUG"):
            return False
        if not all(
            _is_actual_value(values[field])
            for field in ("Commit/MR", "TC", "Test Execution/Evidence", "Last Verified")
        ):
            return False
        if values["Verification Result"] != "PASS" or values["Evidence Status"] != "VERIFIED":
            return False
        if not _has_resolved_evidence_ids(values["Test Execution/Evidence"], root, excluded_paths):
            return False
    if _is_actual_value(values["CR"]):
        if values["Evidence Status"] != "VERIFIED" or not _has_resolved_evidence_ids(
            values["Test Execution/Evidence"], root, excluded_paths
        ):
            return False
        if not all(_is_actual_value(values[field]) for field in ("REQ/NFR", "DES/ADR", "TASK", "TC")):
            return False
    if values["Traceability Status"] == "COMPLETE" and not all(
        _is_actual_value(values[field]) for field in COMPLETE_TRACEABILITY_FIELDS
    ):
        return False
    return True


def _typed_links_are_valid(values: dict[str, str], root: Path) -> bool:
    for field, prefixes in {
        "BG": ("BG",),
        "PRD": ("PRD",),
        "DES/ADR": ("DES", "ADR"),
        "TASK": ("TASK",),
        "CR": ("CR",),
        "TC": ("TC",),
        "BUG": ("BUG",),
        "REL": ("REL",),
    }.items():
        if values[field].strip() and not _has_typed_references(values[field], *prefixes):
            return False
    if values["Commit/MR"].strip() and not _is_commit_or_mr_reference(
        values["Commit/MR"], root
    ):
        return False
    if values["Test Execution/Evidence"].strip() and not _has_typed_references(
        values["Test Execution/Evidence"], "EVD"
    ):
        return False
    return True


def _is_actual_evidence(
    value: str,
    root: Path | None,
    excluded_paths: tuple[Path, ...],
    source_path: Path | None,
) -> bool:
    if root is None or not _is_actual_value(value) or _contains_placeholder(value):
        return False
    references = [reference.strip() for reference in re.split(r"[;,]", value) if reference.strip()]
    return bool(references) and all(
        _is_valid_evidence_reference(reference, root, excluded_paths, source_path) for reference in references
    )


def _is_valid_evidence_reference(
    value: str, root: Path, excluded_paths: tuple[Path, ...], source_path: Path | None
) -> bool:
    if source_path is not None and _is_existing_markdown_link(value, source_path, root, excluded_paths):
        return True
    if re.fullmatch(r"[0-9a-fA-F]{7,40}", value):
        return _is_current_commit(root, value)
    if re.fullmatch(r"(?:BG|MR|PRD|REQ|NFR|DES|ADR|TASK|TC|BUG|CR|RISK|REL|EVD)-[A-Za-z0-9._-]+", value):
        return _artifact_is_declared_elsewhere(root, value, excluded_paths)
    return False


def _is_existing_markdown_link(
    value: str, source_path: Path, root: Path, excluded_paths: tuple[Path, ...]
) -> bool:
    match = re.fullmatch(
        r"\[[^\]\r\n]+\]\(\s*(?:<([^>\r\n]+)>|([^\s()<>]+))"
        r"(?:\s+(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|\([^()\r\n]*\)))?\s*\)",
        value,
    )
    if match is None:
        return False
    target = (match.group(1) or match.group(2)).split("#", maxsplit=1)[0]
    if not target or "://" in target:
        return False
    try:
        resolved_target = (source_path.parent / target).resolve(strict=True)
    except OSError:
        return False
    resolved_root = root.resolve()
    return (
        resolved_target.is_file()
        and resolved_target.is_relative_to(resolved_root)
        and resolved_target not in {path.resolve() for path in excluded_paths}
    )


def _is_current_commit(root: Path, commit_sha: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{commit_sha}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _artifact_is_declared_elsewhere(root: Path, artifact_id: str, excluded_paths: tuple[Path, ...]) -> bool:
    excluded = {path.resolve() for path in excluded_paths}
    for path in root.rglob("*.md"):
        if path.resolve() in excluded:
            continue
        contents = path.read_text(encoding="utf-8")
        if any(
            _metadata_value(contents, field) == artifact_id
            for field in ("Record ID", "Artifact ID", "Evidence ID")
        ):
            return True
    return False


def _has_typed_references(value: str, *prefixes: str) -> bool:
    tokens = _reference_tokens(value)
    pattern = re.compile(
        rf"(?:{'|'.join(re.escape(prefix) for prefix in prefixes)})-[A-Za-z0-9._-]+"
    )
    return tokens is not None and bool(tokens) and all(pattern.fullmatch(token) for token in tokens)


def _is_commit_or_mr_reference(value: str, root: Path) -> bool:
    tokens = _reference_tokens(value)
    return tokens is not None and bool(tokens) and all(
        _has_typed_references(token, "MR")
        or (re.fullmatch(r"[0-9a-fA-F]{7,40}", token) is not None and _is_current_commit(root, token))
        for token in tokens
    )


def _has_resolved_evidence_ids(value: str, root: Path, excluded_paths: tuple[Path, ...]) -> bool:
    tokens = _reference_tokens(value)
    return tokens is not None and bool(tokens) and all(
        re.fullmatch(r"EVD-[A-Za-z0-9._-]+", token) is not None
        and _artifact_is_declared_elsewhere(root, token, excluded_paths)
        for token in tokens
    )


def _reference_tokens(value: str) -> list[str] | None:
    if not _is_actual_value(value):
        return None
    tokens = [token.strip() for token in re.split(r"\s*(?:,|;|<br\s*/?>)\s*", value, flags=re.IGNORECASE)]
    return tokens if tokens and all(tokens) else None


def _is_actual_value(value: str) -> bool:
    normalized = value.strip()
    return bool(normalized) and not _contains_placeholder(normalized)


def _contains_placeholder(value: str) -> bool:
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered == "-":
        return True
    if re.search(r"\{\{[^{}\r\n]*\}\}", normalized) or re.search(
        r"\[待[^\]\r\n]*\]", normalized
    ):
        return True
    return any(
        re.match(rf"^{re.escape(placeholder)}(?=$|[^A-Za-z0-9_])", lowered)
        for placeholder in PLACEHOLDER_VALUES - {"-"}
    )


def _metadata_value(contents: str, field: str) -> str | None:
    pattern = re.compile(rf"^\s*-\s*{re.escape(field)}:\s*([^\s]+)\s*$", re.MULTILINE)
    match = pattern.search("\n".join(_unfenced_lines(contents)))
    return match.group(1) if match else None


def _read_markdown_tables(path: Path) -> list[tuple[list[str], list[list[str]]]] | None:
    if not path.is_file():
        return None
    lines = _unfenced_lines(path.read_text(encoding="utf-8"))
    tables = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.lstrip().startswith("|"):
            index += 1
            continue
        if index + 1 >= len(lines):
            return None
        header = _table_cells(line)
        separator = _table_cells(lines[index + 1])
        if not header or len(header) != len(separator) or not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separator
        ):
            return None
        rows = []
        index += 2
        while index < len(lines):
            row_line = lines[index]
            if not row_line.lstrip().startswith("|"):
                break
            row = _table_cells(row_line)
            if len(row) != len(header):
                return None
            rows.append(row)
            index += 1
        tables.append((header, rows))
    return tables


def _unfenced_lines(contents: str) -> list[str]:
    visible = []
    fence: tuple[str, int] | None = None
    for line in contents.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if match is not None and match.group(1).startswith("`") and "`" in match.group(2):
            match = None
        if fence is not None:
            if (
                match is not None
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= fence[1]
                and match.group(2).strip(" \t") == ""
            ):
                fence = None
            continue
        if match is not None:
            fence = (match.group(1)[0], len(match.group(1)))
            continue
        visible.append(line)
    return visible


def _rtm_path(manifest: dict) -> Path:
    return _manifest_path(manifest, "requirement_traceability_matrix") or Path(DEFAULT_RTM_PATH)


def _table_cells(line: str) -> list[str]:
    return [
        cell.strip().replace("\\|", "|")
        for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))
    ]
