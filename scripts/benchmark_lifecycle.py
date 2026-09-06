"""Isolated synthetic capacity and soak evidence for the lifecycle SQLite store.

The seed deliberately bypasses Runtime writes in batches.  It measures read
capacity through Runtime's public snapshot and collection interfaces only.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import platform
import sqlite3
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from rd_platform.runtime import Runtime
from rd_platform.store import Store


MIB = 1024 * 1024
FULL_DISK_BUDGET_BYTES = 1536 * MIB
FULL_TIME_BUDGET_SECONDS = 600
MAX_SOAK_SECONDS = 72 * 60 * 60
WORKLOAD_SCOPE = {
    "kind": "SQLite public read-only probes",
    "public_read_operations": ["Runtime.lifecycle_collection", "Runtime.lifecycle_snapshot"],
    "excludes": ["Runtime write throughput", "full system stability", "write consistency"],
}


@dataclass(frozen=True)
class CapacityProfile:
    name: str
    projects: int
    artifact_versions: int
    events: int
    samples: int


PROFILES = {
    "smoke": CapacityProfile("smoke", projects=2, artifact_versions=200, events=1000, samples=5),
    "full": CapacityProfile("full", projects=100, artifact_versions=100000, events=1000000, samples=100),
}


class BudgetExceeded(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")


def _prepare_output(output_dir: str | Path) -> tuple[Path, Path, str]:
    directory = Path(output_dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    db_path = directory / "state.db"
    if db_path.exists():
        raise FileExistsError("refusing to overwrite existing benchmark state.db")
    return directory, db_path, "perf-" + uuid.uuid4().hex


def _rss_bytes() -> int | None:
    if os.name == "nt":
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        if psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return int(counters.WorkingSetSize)
        return None
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value * 1024 if sys.platform != "darwin" else value)
    except (ImportError, AttributeError):
        return None


def _environment() -> dict[str, Any]:
    return {"python": sys.version, "platform": platform.platform(), "sqlite": sqlite3.sqlite_version,
            "available_cpu_count": os.cpu_count(), "rss_bytes": _rss_bytes()}


def _percentiles(samples_ns: list[int]) -> dict[str, float | int]:
    if not samples_ns:
        return {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "throughput_per_second": 0.0}
    ordered = sorted(samples_ns)
    value = lambda percentile: ordered[math.ceil(percentile * len(ordered)) - 1] / 1_000_000
    total = sum(samples_ns) / 1_000_000_000
    return {"count": len(samples_ns), "p50_ms": value(.50), "p95_ms": value(.95), "p99_ms": value(.99),
            "throughput_per_second": len(samples_ns) / total if total else 0.0}


def _guard(db_path: Path, started: float, disk_budget_bytes: int, time_budget_seconds: int | None) -> None:
    if db_path.exists() and db_path.stat().st_size > disk_budget_bytes:
        raise BudgetExceeded("disk budget exceeded")
    if time_budget_seconds is not None and time.monotonic() - started > time_budget_seconds:
        raise BudgetExceeded("time budget exceeded")


def _seed(db_path: Path, profile: CapacityProfile, *, disk_budget_bytes: int, time_budget_seconds: int | None, started: float,
          on_progress=None) -> list[str]:
    runtime = Runtime(db_path)
    project_ids = [f"perf-project-{number:03d}" for number in range(profile.projects)]
    timestamp = _now()
    with runtime.store.transaction() as connection:
        for project_id in project_ids:
            connection.execute("INSERT INTO projects VALUES (?,?,?,?,?)", (project_id, project_id, "synthetic capacity fixture", "ACTIVE", timestamp))
            lifecycle = {"id": project_id, "project_id": project_id, "repository_root": str(db_path.parent), "mode": "active",
                         "current_gate": "G0", "state": "ACTIVE", "policy_version": "lifecycle-v1", "created_at": timestamp}
            connection.execute("INSERT INTO lc_projects VALUES (?,?,?,?)", (project_id, project_id, "ACTIVE", Store.dumps(lifecycle)))
            for ordinal in range(12):
                gate_id = f"{project_id}:G{ordinal}"
                gate = {"id": gate_id, "project_id": project_id, "gate_id": f"G{ordinal}", "ordinal": ordinal,
                        "evaluation_state": "NOT_EVALUATED", "gate_status": None, "current_assessment_id": None, "decided_at": None}
                connection.execute("INSERT INTO lc_gates VALUES (?,?,?,?)", (gate_id, project_id, "CURRENT", Store.dumps(gate)))
    for offset in range(0, profile.artifact_versions, 5000):
        with runtime.store.transaction() as connection:
            rows = []
            versions = []
            for number in range(offset, min(offset + 5000, profile.artifact_versions)):
                project_id = project_ids[number % len(project_ids)]
                artifact_id = f"DOC-PERF-{number:06d}"
                artifact = {"id": artifact_id, "artifact_id": artifact_id, "project_id": project_id, "artifact_type": "DOC",
                            "title": "synthetic capacity artifact", "version": 1, "state": "BASELINED",
                            "content_ref": {"inline_json": {"synthetic": number}, "sha256": "synthetic"}, "created_at": timestamp}
                encoded = Store.dumps(artifact)
                rows.append((artifact_id, project_id, "BASELINED", encoded))
                versions.append((artifact_id, 1, encoded))
            connection.executemany("INSERT INTO lc_artifacts VALUES (?,?,?,?)", rows)
            connection.executemany("INSERT INTO lc_artifact_versions VALUES (?,?,?)", versions)
        _guard(db_path, started, disk_budget_bytes, time_budget_seconds)
        if on_progress:
            on_progress(min(offset + 5000, profile.artifact_versions), 0)
    for offset in range(0, profile.events, 5000):
        with runtime.store.transaction() as connection:
            rows = [(project_ids[number % len(project_ids)], f"perf-event-{number:08d}", "synthetic.seeded", "synthetic", "{}", timestamp, timestamp)
                    for number in range(offset, min(offset + 5000, profile.events))]
            connection.executemany("INSERT INTO lc_events(project_id,event_id,type,entity_id,data,occurred_at,recorded_at) VALUES (?,?,?,?,?,?,?)", rows)
        _guard(db_path, started, disk_budget_bytes, time_budget_seconds)
        if on_progress:
            on_progress(profile.artifact_versions, min(offset + 5000, profile.events))
    return project_ids


def _measure_reads(db_path: Path, project_ids: list[str], samples: int, *, deadline: float | None = None) -> dict[str, Any]:
    collection, snapshot, errors = [], [], []
    runtime = Runtime(db_path)
    def check_deadline() -> None:
        if deadline is not None and time.monotonic() > deadline:
            raise BudgetExceeded("time budget exceeded during public read measurement")
    for number in range(samples):
        project_id = project_ids[number % len(project_ids)]
        check_deadline()
        begin = time.perf_counter_ns()
        try:
            runtime.lifecycle_collection(project_id, "artifacts", limit=500)
            collection.append(time.perf_counter_ns() - begin)
            check_deadline()
        except BudgetExceeded:
            raise
        except Exception as error:
            errors.append({"operation": "collection", "error": f"{type(error).__name__}: {error}"})
        check_deadline()
        begin = time.perf_counter_ns()
        try:
            runtime.lifecycle_snapshot(project_id, limit=500)
            snapshot.append(time.perf_counter_ns() - begin)
            check_deadline()
        except BudgetExceeded:
            raise
        except Exception as error:
            errors.append({"operation": "snapshot", "error": f"{type(error).__name__}: {error}"})
    return {"collection": _percentiles(collection), "snapshot": _percentiles(snapshot), "errors": errors}


def _terminal(directory: Path, run_id: str, result: dict[str, Any]) -> dict[str, Any]:
    path = directory / f"{run_id}-terminal.json"
    result["terminal_json"] = str(path)
    _write_json(path, result)
    return result


def run_capacity(output_dir: str | Path, profile: CapacityProfile, *, disk_budget_bytes: int = FULL_DISK_BUDGET_BYTES,
                 time_budget_seconds: int | None = FULL_TIME_BUDGET_SECONDS) -> dict[str, Any]:
    if min(profile.projects, profile.artifact_versions, profile.events, profile.samples) <= 0 or disk_budget_bytes <= 0:
        raise ValueError("positive capacity profile and disk budget required")
    directory, db_path, run_id = _prepare_output(output_dir)
    started, cpu_started = time.monotonic(), time.process_time()
    result: dict[str, Any] = {"schema_version": "lifecycle-capacity-v1", "run_id": run_id, "mode": "capacity", "profile": asdict(profile),
                              "seed_mode": "synthetic_batch_sql", "workload_scope": WORKLOAD_SCOPE, "started_at": _now(), "environment": _environment(), "phase": "setup"}
    checkpoint = directory / f"{run_id}-checkpoint.json"
    result["checkpoint_json"] = str(checkpoint)
    def progress(artifact_versions: int, events: int) -> None:
        result["progress"] = {"projects": profile.projects, "artifact_versions": artifact_versions, "events": events}
        _write_json(checkpoint, result)
    try:
        progress(0, 0)
        result["phase"] = "seed"
        projects = _seed(db_path, profile, disk_budget_bytes=disk_budget_bytes, time_budget_seconds=time_budget_seconds, started=started, on_progress=progress)
        deadline = started + time_budget_seconds if time_budget_seconds is not None else None
        result["phase"] = "public_read_measurement"
        reads = _measure_reads(db_path, projects, profile.samples, deadline=deadline)
        result.update(status="PASS" if not reads["errors"] else "FAIL", exit_code=0 if not reads["errors"] else 1,
                      seeded={"projects": profile.projects, "artifact_versions": profile.artifact_versions, "events": profile.events}, reads=reads)
    except BudgetExceeded as error:
        result.update(status="ABORTED", exit_code=2, reason=str(error))
    except KeyboardInterrupt:
        result.update(status="INTERRUPTED", exit_code=130, reason="KeyboardInterrupt")
    except Exception as error:
        result.update(status="FAIL", exit_code=1, error=f"{type(error).__name__}: {error}")
    result.update(finished_at=_now(), elapsed_seconds=time.monotonic() - started, actual_duration_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started,
                  database_bytes=db_path.stat().st_size if db_path.exists() else 0, rss_bytes=_rss_bytes(), disk_budget_bytes=disk_budget_bytes,
                  time_budget_seconds=time_budget_seconds)
    _write_json(checkpoint, result)
    return _terminal(directory, run_id, result)


def run_soak(output_dir: str | Path, profile: CapacityProfile, *, duration_seconds: int, interval_seconds: int,
             disk_budget_bytes: int = FULL_DISK_BUDGET_BYTES) -> dict[str, Any]:
    if type(duration_seconds) is not int or not 1 <= duration_seconds <= MAX_SOAK_SECONDS:
        raise ValueError("duration_seconds must be 1..259200")
    if type(interval_seconds) is not int or interval_seconds < 1:
        raise ValueError("interval_seconds must be at least 1")
    started, cpu_started, soak_started_at = time.monotonic(), time.process_time(), _now()
    directory, db_path = Path(output_dir).resolve(), Path(output_dir).resolve() / "state.db"
    run_id = "soak-" + uuid.uuid4().hex
    checkpoint = directory / f"{run_id}-checkpoint.json"
    try:
        capacity = run_capacity(output_dir, profile, disk_budget_bytes=disk_budget_bytes, time_budget_seconds=FULL_TIME_BUDGET_SECONDS)
    except KeyboardInterrupt:
        directory.mkdir(parents=True, exist_ok=True)
        interrupted = {"schema_version": "lifecycle-soak-v1", "run_id": run_id, "mode": "soak", "seed_mode": "synthetic_batch_sql",
                       "started_at": soak_started_at, "duration_seconds": duration_seconds, "interval_seconds": interval_seconds, "environment": _environment(),
                       "workload_scope": WORKLOAD_SCOPE, "phase": "capacity_setup", "status": "INTERRUPTED", "exit_code": 130,
                       "reason": "KeyboardInterrupt", "checkpoint_json": str(checkpoint), "actual_duration_seconds": time.monotonic() - started}
        _write_json(checkpoint, interrupted)
        return _terminal(directory, run_id, interrupted)
    result: dict[str, Any] = {"schema_version": "lifecycle-soak-v1", "run_id": run_id, "mode": "soak", "seed_mode": "synthetic_batch_sql",
                              "capacity_terminal_json": capacity["terminal_json"], "started_at": soak_started_at, "duration_seconds": duration_seconds,
                              "interval_seconds": interval_seconds, "environment": _environment(), "samples": {"collection_ms": [], "snapshot_ms": []},
                              "reads": {"errors": []}, "resource_samples": [], "workload_scope": WORKLOAD_SCOPE, "phase": "capacity_setup"}
    if capacity["status"] != "PASS":
        interrupted = capacity["status"] == "INTERRUPTED"
        result.update(status="INTERRUPTED" if interrupted else "ABORTED", exit_code=130 if interrupted else 2,
                      reason="KeyboardInterrupt during capacity setup" if interrupted else "capacity seed did not pass",
                      actual_duration_seconds=time.monotonic() - started)
        result["checkpoint_json"] = str(checkpoint)
        _write_json(checkpoint, result)
        return _terminal(directory, run_id, result)
    result["phase"] = "sampling"
    deadline = time.monotonic() + duration_seconds
    try:
        while True:
            reads = _measure_reads(db_path, ["perf-project-000"], 1)
            result["samples"]["collection_ms"].append(reads["collection"]["p50_ms"])
            result["samples"]["snapshot_ms"].append(reads["snapshot"]["p50_ms"])
            result["reads"]["errors"].extend(reads["errors"])
            result["elapsed_seconds"] = time.monotonic() - started
            result["resource_samples"].append({"elapsed_seconds": result["elapsed_seconds"], "cpu_seconds": time.process_time() - cpu_started,
                                               "rss_bytes": _rss_bytes(), "database_bytes": db_path.stat().st_size})
            result["checkpoint_json"] = str(checkpoint)
            _write_json(checkpoint, result)
            if time.monotonic() >= deadline:
                break
            time.sleep(min(interval_seconds, max(0, deadline - time.monotonic())))
        result["reads"] = {"collection": _percentiles([int(value * 1_000_000) for value in result["samples"]["collection_ms"]]),
                           "snapshot": _percentiles([int(value * 1_000_000) for value in result["samples"]["snapshot_ms"]]),
                           "errors": result["reads"]["errors"]}
        result.update(status="PASS" if not result["reads"]["errors"] else "FAIL", exit_code=0 if not result["reads"]["errors"] else 1)
    except KeyboardInterrupt:
        result.update(status="INTERRUPTED", exit_code=130, reason="KeyboardInterrupt")
    except Exception as error:
        result.update(status="FAIL", exit_code=1, error=f"{type(error).__name__}: {error}")
    result.update(finished_at=_now(), elapsed_seconds=time.monotonic() - started, actual_duration_seconds=time.monotonic() - started, database_bytes=db_path.stat().st_size if db_path.exists() else 0,
                  rss_bytes=_rss_bytes(), checkpoint_json=str(checkpoint))
    _write_json(checkpoint, result)
    return _terminal(directory, run_id, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="isolated synthetic lifecycle capacity and soak benchmark")
    parser.add_argument("mode", choices=("capacity", "soak"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="smoke")
    parser.add_argument("--duration-seconds", type=int)
    parser.add_argument("--interval-seconds", type=int, default=1)
    args = parser.parse_args(argv)
    if args.mode == "capacity":
        result = run_capacity(args.output_dir, PROFILES[args.profile])
    else:
        if args.duration_seconds is None:
            parser.error("soak requires --duration-seconds")
        result = run_soak(args.output_dir, PROFILES[args.profile], duration_seconds=args.duration_seconds, interval_seconds=args.interval_seconds)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
