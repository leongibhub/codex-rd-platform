"""Durable, bounded dispatcher for lifecycle work leases (TASK-V3-016)."""
from __future__ import annotations

import hashlib
import json
import math
import os
from .store import Store
from pathlib import Path
import threading
import time

from .lifecycle_base import ARTIFACT_TYPES, LifecycleBase
from .lifecycle import LifecycleService
from .worker_backends import execute_backend, parse_envelope, validate_backend
from .proposal_files import prepare as prepare_proposals, apply as apply_proposals, rollback as rollback_proposals, commit as commit_proposals, recover as recover_proposals, _path as proposal_path, _target as proposal_target


def _number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(label + " is outside its finite budget")
    return value


def _validate(runtime, config):
    if not isinstance(config, dict): raise ValueError("worker config must be an object")
    project_id = config.get("project_id")
    root = Path(config.get("repository_root", "")).resolve()
    if not isinstance(project_id, str) or not project_id or not root.is_dir():
        raise ValueError("project_id and existing repository_root are required")
    snapshot = runtime.lifecycle_snapshot(project_id)
    if Path(snapshot["lifecycle"]["repository_root"]).resolve() != root:
        raise ValueError("worker repository_root must match lifecycle repository_root")
    workers = config.get("workers")
    if not isinstance(workers, list) or not workers: raise ValueError("workers are required")
    maximum = config.get("max_concurrency", len(workers))
    if type(maximum) is not int or not 1 <= maximum <= len(workers): raise ValueError("max_concurrency is invalid")
    checked = []
    seen = set()
    agents = {a["id"]: a for a in runtime.snapshot()["agents"]}
    for worker in workers:
        if not isinstance(worker, dict): raise ValueError("worker must be an object")
        agent_id, role = worker.get("agent_id"), worker.get("role")
        if not isinstance(agent_id, str) or not agent_id or agent_id in seen: raise ValueError("worker agent_id is invalid or duplicate")
        seen.add(agent_id)
        if agents.get(agent_id, {}).get("role") != role: raise ValueError("worker role does not match registered agent")
        if role not in {"developer", "tester", "reviewer", "requirement_analyst", "product_manager", "architect", "researcher", "release_manager", "documentation_manager"}:
            raise ValueError("worker role is invalid")
        lease = _number(worker.get("lease_seconds", 300), "lease_seconds", 1, 3600)
        timeout = _number(worker.get("timeout_seconds", 300), "timeout_seconds", 1, 3600)
        cap = worker.get("max_output_bytes", 65536)
        if type(cap) is not int or not 1 <= cap <= 1_000_000: raise ValueError("max_output_bytes is invalid")
        paths=worker.get("source_paths", [])
        if not isinstance(paths,list) or any(not isinstance(p,str) or not p or Path(p).is_absolute() or ".." in Path(p).parts or not (root/Path(p)).resolve().is_relative_to(root) for p in paths): raise ValueError("source_paths must be confined relative paths")
        for source in paths:
            proposal_path(source, "source path")
            if (root/source).resolve() == Path(runtime.db_path).resolve(): raise ValueError("control database is not a source")
        if "safe_to_retry" in worker and type(worker["safe_to_retry"]) is not bool:
            raise ValueError("safe_to_retry must be boolean")
        checked.append({"agent_id": agent_id, "role": role, "lease_seconds": int(lease), "timeout_seconds": timeout,
                        "max_output_bytes": cap, "backend": validate_backend(worker.get("backend"), repository_root=root, control_db=runtime.db_path),
                        "safe_to_retry": worker.get("safe_to_retry") is True,
                        "source_paths": paths})
    poll = _number(config.get("poll_interval_seconds", .2), "poll_interval_seconds", .05, 60)
    return {"project_id": project_id, "root": root, "workers": checked, "max_concurrency": maximum, "poll": poll}


def _unsafe_attempt_fences(snapshot):
    """Return work IDs whose latest invalidated attempt has unknown effects.

    A lifecycle pause or reap deliberately says that it did *not* cancel the
    external process.  Another service therefore cannot infer that replaying
    the READY work is safe.  The fence remains until a later claim begins a
    new attempt (which this dispatcher only permits with ``safe_to_retry``),
    so an older expiry cannot poison an ordinary retry after that safe attempt
    has itself finished.
    """
    fenced = set()
    for event in snapshot.get("events", []):
        work_id = event.get("entity_id")
        if event.get("type") in {"work.lease_expired", "work.invalidated"}:
            if event.get("data", {}).get("external_process_cancelled") is not True:
                fenced.add(work_id)
        elif event.get("type") == "work.claimed":
            # A later claim is a different attempt.  It could only have been
            # issued after an explicit safe-retry decision by this service.
            fenced.discard(work_id)
    return fenced


