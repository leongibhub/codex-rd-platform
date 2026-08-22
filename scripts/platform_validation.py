from dataclasses import dataclass
from pathlib import Path
import json
import tomllib


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


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
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("name:"):
                result.add(line.split(":", 1)[1].strip())
                break
    return result


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
