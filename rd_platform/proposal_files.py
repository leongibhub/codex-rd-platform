"""Host-side CAS proposal-file batches with durable recovery journals."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path, PureWindowsPath
from uuid import uuid4

_FIELDS = {"action", "id", "type", "title", "relative_path", "content", "expected_sha256"}
_CONTROL = {".rd-platform", ".git", ".codex"}


def _sha(raw): return hashlib.sha256(raw).hexdigest()


def _path(value, label):
    if not isinstance(value, str) or not value or "\0" in value: raise ValueError(label + " must be non-empty text")
    path = Path(value)
    if path.is_absolute() or PureWindowsPath(value).is_absolute() or PureWindowsPath(value).drive or ".." in path.parts:
        raise ValueError(label + " must be a confined relative path")
    if any(part.casefold() in _CONTROL for part in path.parts): raise ValueError("control metadata paths are not allowed")
    return path


def _key(path): return path.as_posix().casefold()


def _target(root, relative):
    target, current = root / relative, root
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(str(current)):
            raise ValueError("proposal path cannot traverse links or junctions")
    parent = target.parent
    existing = parent
    while not existing.exists(): existing = existing.parent
    resolved_existing = existing.resolve(strict=True)
    if not resolved_existing.is_relative_to(root): raise ValueError("proposal path escapes repository")
    if target.exists() and target.resolve(strict=True).parent != target.parent.resolve(strict=True): raise ValueError("proposal target link is not allowed")
    return target


def _save(path, record):
    raw = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2).encode() + b"\n"
    temporary = path.with_name("." + path.name + "." + uuid4().hex + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    return record


def _load(journal):
    path = Path(journal)
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise ValueError("proposal journal is unreadable") from error
    if not isinstance(data, dict) or data.get("state") not in {"PREPARED", "APPLIED", "COMMITTED", "ROLLED_BACK"} or not isinstance(data.get("changes"), list):
        raise ValueError("proposal journal is invalid")
    expected_root = path.resolve().parent.parent.parent
    if path.parent.name != "proposal-journal" or path.parent.parent.name != ".rd-platform" or Path(data.get("root", "")).resolve() != expected_root:
        raise ValueError("proposal journal root does not match its host directory")
    for change in data["changes"]:
        if not isinstance(change, dict): raise ValueError("invalid journal change")
        _path(change.get("path"), "journal path")
        if change.get("action") not in {"create", "update"}: raise ValueError("invalid journal action")
        for prefix in ("old", "new"):
            raw = change.get(prefix + "_b64")
            if raw is None and prefix == "old" and change.get("old_sha256") is None: continue
            try: decoded = base64.b64decode(raw, validate=True)
            except (ValueError, TypeError) as error: raise ValueError("invalid journal bytes") from error
            if _sha(decoded) != change.get(prefix + "_sha256"): raise ValueError("invalid journal digest")
    for directory in data.get("directories", []): _path(directory, "journal directory")
    return path, data


def _write_atomic(target, raw):
    temporary = target.with_name("." + target.name + ".proposal-" + uuid4().hex + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, target)


def prepare(root, proposals, allowlist, *, binding=None):
    """Validate an entire create/update batch before creating a journal or file."""
    root = Path(root).resolve(strict=True)
    if not isinstance(proposals, list) or not proposals: raise ValueError("proposals must be a nonempty list")
    if not isinstance(allowlist, (list, tuple, set)) or not allowlist: raise ValueError("source_paths allowlist is required")
    allowed = {_key(_path(item, "allowlist path")) for item in allowlist}
    if len(allowed) != len(allowlist): raise ValueError("duplicate allowlist path")
    changes, seen = [], set()
    for proposal in proposals:
        if not isinstance(proposal, dict) or set(proposal) != _FIELDS: raise ValueError("invalid proposal control metadata")
        action = proposal["action"]
        if action not in {"create", "update"}: raise ValueError("proposal action is invalid")
        if not all(isinstance(proposal[key], str) and proposal[key] for key in ("id", "type", "title", "content")): raise ValueError("proposal metadata is invalid")
        relative = _path(proposal["relative_path"], "proposal path"); key = _key(relative)
        if key not in allowed: raise ValueError("proposal path not allowed")
        if key in seen: raise ValueError("duplicate proposal path")
        seen.add(key); target = _target(root, relative); exists = target.exists()
        if exists and not target.is_file(): raise ValueError("proposal target must be a regular file")
        old, expected = (target.read_bytes() if exists else None), proposal["expected_sha256"]
        if action == "create" and (exists or expected is not None): raise ValueError("create must target a new path with null expected_sha256")
        if action == "update" and (not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or old is None or expected != _sha(old)):
            raise ValueError("CAS mismatch")
        raw = proposal["content"].encode("utf-8")
        if len(raw) > 1_048_576: raise ValueError("proposal byte budget exceeded")
        changes.append({"path": relative.as_posix(), "action": action, "id": proposal["id"], "type": proposal["type"], "title": proposal["title"],
                        "old_b64": base64.b64encode(old).decode() if old is not None else None, "old_sha256": _sha(old) if old is not None else None,
                        "new_b64": base64.b64encode(raw).decode(), "new_sha256": _sha(raw), "applied": False})
    directory = root / ".rd-platform" / "proposal-journal"
    for value in (root / ".rd-platform", directory):
        if value.exists() and (value.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(str(value))):
            raise ValueError("proposal journal control directory cannot traverse links or junctions")
    directory.mkdir(parents=True, exist_ok=True)
    directories = set()
    for change in changes:
        parent = Path(change["path"]).parent
        while str(parent) not in {"", "."}:
            if not (root / parent).exists(): directories.add(parent.as_posix())
            parent = parent.parent
    directories = sorted(directories)
    journal = directory / (uuid4().hex + ".json")
    _save(journal, {"schema_version": 1, "root": str(root), "state": "PREPARED", "changes": changes, "directories": directories, "artifact_refs": None, "binding": binding})
    return journal, changes


def apply(journal):
    path, data = _load(journal)
    if data["state"] != "PREPARED": raise ValueError("prepared journal required")
    root = Path(data["root"]).resolve(strict=True)
    for change in data["changes"]:
        target = _target(root, _path(change["path"], "journal path")); current = target.read_bytes() if target.exists() else None
        if (_sha(current) if current is not None else None) != change["old_sha256"]: raise ValueError("CAS mismatch before apply")
    for change in data["changes"]:
        target = _target(root, _path(change["path"], "journal path")); target.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(target, base64.b64decode(change["new_b64"], validate=True))
        change["applied"] = True; _save(path, data)
    data["state"] = "APPLIED"
    return _save(path, data)


def commit(journal, artifact_refs):
    path, data = _load(journal)
    if data["state"] != "APPLIED": raise ValueError("applied journal required")
    if not isinstance(artifact_refs, list) or len(artifact_refs) != len(data["changes"]): raise ValueError("exact artifact refs required")
    _exact_refs(data, artifact_refs)
    data["artifact_refs"], data["state"] = artifact_refs, "COMMITTED"
    return _save(path, data)


def _exact_refs(data, artifact_refs):
    if not isinstance(artifact_refs, list) or len(artifact_refs) != len(data["changes"]): raise ValueError("exact artifact refs required")
    expected = {(item["type"], item["id"]) for item in data["changes"]}
    actual = {(item.get("type"), item.get("id")) for item in artifact_refs if isinstance(item, dict) and type(item.get("version")) is int and item["version"] > 0}
    if actual != expected or len(actual) != len(artifact_refs): raise ValueError("artifact refs do not exactly match proposal batch")


def rollback(journal):
    path, data = _load(journal)
    if data["state"] in {"COMMITTED", "ROLLED_BACK"}: return data
    root = Path(data["root"]).resolve(strict=True)
    restore = []
    for change in data["changes"]:
        target = _target(root, _path(change["path"], "journal path"))
        current = target.read_bytes() if target.is_file() else None
        current_hash = _sha(current) if current is not None else None
        if current_hash == change["old_sha256"]: continue
        if current_hash != change["new_sha256"]: raise ValueError("external drift; recovery blocked")
        restore.append(change)
    for change in reversed(restore):
        target = _target(root, _path(change["path"], "journal path"))
        if change["old_b64"] is None: target.unlink()
        else: _write_atomic(target, base64.b64decode(change["old_b64"], validate=True))
    data["state"] = "ROLLED_BACK"
    for directory in sorted(data.get("directories", []), key=lambda item: len(Path(item).parts), reverse=True):
        try: (root / directory).rmdir()
        except OSError: pass
    return _save(path, data)


def recover(journal, committed):
    """Keep files only when caller proves their exact SQLite artifact refs."""
    if not callable(committed): raise ValueError("committed proof callable is required")
    path, data = _load(journal)
    if data["state"] in {"COMMITTED", "ROLLED_BACK"}: return data
    proof = committed(data)
    if proof:
        refs = data.get("artifact_refs") if proof is True else proof
        _exact_refs(data, refs)
        root = Path(data["root"]).resolve(strict=True)
        for change in data["changes"]:
            target = _target(root, _path(change["path"], "journal path"))
            if not target.is_file() or _sha(target.read_bytes()) != change["new_sha256"]:
                raise ValueError("committed file drift; recovery requires reconciliation")
        data["artifact_refs"] = refs
        data["state"] = "COMMITTED"; return _save(path, data)
    return rollback(path)
