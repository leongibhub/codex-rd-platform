"""Trusted-host execution adapters for TASK-V3-016 workers.

These adapters execute only host configuration.  They do not give a model a
Runtime database handle or elevate a model response to verified evidence.
"""
from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from .store import Store

from .runner import run_command
from .lifecycle_base import ARTIFACT_TYPES
from .proposal_backend import run_responses

_ENVELOPE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["status", "summary", "output_refs", "artifacts"],
    "properties": {
        "status": {"type": "string", "enum": ["DONE", "FAILED", "WAITING_USER", "BLOCKED"]},
        "summary": {"type": "string", "minLength": 1, "maxLength": 4000},
        "output_refs": {"type": "array", "maxItems": 0, "items": {"type": "object", "additionalProperties": False,
            "required": ["type", "id", "version"], "properties": {"type": {"type": "string", "enum": sorted(ARTIFACT_TYPES | {"TEST_CASE", "TEST_EXECUTION", "BUG", "REL", "EVIDENCE"})},
            "id": {"type": "string", "minLength": 1}, "version": {"type": "integer", "minimum": 1}}}},
        "artifacts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["id", "type", "title", "relative_path", "sha256"], "properties": {
                "id": {"type": "string", "minLength": 1}, "type": {"type": "string", "enum": sorted(ARTIFACT_TYPES - {"TEST_MODEL"})},
                "title": {"type": "string", "minLength": 1}, "relative_path": {"type": "string", "minLength": 1},
                "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}}},
    },
}


def _object(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + " must be an object")
    return value


def validate_backend(spec: dict, *, repository_root: Path, control_db: str | Path) -> dict:
    """Validate a trusted backend declaration before it can be dispatched."""
    spec = _object(spec, "backend")
    kind = spec.get("type")
    if kind == "argv":
        argv = spec.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v or "\0" in v for v in argv):
            raise ValueError("argv backend requires nonempty string argv")
        return {"type": kind, "argv": list(argv)}
    if kind == "responses":
        endpoint=spec.get("endpoint","https://api.openai.com/v1/responses"); parsed=urllib.parse.urlparse(endpoint)
        if not isinstance(spec.get("model"),str) or not spec["model"] or not isinstance(spec.get("api_key_env"),str) or not spec["api_key_env"] or parsed.scheme!="https" or parsed.username or parsed.password: raise ValueError("responses backend requires model, key env, trusted HTTPS endpoint")
        tokens=spec.get("max_output_tokens",2048)
        if type(tokens) is not int or not 1<=tokens<=16384: raise ValueError("responses max_output_tokens is invalid")
        return {"type":"responses","model":spec["model"],"api_key_env":spec["api_key_env"],"endpoint":endpoint,"max_output_tokens":tokens}
    if kind == "codex": raise ValueError("codex backend is not production-safe; use responses proposals")
    raise ValueError("backend type must be argv or responses")


def execute_backend(spec: dict, *, repository_root: Path, timeout_seconds: float,
                    max_output_bytes: int, cancel_event, context_bundle=None) -> dict:
    """Run an already validated backend and return capped host observation."""
    if spec["type"] == "argv":
        return run_command(spec["argv"], repository_root, timeout=timeout_seconds,
                           max_output_bytes=max_output_bytes, cancel_event=cancel_event)
    if spec["type"] == "responses":
        result=run_responses(spec, prompt=json.dumps(context_bundle or {}, ensure_ascii=False), timeout_seconds=timeout_seconds, max_output_bytes=max_output_bytes, cancel_event=cancel_event)
        result["envelope_text"]=result.get("stdout", "")
        return result
    raise ValueError("unsupported execution backend")


def parse_envelope(command: dict) -> dict:
    """Accept exactly one JSON response envelope; never infer success from exit 0."""
    if command.get("status") != "PASS" or command.get("cancelled"):
        raise ValueError("backend command did not complete successfully")
    raw = command.get("envelope_text", command.get("stdout", ""))
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("backend produced empty envelope")
    try:
        envelope = Store.loads(raw)
    except (ValueError, RecursionError) as error:
        raise ValueError("backend envelope is not JSON") from error
    _object(envelope, "backend envelope")
    if set(envelope) - (set(_ENVELOPE_SCHEMA["properties"]) | {"proposals"}):
        raise ValueError("backend envelope has unsupported fields")
    if envelope.get("status") not in {"DONE", "FAILED", "WAITING_USER", "BLOCKED"}:
        raise ValueError("backend envelope has invalid status")
    if not isinstance(envelope.get("summary"), str) or not envelope["summary"].strip() or len(envelope["summary"]) > 4000:
        raise ValueError("backend envelope has invalid summary")
    if "proposals" in envelope:
        if set(envelope) != {"status","summary","proposals"} or not isinstance(envelope["proposals"],list): raise ValueError("backend proposals are invalid")
        return envelope
    if not isinstance(envelope.get("output_refs"), list) or not isinstance(envelope.get("artifacts"), list):
        raise ValueError("backend envelope has invalid output lists")
    if envelope["output_refs"]:
        raise ValueError("worker backend must declare new artifacts, not output_refs")
    for ref in envelope["output_refs"]:
        if not isinstance(ref, dict) or set(ref) != {"type", "id", "version"} or not isinstance(ref["type"], str) or not ref["type"] or not isinstance(ref["id"], str) or not ref["id"] or type(ref["version"]) is not int or ref["version"] < 1:
            raise ValueError("backend envelope has invalid output artifact reference")
    return envelope