def _all_collection(runtime, project_id, collection):
    cursor = None; items = []
    while True:
        page = runtime.lifecycle_collection(project_id, collection, limit=500, after_cursor=cursor)
        items.extend(page["items"])
        if not page["has_more"]: return items
        cursor = page["next_cursor"]


def _all_events(runtime, project_id):
    after = 0; events = []
    while True:
        page = runtime.lifecycle_snapshot(project_id, after_sequence=after, limit=500)
        events.extend(page["events"])
        if not page["has_more"]: return events
        after = page["next_sequence"]


def _bound_refs(work, all_work):
    refs = list(work.get("input_refs", []))
    adopted = work.get("dependency_input_refs", [])
    if adopted:
        return refs + list(adopted)
    for dependency in work.get("dependencies", []):
        refs.extend(all_work.get(dependency, {}).get("output_refs", []))
    return refs


def _validate_bound_refs(runtime, project_id, work, all_work, *, preclaim=False):
    """Reject version *or content* drift for direct and dependency inputs."""
    refs = list(work.get("input_refs", [])) if preclaim and work.get("strict_policy") else _bound_refs(work, all_work)
    with runtime.store.transaction(write=False) as connection:
        LifecycleService().refs(connection, project_id, refs, nonempty=False)


def _register_artifacts(svc, connection, project_id, root, agent_id, artifacts):
    refs = []
    if not isinstance(artifacts, list): raise ValueError("artifacts must be an array")
    seen = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"id", "type", "title", "relative_path", "sha256"}:
            raise ValueError("output artifact declaration is invalid")
        ident, kind, title = item["id"], item["type"], item["title"]
        relative, digest = item["relative_path"], item["sha256"]
        if not all(isinstance(v, str) and v for v in (ident, kind, title, relative, digest)) or ident in seen:
            raise ValueError("output artifact fields are invalid")
        seen.add(ident)
        prefix = {"CODE_CHANGE": "CODE"}.get(kind, kind)
        if kind not in ARTIFACT_TYPES - {"TEST_MODEL"} or not ident.startswith(prefix + "-"):
            raise ValueError("output artifact type or id is invalid")
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("output artifact path is not workspace-relative")
        full = (root / path).resolve()
        if not full.is_relative_to(root) or not full.is_file() or hashlib.sha256(full.read_bytes()).hexdigest() != digest:
            raise ValueError("output artifact path or hash is invalid")
        artifact = svc.execute(connection, "artifact.create", {"project_id": project_id, "artifact_type": kind, "artifact_id": ident,
            "title": title, "state": "DRAFT", "content_ref": {"path": path.as_posix(), "sha256": digest},
            "source": {"kind": "host", "actor": agent_id}})
        refs.append({"type": artifact["artifact_type"], "id": artifact["id"], "version": artifact["version"]})
    return refs


def _recover_proposals(runtime, cfg):
    # Same DB write lock as admission: never recover another active transaction.
    with runtime.store.transaction() as connection:
        svc = LifecycleService()
        directory = cfg["root"] / ".rd-platform" / "proposal-journal"
        for component in (directory.parent, directory):
            if component.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(str(component)):
                raise ValueError("proposal journal cannot traverse links")
        if not directory.exists(): return
        artifacts = {a["id"]: a for a in svc.rows(connection, "artifacts", cfg["project_id"])}
        works = svc.rows(connection, "work_orders", cfg["project_id"])
        def proof(record):
            refs = []
            for change in record["changes"]:
                artifact = artifacts.get(change["id"], {})
                content = artifact.get("content_ref", {})
                if content != {"path": change["path"], "sha256": change["new_sha256"]}:
                    return False
                refs.append({"type": artifact["artifact_type"], "id": artifact["id"], "version": artifact["version"]})
            binding = record["binding"]
            return refs if any(w["id"] == binding["work_id"] and w["attempt"] == binding["attempt"] and w["status"] == "DONE" and all(r in w["output_refs"] for r in refs) for w in works) else False
        for journal in directory.glob("*.json"):
            if journal.is_symlink(): raise ValueError("linked proposal journal")
            record = Store.loads(journal.read_text(encoding="utf-8"))
            binding = record.get("binding")
            if not isinstance(binding, dict): raise ValueError("unbound proposal journal requires host reconciliation")
            if binding.get("project_id") != cfg["project_id"] or binding.get("db") != str(Path(runtime.db_path).resolve()):
                continue
            recover_proposals(journal, proof)


