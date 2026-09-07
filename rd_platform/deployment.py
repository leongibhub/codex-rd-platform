"""Trusted, bounded deployment adapter for TASK-V3-018.

This module executes only operator-supplied, explicit local argv from a pinned
project directory.  It deliberately keeps trial operations outside release
truth; formal release registration remains the Runtime's policy decision.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
from uuid import uuid4

from ._workspace_directory import confined_directory
from .lifecycle import LifecycleService
from .runner import run_command


_SENSITIVE = re.compile(r"token|password|cookie|authorization|private[_-]?key|secret", re.I)
_TERMINAL = frozenset({"COMPLETED"})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise ValueError(f"{name} must be non-empty text")
    return value


def _safe_json(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("configuration keys must be strings")
            if _SENSITIVE.search(key):
                raise ValueError("secrets are not permitted in deployment configuration")
            _safe_json(item)
    elif isinstance(value, list):
        for item in value:
            _safe_json(item)
    elif isinstance(value, str) and re.search(r"\b(?:Bearer|Basic)\s+\S+|(?:token|password|cookie|authorization|private[_-]?key|secret)\s*=\s*(?!\[REDACTED(?:_SECRET)?\])\S+", value, re.I):
        raise ValueError("secrets are not permitted in deployment configuration")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError("configuration must be JSON values")


def _command(config, name, *, require_idempotent=False):
    value = config.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"{name} command configuration is required")
    argv = value.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item and "\0" not in item for item in argv):
        raise ValueError(f"{name}.argv must be a nonempty string list")
    timeout = value.get("timeout_seconds")
    limit = value.get("output_limit_bytes")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 86400:
        raise ValueError(f"{name}.timeout_seconds must be bounded")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10_000_000:
        raise ValueError(f"{name}.output_limit_bytes must be bounded")
    if require_idempotent and not isinstance(value.get("idempotent", False), bool):
        raise ValueError("deploy.idempotent must be boolean")
    return {"argv": argv, "timeout": timeout, "limit": limit, "idempotent": value.get("idempotent", False)}


def _relative(root, value, name):
    raw = Path(_text(value, name))
    if not raw.is_absolute() or PureWindowsPath(str(raw)).drive and not raw.drive:
        raise ValueError(f"{name} must be an absolute local path")
    resolved = raw.resolve(strict=True)
    try:
        return resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{name} must stay beneath project repository") from error


def _canonical_lexical(path):
    """Normalize Windows 8.3 spelling without resolving a link/reparse point."""
    candidate = Path(os.path.abspath(path))
    if os.name != "nt":
        return candidate
    import ctypes
    size = 32768
    buffer = ctypes.create_unicode_buffer(size)
    written = ctypes.windll.kernel32.GetLongPathNameW(str(candidate), buffer, size)
    if written and written < size:
        return Path(buffer.value)
    return candidate


def _no_link_escape(cwd, path, *, field):
    """Reject every link/reparse component instead of following it to hash or run."""
    cwd = _canonical_lexical(cwd)
    path = _canonical_lexical(path)
    try:
        relative = path.relative_to(cwd)
    except ValueError as error:
        raise ValueError(f"{field} must stay beneath cwd") from error
    current = cwd
    isjunction = getattr(os.path, "isjunction", lambda value: False)
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or isjunction(str(current)):
            raise ValueError(f"{field} cannot traverse symbolic links or junctions")
    resolved = _canonical_lexical(Path(path).resolve(strict=True))
    try:
        resolved.relative_to(cwd)
    except ValueError as error:
        raise ValueError(f"{field} must stay beneath cwd") from error
    return relative.as_posix()


def _source_hashes(root, cwd, hashes):
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("source_hashes must be a nonempty object")
    for relative, expected in hashes.items():
        if not isinstance(relative, str) or not relative or "\0" in relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("source hash path must be confined to cwd")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("source hash must be sha256")
        path = cwd / relative
        _no_link_escape(cwd, path, field="source hash path")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("source hash drift prevents command launch")


def _command_sources(root, cwd, hashes, commands):
    """A project-local script in argv must itself be pinned, not merely its cwd."""
    declared = set(hashes)
    for command in commands:
        for arg in command["argv"]:
            candidate = Path(arg)
            candidate = candidate if candidate.is_absolute() else cwd / candidate
            lexical_candidate = _canonical_lexical(candidate)
            lexical_root = _canonical_lexical(root)
            lexical_cwd = _canonical_lexical(cwd)
            try:
                relative = lexical_candidate.relative_to(lexical_cwd).as_posix()
            except ValueError:
                relative = None
            if not candidate.exists():
                continue
            if relative is None:
                if lexical_candidate.is_relative_to(lexical_root):
                    raise ValueError("project command source must stay beneath cwd")
                continue  # trusted host tool outside this project (for example Python).
            relative = _no_link_escape(cwd, lexical_candidate, field="project command source")
            if not candidate.is_file():
                raise ValueError("project command argv source must be a regular file")
            if relative not in declared:
                raise ValueError("project command source must have a declared source hash")


def _fingerprint(config, action):
    # Never include credential material: validation already rejects named secrets.
    return hashlib.sha256(json.dumps({"config": config, "action": action}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _append(receipt_dir, entry):
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = receipt_dir / "operations.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _entries(receipt_dir, operation_id):
    path = receipt_dir / "operations.jsonl"
    if not path.is_file():
        return []
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("operation receipt is corrupt; reconcile manually") from error
        if value.get("operation_id") == operation_id:
            result.append(value)
    return result


@contextmanager
def _operation_lock(receipt_dir):
    path = receipt_dir / ".deployment.lock"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError("deployment operation lock exists; reconcile before retry") from error
    try:
        os.write(fd, str(os.getpid()).encode())
        os.fsync(fd)
        yield
    finally:
        os.close(fd)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _write_receipt(root, receipt_dir, operation_id, suffix, value):
    path = receipt_dir / f"operation-{operation_id}-{suffix}.json"
    if path.exists():
        raise ValueError("operation receipt already exists; reconcile before retry")
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        relative = path.resolve(strict=True).relative_to(root).as_posix()
    except ValueError:
        relative = None
    return path, relative, hashlib.sha256(payload).hexdigest()


def _run(command, guard, root, hashes):
    # Revalidate immediately before every launch; a completed prior command
    # cannot authorize a modified script for the next deployment step.
    _source_hashes(root, guard.path, hashes)
    _command_sources(root, guard.path, hashes, (command,))
    return run_command(command["argv"], guard.path, timeout=command["timeout"], max_output_bytes=command["limit"], cwd_guard=guard)


def _formal_common(config):
    release_id = _text(config.get("release_id"), "release_id")
    _text(config.get("operator"), "operator")
    executor = _text(config.get("executor_id"), "executor_id")
    if not isinstance(config.get("evidence_artifact_refs"), list) or not config["evidence_artifact_refs"]:
        raise ValueError("formal deployment requires evidence_artifact_refs")
    return release_id, executor


def _formal_deploy_preflight(runtime, config):
    release_id, executor = _formal_common(config)
    snapshot = runtime.lifecycle_snapshot(config["project_id"])
    release = next((row for row in snapshot["releases"] if row["id"] == release_id), None)
    if release is None:
        raise KeyError("release not found: " + release_id)
    if release["status"] != "READY":
        raise ValueError("formal deployment requires READY release")
    if not any(row["gate_id"] == "G10" and row["gate_status"] == "PASS" for row in snapshot["gates"]):
        raise ValueError("formal deployment requires current G10 PASS")
    return release_id, executor


def _register_formal_deployment(runtime, config, result, receipt_ref):
    """Register facts after physical action; failures remain in the operation receipt."""
    release_id, executor = _formal_deploy_preflight(runtime, config)
    if not receipt_ref or not receipt_ref[0]:
        raise ValueError("formal receipt must be stored under project repository")
    with runtime.store.transaction() as connection:
        service = LifecycleService()
        evidence = service.execute(connection, "evidence.register", {
            "project_id": config["project_id"], "evidence_id": "EVD-DEPLOY-" + uuid4().hex, "kind": "deployment", "status": "VERIFIED",
            "source": {"kind": "host", "actor": executor}, "locator": {"path": receipt_ref[0], "sha256": receipt_ref[1]}, "observed_at": _now(),
            "metadata": {"subject_id": release_id, "result": "PASS" if result["status"] == "PASS" else "FAIL", "artifact_refs": config["evidence_artifact_refs"]},
        })
        release = service.execute(connection, "release.record_deployment", {
            "release_id": release_id, "result": "PASS" if result["status"] == "PASS" else "FAIL", "operator": config["operator"],
            "environment_ref": config["environment_ref"], "evidence_refs": [{"type": "EVIDENCE", "id": evidence["id"], "version": evidence["version"]}],
        })
        mutation = {"deployment": release}
        if result["status"] != "PASS":
            rollback_evidence = service.execute(connection, "evidence.register", {
                "project_id": config["project_id"], "evidence_id": "EVD-ROLLBACK-" + uuid4().hex, "kind": "rollback", "status": "VERIFIED",
                "source": {"kind": "host", "actor": executor}, "locator": {"path": receipt_ref[0], "sha256": receipt_ref[1]}, "observed_at": _now(),
                "metadata": {"subject_id": release_id, "result": "PASS" if result.get("compensated") else "FAIL", "artifact_refs": config["evidence_artifact_refs"]},
            })
            mutation["rollback"] = service.execute(connection, "release.rollback", {
                "release_id": release_id, "result": "PASS" if result.get("compensated") else "FAIL", "operator": config["operator"],
                "reason": "deployment or health command failed; declared compensation executed",
                "evidence_refs": [{"type": "EVIDENCE", "id": rollback_evidence["id"], "version": rollback_evidence["version"]}],
            })
        return mutation


def _register_formal_rollback(runtime, config, result, receipt_ref):
    """Register an explicit external rollback without creating a deployment fact."""
    release_id, executor = _formal_common(config)
    if not receipt_ref or not receipt_ref[0]:
        raise ValueError("formal receipt must be stored under project repository")
    with runtime.store.transaction() as connection:
        service = LifecycleService()
        rollback_evidence = service.execute(connection, "evidence.register", {
            "project_id": config["project_id"], "evidence_id": "EVD-ROLLBACK-" + uuid4().hex,
            "kind": "rollback", "status": "VERIFIED", "source": {"kind": "host", "actor": executor},
            "locator": {"path": receipt_ref[0], "sha256": receipt_ref[1]}, "observed_at": _now(),
            "metadata": {"subject_id": release_id, "result": "PASS" if result["status"] == "PASS" else "FAIL", "artifact_refs": config["evidence_artifact_refs"]},
        })
        return {"rollback": service.execute(connection, "release.rollback", {
            "release_id": release_id, "result": "PASS" if result["status"] == "PASS" else "FAIL",
            "operator": config["operator"], "reason": "explicit declared rollback executed",
            "evidence_refs": [{"type": "EVIDENCE", "id": rollback_evidence["id"], "version": rollback_evidence["version"]}],
        })}


def execute_deployment(runtime, config, *, action="deploy") -> dict:
    """Execute a declared deployment or compensation action and retain real facts.

    The caller supplies a trusted local configuration.  No command is inferred
    from a release, environment name, HTTP request, or unpinned source tree.
    """
    if action not in {"deploy", "rollback"}:
        raise ValueError("action must be deploy or rollback")
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    _safe_json(config)
    project_id = _text(config.get("project_id"), "project_id")
    mode = config.get("mode", "trial")
    if mode not in {"trial", "formal"}:
        raise ValueError("mode must be trial or formal")
    operation_id = _text(config.get("operation_id"), "operation_id")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", operation_id):
        raise ValueError("operation_id must be a safe identifier")
    environment = _text(config.get("environment"), "environment")
    snapshot = runtime.lifecycle_snapshot(project_id)
    root = Path(snapshot["lifecycle"]["repository_root"]).resolve(strict=True)
    cwd = Path(_text(config.get("cwd"), "cwd")).resolve(strict=True)
    relative_cwd = _relative(root, str(cwd), "cwd")
    _source_hashes(root, cwd, config.get("source_hashes"))
    deploy = _command(config, "deploy", require_idempotent=True)
    health = _command(config, "health")
    rollback = _command(config, "rollback")
    rollback_health = _command(config, "rollback_health")
    _command_sources(root, cwd, config["source_hashes"], (deploy, health, rollback, rollback_health))
    if mode == "formal":
        if action == "deploy": _formal_deploy_preflight(runtime, config)
        else: _formal_common(config)
    receipt_dir = Path(_text(config.get("receipt_dir"), "receipt_dir")).resolve()
    if not receipt_dir.is_absolute() or receipt_dir == root.parent:
        raise ValueError("receipt_dir must be a specific local directory")
    if mode == "formal":
        try:
            receipt_dir.relative_to(root)
        except ValueError as error:
            raise ValueError("formal receipt_dir must stay beneath project repository") from error
    receipt_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = _fingerprint(config, action)
    prior = _entries(receipt_dir, operation_id)
    if prior:
        if prior[0].get("fingerprint") != fingerprint:
            raise ValueError("operation_id fingerprint conflicts with existing receipt")
        if prior[-1].get("state") in _TERMINAL:
            return prior[-1]["result"]
        raise ValueError("operation outcome unknown; reconcile before retry")
    with _operation_lock(receipt_dir):
        # Re-read under the lock so concurrent callers cannot both launch.
        repeated = _entries(receipt_dir, operation_id)
        if repeated:
            if repeated[0].get("fingerprint") != fingerprint:
                raise ValueError("operation_id fingerprint conflicts with existing receipt")
            raise ValueError("operation outcome unknown; reconcile before retry")
        start = {"operation_id": operation_id, "project_id": project_id, "environment": environment, "mode": mode,
                 "action": action, "state": "STARTED", "fingerprint": fingerprint, "recorded_at": _now()}
        _append(receipt_dir, start)
        _, receipt_path, receipt_hash = _write_receipt(root, receipt_dir, operation_id, "started", start)
        with confined_directory(root, relative_cwd) as guard:
            if action == "rollback":
                rollback_result = _run(rollback, guard, root, config["source_hashes"])
                rollback_health_result = _run(rollback_health, guard, root, config["source_hashes"]) if rollback_result["status"] == "PASS" else None
                status = "PASS" if rollback_result["status"] == "PASS" and rollback_health_result and rollback_health_result["status"] == "PASS" else "FAIL"
                result = {"operation_id": operation_id, "mode": mode, "action": action, "status": status,
                          "rollback": rollback_result, "rollback_health": rollback_health_result}
            else:
                deploy_result = _run(deploy, guard, root, config["source_hashes"])
                health_result = _run(health, guard, root, config["source_hashes"]) if deploy_result["status"] == "PASS" else None
                if deploy_result["status"] == "PASS" and health_result and health_result["status"] == "PASS":
                    result = {"operation_id": operation_id, "mode": mode, "action": action, "status": "PASS", "deploy": deploy_result, "health": health_result}
                else:
                    rollback_result = _run(rollback, guard, root, config["source_hashes"])
                    rollback_health_result = _run(rollback_health, guard, root, config["source_hashes"]) if rollback_result["status"] == "PASS" else None
                    compensated = rollback_result["status"] == "PASS" and rollback_health_result and rollback_health_result["status"] == "PASS"
                    result = {"operation_id": operation_id, "mode": mode, "action": action,
                              "status": "FAIL", "deploy": deploy_result, "health": health_result,
                              "rollback": rollback_result, "rollback_health": rollback_health_result,
                              "compensated": bool(compensated)}
        # Durable actual result precedes formal Runtime mutation, which can fail on Gate drift.
        terminal = dict(start, state="COMPLETED", result=result, recorded_at=_now())
        _, terminal_path, terminal_hash = _write_receipt(root, receipt_dir, operation_id, "completed", terminal)
        if mode == "formal":
            try:
                result["formal_release"] = (_register_formal_deployment(runtime, config, result, (terminal_path, terminal_hash))
                                            if action == "deploy" else _register_formal_rollback(runtime, config, result, (terminal_path, terminal_hash)))
            except (KeyError, ValueError) as error:
                result["formal_registration_error"] = str(error)
                result["actual_status"] = result["status"]
                result["status"] = "FAIL"
        if mode == "trial":
            if action == "rollback": result["status"] = "TRIAL_ROLLED_BACK" if result["status"] == "PASS" else "TRIAL_ROLLBACK_FAILED"
            elif result["status"] == "PASS": result["status"] = "TRIAL_SUCCEEDED"
            else: result["status"] = "TRIAL_ROLLED_BACK" if result["compensated"] else "TRIAL_ROLLBACK_FAILED"
        terminal["result"] = result
        _append(receipt_dir, terminal)
        return result
