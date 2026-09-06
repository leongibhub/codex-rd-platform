"""Trusted local manifest executor for the V3 multistack self-test matrix.

This module is intentionally CLI-only: it executes repository-controlled argv
arrays via :func:`rd_platform.runner.run_command`, never shell text or HTTP
input.  It is not a sandbox for untrusted source code.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

from .runner import run_command


_PHASES = ("build", "unit", "integration")
_TOOLS = ("python", "node", "java", "javac", "cxx")
_TOKENS = set(_TOOLS) | {"root", "app", "build"}
_TOKEN_RE = re.compile(r"\{([^{}]+)\}")
_OUTPUT_BUDGET = 65_536
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_SKIP_DIRECTORIES = {".git", ".rd-platform", "node_modules", "__pycache__", "build", ".aws", ".azure"}
_SECRET_FILE_RE = re.compile(
    r"(?:\.env(?:\..*)?|\.npmrc|\.pypirc|\.netrc|credentials.*\.json|.*secret.*\.json|"
    r"service[-_]?account.*\.json|.*private[_-]?key.*|.*\.(?:pem|key|p12|pfx)|"
    r"id_(?:rsa|dsa|ecdsa|ed25519))\Z", re.I,
)
_SENSITIVE_CONTENT_PATTERNS = (
    ("pem_private_key", re.compile(rb"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("aws_access_key", re.compile(rb"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(rb"(?:ghp|github_pat)_[A-Za-z0-9_]{16,}")),
    ("openai_key", re.compile(rb"sk-[A-Za-z0-9_-]{16,}")),
    ("npm_auth_token", re.compile(rb"_authToken\s*=\s*[^\s]+", re.I)),
    ("bearer_token", re.compile(rb"Authorization\s*:\s*Bearer\s+[^\s\"']+", re.I)),
)


def _tool_record(value: str | Path | None) -> dict:
    if value is None:
        return {"status": "NOT_AVAILABLE", "path": None}
    path = Path(value)
    if not path.is_file():
        return {"status": "NOT_AVAILABLE", "path": None}
    return {"status": "AVAILABLE", "path": str(path.resolve())}


def probe_tools(overrides: dict | None = None) -> dict:
    """Return observable local-tool availability, optionally overridden in tests."""
    if overrides is not None and (not isinstance(overrides, dict) or any(key not in _TOOLS for key in overrides)):
        raise ValueError("overrides must only contain known tool names")
    detected = {
        "python": sys.executable,
        "node": shutil.which("node"),
        "java": _java_tool("java"),
        "javac": _java_tool("javac"),
        # C++ is intentionally application-specific (for example WSL), not a
        # global host-tool promise.
        "cxx": shutil.which("c++") if os.name != "nt" else None,
    }
    if overrides:
        detected.update(overrides)
    return {name: _tool_record(detected[name]) for name in _TOOLS}


def _java_tool(name: str) -> str | Path | None:
    """Use explicit Java home/PATH before the observed Windows JDK fallback."""
    home = os.environ.get("JAVA_HOME")
    if home:
        candidate = Path(home) / "bin" / f"{name}.exe"
        if candidate.is_file():
            return candidate
    found = shutil.which(name)
    if found:
        return found
    return Path(rf"C:\Program Files\Java\jdk-1.8\bin\{name}.exe")


def _inside(candidate: Path, parent: Path, label: str) -> Path:
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(parent)
    except ValueError as error:
        raise ValueError(f"{label} escapes root") from error
    return resolved


def _link_or_junction(path: Path) -> bool:
    """Detect Windows reparse-point junctions as well as normal symlinks."""
    if path.is_symlink() or os.path.islink(path):
        return True
    attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT


def _safe_tree_root(candidate: Path, parent: Path, label: str, *, allow_missing_leaf=False) -> Path:
    """Resolve containment without traversing a reparse point/symlink."""
    _inside(candidate, parent, label)
    relative = candidate.absolute().relative_to(parent.absolute())
    current = parent
    for index, part in enumerate(relative.parts):
        current = current / part
        if not current.exists():
            if allow_missing_leaf and index == len(relative.parts) - 1:
                break
            continue
        if _link_or_junction(current):
            raise ValueError(f"{label} contains a symlink or junction")
    return candidate


def _strict_json(text: str):
    def reject_constant(value):
        raise ValueError(f"non-finite JSON value: {value}")
    value = json.loads(text, parse_constant=reject_constant)
    def validate_depth(item, level=0):
        if level > 64:
            raise ValueError("JSON nesting exceeds 64 levels")
        if isinstance(item, dict):
            for child in item.values():
                validate_depth(child, level + 1)
        elif isinstance(item, list):
            for child in item:
                validate_depth(child, level + 1)
    validate_depth(value)
    return value


def _context(manifest_path, root):
    manifest_file = Path(manifest_path).resolve(strict=True)
    if not manifest_file.is_file():
        raise ValueError("manifest_path must name a file")
    project_root = Path(root).resolve(strict=True) if root is not None else manifest_file.parent
    if not project_root.is_dir():
        raise ValueError("root must name a directory")
    _inside(manifest_file, project_root, "manifest")
    app = manifest_file.parent.resolve(strict=True)
    _inside(app, project_root, "app")
    try:
        manifest = _strict_json(manifest_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError("manifest must be valid JSON") from error
    if not isinstance(manifest, dict) or isinstance(manifest.get("schema_version"), bool) or manifest.get("schema_version") != 1:
        raise ValueError("manifest schema_version must be 1")
    if not isinstance(manifest.get("id"), str) or not _ID_RE.fullmatch(manifest["id"]):
        raise ValueError("manifest id must be a portable single path component")
    commands = manifest.get("commands")
    if not isinstance(commands, dict):
        raise ValueError("manifest commands must be an object")
    if set(commands) - set(_PHASES):
        raise ValueError("manifest commands may only contain build, unit, integration")
    for argv in commands.values():
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            raise ValueError("each command must be a nonempty argv list of strings")
        unknown = {name for item in argv for name in _TOKEN_RE.findall(item)} - _TOKENS
        if unknown:
            raise ValueError(f"unknown placeholder: {sorted(unknown)[0]}")
    output_budget = manifest.get("output_budget", _OUTPUT_BUDGET)
    if isinstance(output_budget, bool) or not isinstance(output_budget, int) or not 1 <= output_budget <= _OUTPUT_BUDGET:
        raise ValueError(f"output_budget must be between 1 and {_OUTPUT_BUDGET}")
    build_base = _safe_tree_root(project_root / ".rd-platform" / "build", project_root, "build base", allow_missing_leaf=True)
    build = _safe_tree_root(build_base / manifest["id"], build_base, "build", allow_missing_leaf=True)
    return manifest_file, project_root, app, build, manifest


def _compile(argv, values: dict[str, str]) -> tuple[list[str], set[str]]:
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        raise ValueError("each command must be a nonempty argv list of strings")
    required = set()
    compiled = []
    for item in argv:
        names = _TOKEN_RE.findall(item)
        unknown = set(names) - _TOKENS
        if unknown:
            raise ValueError(f"unknown placeholder: {sorted(unknown)[0]}")
        required.update(name for name in names if name in _TOOLS)
        rendered = _TOKEN_RE.sub(lambda match: values[match.group(1)], item)
        _validate_workspace_template(item, rendered, values)
        compiled.append(rendered)
    return compiled, required


def _validate_workspace_template(template: str, rendered: str, values: dict[str, str]) -> None:
    """Confine explicit workspace placeholders without claiming argv sandboxing."""
    for token in ("root", "app", "build"):
        marker = "{" + token + "}"
        if marker not in template:
            continue
        before, _marker, _after = template.partition(marker)
        if before and not before.endswith("="):
            raise ValueError("workspace placeholder must be a path argument or assignment value")
        path_text = rendered[len(before):]
        _inside(Path(path_text), Path(values["root"]), "workspace path")


def _source_manifest(app: Path, *, include_bytes=False) -> tuple[list[dict], str, list[dict], dict[str, bytes]]:
    files = []
    excluded = []
    snapshots = {}
    for base, directories, names in os.walk(app, topdown=True, followlinks=False):
        directory = Path(base)
        if _link_or_junction(directory):
            raise ValueError("source symlinks or junctions are not allowed")
        if any(_link_or_junction(directory / name) for name in directories):
            raise ValueError("source symlinks or junctions are not allowed")
        for name in directories:
            if name in _SKIP_DIRECTORIES:
                excluded.append({"path": (directory / name).relative_to(app).as_posix() + "/", "reason": "known_sensitive_configuration_directory"})
        directories[:] = sorted(name for name in directories if name not in _SKIP_DIRECTORIES)
        for name in sorted(names):
            path = directory / name
            if _link_or_junction(path):
                raise ValueError("source symlinks or junctions are not allowed")
            relative = path.relative_to(app).as_posix()
            if _SECRET_FILE_RE.fullmatch(name):
                excluded.append({"path": relative, "reason": "known_sensitive_configuration"})
                continue
            content = path.read_bytes()
            if reason := _sensitive_content_reason(content):
                raise ValueError(f"sensitive source content ({reason}) detected in {relative}; packaging refused")
            digest = hashlib.sha256(content).hexdigest()
            files.append({"path": relative, "sha256": digest})
            if include_bytes:
                snapshots[relative] = content
    files.sort(key=lambda item: item["path"])
    excluded.sort(key=lambda item: item["path"])
    aggregate = hashlib.sha256(json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return files, aggregate, excluded, snapshots


def _sensitive_content_reason(content: bytes) -> str | None:
    """Fail closed for a small, documented set of high-confidence signatures."""
    overlap = 128
    previous = b""
    for offset in range(0, len(content), 65_536):
        payload = previous + content[offset:offset + 65_536]
        for name, pattern in _SENSITIVE_CONTENT_PATTERNS:
            if pattern.search(payload):
                return name
        previous = payload[-overlap:]
    return None


def _verify_snapshot_unchanged(app: Path, files: list[dict]) -> None:
    """Reject a source drift before committing a delivery from its snapshot."""
    for item in files:
        path = app / item["path"]
        try:
            current = path.read_bytes()
        except OSError as error:
            raise ValueError("source changed after snapshot; packaging refused") from error
        if hashlib.sha256(current).hexdigest() != item["sha256"]:
            raise ValueError("source changed after snapshot; packaging refused")


def run_matrix(manifest_path, *, root=None, tools=None, phases=None) -> dict:
    """Execute selected manifest phases and retain actual bounded runner evidence."""
    manifest_file, project_root, app, build, manifest = _context(manifest_path, root)
    selected = _PHASES if phases is None else tuple(phases)
    if not selected or len(set(selected)) != len(selected) or any(phase not in _PHASES for phase in selected):
        raise ValueError("phases must be selected from build, unit, integration")
    tool_info = probe_tools(tools) if tools is None or any(not isinstance(value, dict) for value in tools.values()) else tools
    if set(tool_info) != set(_TOOLS):
        raise ValueError("tools must describe python, node, java, javac, cxx")
    for name, record in tool_info.items():
        if not isinstance(record, dict) or record.get("status") not in {"AVAILABLE", "NOT_AVAILABLE"}:
            raise ValueError(f"invalid tool record for {name}")
    values = {"root": str(project_root), "app": str(app), "build": str(build)}
    values.update({name: record.get("path") or "" for name, record in tool_info.items()})
    sources, source_sha256, excluded_sources, _snapshots = _source_manifest(app)
    evidence = {}
    for phase in selected:
        argv = manifest["commands"].get(phase)
        if argv is None:
            evidence[phase] = {"status": "NOT_EXECUTED", "reason": "command is absent"}
            continue
        compiled, required = _compile(argv, values)
        absent = sorted(name for name in required if tool_info[name]["status"] != "AVAILABLE")
        if absent:
            evidence[phase] = {"status": "NOT_AVAILABLE", "reason": "required tool unavailable", "tools": absent}
            continue
        build.mkdir(parents=True, exist_ok=True)
        evidence[phase] = run_command(compiled, cwd=app, max_output_bytes=manifest.get("output_budget", _OUTPUT_BUDGET))
        if evidence[phase]["status"] == "FAIL":
            break
    statuses = {item["status"] for item in evidence.values()}
    status = "FAIL" if "FAIL" in statuses else "NOT_AVAILABLE" if "NOT_AVAILABLE" in statuses else "NOT_EXECUTED" if "NOT_EXECUTED" in statuses else "PASS"
    return {
        "schema_version": "stack-harness-v1", "status": status,
        "manifest": str(manifest_file), "app": str(app), "build": str(build),
        "tools": tool_info, "phases": evidence, "source_sha256": source_sha256,
        "source_files": sources, "excluded_sources": excluded_sources,
    }


def package_app(manifest_path, *, root=None) -> dict:
    """Create a reproducible source archive and SHA-256 manifest below root."""
    manifest_file, project_root, app, _build, manifest = _context(manifest_path, root)
    files, source_sha256, excluded_sources, snapshots = _source_manifest(app, include_bytes=True)
    delivery_dir = _safe_tree_root(project_root / ".rd-platform" / "deliveries", project_root, "deliveries", allow_missing_leaf=True)
    delivery_dir.mkdir(parents=True, exist_ok=True)
    archive = _safe_tree_root(delivery_dir / f"{manifest['id']}-{source_sha256}.zip", delivery_dir, "archive", allow_missing_leaf=True)
    digest_file = _safe_tree_root(delivery_dir / f"{manifest['id']}-{source_sha256}.sha256.json", delivery_dir, "delivery manifest", allow_missing_leaf=True)
    temporary_archive = temporary_manifest = None
    try:
        _verify_snapshot_unchanged(app, files)
        with tempfile.NamedTemporaryFile(dir=delivery_dir, suffix=".zip", delete=False) as temporary:
            temporary_archive = Path(temporary.name)
        with zipfile.ZipFile(temporary_archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as package:
            for item in files:
                info = zipfile.ZipInfo(item["path"], date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                package.writestr(info, snapshots[item["path"]])
        archive_sha256 = hashlib.sha256(temporary_archive.read_bytes()).hexdigest()
        payload = {"schema_version": "stack-package-v1", "id": manifest["id"], "archive": archive.name,
                   "archive_sha256": archive_sha256, "source_sha256": source_sha256, "files": files,
                   "excluded_sources": excluded_sources}
        with tempfile.NamedTemporaryFile(dir=delivery_dir, suffix=".json", delete=False, mode="w", encoding="utf-8") as temporary:
            temporary.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            temporary_manifest = Path(temporary.name)
        if archive.exists():
            if hashlib.sha256(archive.read_bytes()).hexdigest() != archive_sha256:
                raise ValueError("refusing to overwrite existing delivery archive")
        else:
            temporary_archive.replace(archive)
        expected_manifest = temporary_manifest.read_bytes()
        if digest_file.exists():
            if digest_file.read_bytes() != expected_manifest:
                raise ValueError("refusing to overwrite existing delivery manifest")
        else:
            temporary_manifest.replace(digest_file)
    finally:
        for temporary in (temporary_archive, temporary_manifest):
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return {"status": "PASS", "archive": str(archive), "sha256_manifest": str(digest_file),
            "archive_sha256": archive_sha256, "source_sha256": source_sha256, "files": files,
            "excluded_sources": excluded_sources, "manifest": str(manifest_file)}