def _context_bundle(runtime, cfg, work):
    """Read only registered, version-bound inputs; never disclose control-plane paths."""
    snapshot = runtime.lifecycle_snapshot(cfg["project_id"], limit=1)
    by_work = {item["id"]: item for item in _all_collection(runtime, cfg["project_id"], "work_orders")}
    refs = _bound_refs(work, by_work)
    _validate_bound_refs(runtime, cfg["project_id"], work, by_work)
    records = {item["id"]: item for collection in ("artifacts", "evidence", "test_cases", "test_models", "test_executions", "defects", "releases")
               for item in _all_collection(runtime, cfg["project_id"], collection)}
    subjects = []
    for ref in refs:
        record = records.get(ref.get("id"))
        if record is None or record.get("version", 1) != ref.get("version"):
            raise ValueError("context reference is not current")
        content = record.get("content_ref", record.get("locator", {}))
        if "inline_json" in content:
            value = content["inline_json"]
        elif "path" in content:
            path = (cfg["root"] / content["path"]).resolve()
            if not path.is_relative_to(cfg["root"]) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != content.get("sha256"):
                raise ValueError("context artifact content drifted")
            value = path.read_text(encoding="utf-8", errors="replace")[:65536]
        else:
            # Lifecycle entities such as TEST_CASE have no file content_ref;
            # a redacted current structured record is the bounded handoff.
            value = {"record": record}
        subjects.append({"ref": ref, "content": LifecycleBase().redact_projection(value)})
    return {"schema_version": 1, "work": {key: work[key] for key in ("id", "activity", "why", "input_refs", "dependencies", "output_contract", "attempt", "version") if key in work},
            "resolved_subjects": subjects}


def _record_command_observation(svc, connection, project_id, agent_id, work_id, command):
    """Persist host-observed process facts without promoting model text to VERIFIED."""
    kept = {key: command.get(key) for key in ("status", "exit_code", "duration_seconds", "timed_out",
            "cancelled", "output_truncated", "launch_error", "response_path", "request_may_still_be_running", "recovery_required")}
    stdout = command.get("stdout", "")
    if isinstance(stdout, str):
        kept["stdout_sha256"] = hashlib.sha256(stdout.encode("utf-8")).hexdigest()
        kept["stdout_bytes"] = len(stdout.encode("utf-8"))
        kept["stdout"] = LifecycleBase().redact_projection(stdout)
    return svc.execute(connection, "evidence.register", {"project_id": project_id, "kind": "worker_command",
        "status": "OBSERVED", "source": {"kind": "host", "actor": agent_id}, "observed_at": LifecycleBase.now(),
        "locator": {"inline_json": {"work_order_id": work_id, "command": LifecycleBase().redact_projection(kept)}},
        "metadata": {}})


def _run_claim(runtime, cfg, worker, work, token, stop_event):
    cancel = threading.Event()
    result_box = {}
    try:
        context = _context_bundle(runtime, cfg, work) if worker["backend"]["type"] == "responses" else None
        if context is not None:
            sources=[]
            for relative in worker["source_paths"]:
                path=proposal_target(cfg["root"], proposal_path(relative, "source path"))
                if path.exists() and not path.is_file(): raise ValueError("allowed source is not a file")
                if not path.exists():
                    sources.append({"path": relative, "sha256": None, "content": None}); continue
                raw=path.read_bytes()
                if len(raw)>1048576: raise ValueError("allowed source exceeds byte budget")
                sources.append({"path":relative,"sha256":hashlib.sha256(raw).hexdigest(),"content":raw.decode("utf-8")})
            context["allowed_sources"]=sources
    except (ValueError, KeyError, OSError):
        # Context is assembled after claim; a stale/missing version must not
        # leave a lease active merely because no subprocess was started.
        try:
            with runtime.store.transaction() as connection:
                LifecycleService().execute(connection, "work.finish", {"work_order_id": work["id"], "agent_id": worker["agent_id"],
                    "lease_token": token, "status": "FAILED", "summary": "Worker context rejected before process launch", "output_refs": []})
            return "failed", {"status": "FAIL", "launch_error": "context rejected", "stdout": ""}
        except (ValueError, KeyError):
            return "cancelled", {"status": "FAIL", "launch_error": "context rejected after lease invalidation", "stdout": ""}
    thread = threading.Thread(target=lambda: result_box.setdefault("command", execute_backend(worker["backend"], repository_root=cfg["root"], timeout_seconds=worker["timeout_seconds"], max_output_bytes=worker["max_output_bytes"], cancel_event=cancel, context_bundle=context)), daemon=True)
    thread.start()
    heartbeat_after = time.monotonic() + min(worker["lease_seconds"] / 3, 10)
    cancelled = False
    try:
        while thread.is_alive():
            thread.join(cfg["poll"])
            if stop_event and stop_event.is_set(): cancelled = True
            snap = runtime.lifecycle_snapshot(cfg["project_id"], limit=1)
            current = next((item for item in _all_collection(runtime, cfg["project_id"], "work_orders") if item["id"] == work["id"]), None)
            if not current or current["status"] != "CLAIMED" or current.get("agent_id") != worker["agent_id"] or snap["lifecycle"]["state"] != "ACTIVE":
                cancelled = True
            if cancelled: cancel.set()
            if time.monotonic() >= heartbeat_after and not cancelled:
                try: runtime.execute("work.heartbeat", {"work_order_id": work["id"], "agent_id": worker["agent_id"], "lease_token": token})
                except (ValueError, KeyError): cancelled = True; cancel.set()
                heartbeat_after = time.monotonic() + min(worker["lease_seconds"] / 3, 10)
    finally:
        # The event reaches the bounded runner, which kills only its own tree.
        if thread.is_alive(): cancel.set(); thread.join(10)
    command = result_box.get("command", {"status": "FAIL", "launch_error": "backend thread did not return", "stdout": ""})
    if cancelled or command.get("cancelled"):
        with runtime.store.transaction() as connection:
            _record_command_observation(LifecycleService(), connection, cfg["project_id"], worker["agent_id"], work["id"], command)
        return "cancelled", command
    journal = None
    committed = False
    try:
        envelope = parse_envelope(command)
        if worker["backend"]["type"] == "responses" and "proposals" not in envelope:
            raise ValueError("Responses must return proposals")
        if worker["backend"]["type"] == "responses" and envelope["status"] == "DONE" and not envelope.get("proposals"):
            raise ValueError("DONE requires newly produced artifacts")
        with runtime.store.transaction() as connection:
            svc = LifecycleService()
            claim_data = {"work_order_id": work["id"], "agent_id": worker["agent_id"], "lease_token": token}
            svc.lease(connection, claim_data)
            if svc.project(connection, cfg["project_id"])["state"] != "ACTIVE":
                raise ValueError("lifecycle is not active")
            all_work = {item["id"]: item for item in svc.rows(connection, "work_orders", cfg["project_id"])}
            svc.refs(connection, cfg["project_id"], _bound_refs(work, all_work), nonempty=False)
            artifacts = envelope.get("artifacts", [])
            if envelope.get("proposals"):
                if envelope["status"] != "DONE": raise ValueError("non-DONE cannot publish proposals")
                journal, changes = prepare_proposals(cfg["root"], envelope["proposals"], worker["source_paths"],
                    binding={"project_id": cfg["project_id"], "work_id": work["id"], "attempt": work["attempt"], "db": str(Path(runtime.db_path).resolve())})
                apply_proposals(journal)
                artifacts = [{"id": c["id"], "type": c["type"], "title": c["title"],
                              "relative_path": c["path"], "sha256": c["new_sha256"]} for c in changes]
            _record_command_observation(svc, connection, cfg["project_id"], worker["agent_id"], work["id"], command)
            refs = _register_artifacts(svc, connection, cfg["project_id"], cfg["root"], worker["agent_id"], artifacts)
            svc.execute(connection, "work.finish", dict(claim_data, status=envelope["status"],
                summary=LifecycleBase().redact_projection(envelope["summary"]), output_refs=refs))
        committed = True
        if journal:
            # A failure here must retain APPLIED journal and committed files.
            # Next-start recovery proves exact DB outputs before preserving them.
            try: commit_proposals(journal, refs)
            except (ValueError, OSError): pass
        return "completed" if envelope["status"] == "DONE" else ("waiting_user" if envelope["status"] == "WAITING_USER" else "failed"), command
    except (ValueError, KeyError, OSError) as error:
        if journal and not committed:
            # Do not delete a journal; preserve recovery evidence and old bytes.
            try:
                with runtime.store.transaction():
                    rollback_proposals(journal)
            except (ValueError, OSError):
                command["recovery_required"] = True
                command["launch_error"] = "Proposal rollback blocked by external drift; journal retained"
        summary = "Worker command/envelope rejected: " + type(error).__name__
        try:
            with runtime.store.transaction() as connection:
                svc = LifecycleService()
                _record_command_observation(svc, connection, cfg["project_id"], worker["agent_id"], work["id"], command)
                svc.execute(connection, "work.finish", {"work_order_id": work["id"], "agent_id": worker["agent_id"],
                    "lease_token": token, "status": "FAILED", "summary": summary, "output_refs": []})
            return "failed", command
        except (ValueError, KeyError):
            return "cancelled", command


def run_service(runtime, config, *, once=False, stop_event=None) -> dict:
    """Claim and execute bounded trusted work; callers own the service lifetime."""
    if stop_event is not None and not callable(getattr(stop_event, "is_set", None)): raise ValueError("stop_event must provide is_set()")
    cfg = _validate(runtime, config)
    _recover_proposals(runtime, cfg)
    result = {"status": "IDLE", "claimed": 0, "completed": 0, "failed": 0, "waiting_user": 0, "cancelled": 0, "recovery_skipped": 0}
    while not (stop_event and stop_event.is_set()):
        runtime.execute("work.reap", {"project_id": cfg["project_id"]})
        snapshot = runtime.lifecycle_snapshot(cfg["project_id"], limit=1)
        if snapshot["lifecycle"]["state"] != "ACTIVE":
            if once: break
            time.sleep(cfg["poll"])
            continue
        snapshot["work_orders"] = _all_collection(runtime, cfg["project_id"], "work_orders")
        snapshot["events"] = _all_events(runtime, cfg["project_id"])
        unsafe_attempts = _unsafe_attempt_fences(snapshot)
        dispatched = []
        reserved = set()
        for worker in cfg["workers"]:
            if len(dispatched) >= cfg["max_concurrency"]: break
            claim = None
            for ready in (w for w in snapshot["work_orders"] if w["id"] not in reserved and w["status"] == "READY" and w["required_role"] == worker["role"]):
                if ready["id"] in unsafe_attempts and not worker["safe_to_retry"]:
                    result["recovery_skipped"] += 1; reserved.add(ready["id"]); continue
                try:
                    _validate_bound_refs(runtime, cfg["project_id"], ready, {item["id"]: item for item in snapshot["work_orders"]}, preclaim=True)
                except (ValueError, KeyError):
                    # No lease exists yet. Preserve a durable, auditable refusal
                    # instead of silently spinning on a drifted ready order.
                    runtime.execute("work.control", {"work_order_id": ready["id"], "action": "reject", "reason": "Worker input or dependency reference is stale"})
                    result["failed"] += 1; reserved.add(ready["id"]); continue
                try:
                    claim = runtime.execute("work.claim", {"work_order_id": ready["id"], "agent_id": worker["agent_id"], "lease_seconds": worker["lease_seconds"],
                        "expected_version": ready["version"], "safe_to_retry": worker["safe_to_retry"]})
                    break
                except (ValueError, KeyError): reserved.add(ready["id"])
            if claim is None: continue
            reserved.add(ready["id"]); result["claimed"] += 1
            state = {}
            thread = threading.Thread(target=lambda box=state, w=worker, c=claim: box.setdefault("value", _run_claim(runtime, cfg, w, c, c["lease_token"], stop_event)[0]), daemon=True)
            thread.start(); dispatched.append((thread, state))
        for thread, state in dispatched:
            thread.join()
            result[state.get("value", "cancelled")] += 1
        if once: break
        if not dispatched: time.sleep(cfg["poll"])
    result["status"] = "FAIL" if result["failed"] else ("WAITING_USER" if result["waiting_user"] else ("STOPPED" if stop_event and stop_event.is_set() else ("DISPATCHED" if result["claimed"] else "IDLE")))
    return result
