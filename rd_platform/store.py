"""SQLite storage primitives used exclusively by :mod:`rd_platform.runtime`."""

from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


# Explicit data-contract limits, independent of Python encoder/decoder stacks.
# Root containers have depth 1. Nodes count expanded JSON values, including
# containers (object keys are not separate value nodes).
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000


def _validate_json_structure(value: object) -> None:
    """Bound expanded traversal while allowing shared, non-circular containers."""
    active: set[int] = set()
    # Iterator frames keep memory proportional to depth, not container width.
    frames = [(iter((value,)), 0, None)]
    nodes = 0
    while frames:
        children, parent_depth, owner = frames[-1]
        try:
            item = next(children)
        except StopIteration:
            frames.pop()
            if owner is not None:
                active.remove(owner)
            continue
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise ValueError('JSON expanded node limit exceeded')
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('non-finite JSON value')
        if not isinstance(item, (dict, list, tuple)):
            continue # The standard encoder retains scalar/type validation.
        depth = parent_depth + 1
        if depth > MAX_JSON_DEPTH:
            raise ValueError('JSON container depth exceeds 64')
        identity = id(item)
        if identity in active:
            raise ValueError('circular JSON container reference')
        if len(item) > MAX_JSON_NODES - nodes:
            raise ValueError('JSON expanded node limit exceeded')
        if isinstance(item, dict):
            for key in item:
                if isinstance(key, float) and not math.isfinite(key):
                    raise ValueError('non-finite JSON object key')
            iterator = iter(item.values())
        else:
            iterator = iter(item)
        active.add(identity)
        frames.append((iterator, depth, identity))


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, idea TEXT NOT NULL, stage TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, role TEXT NOT NULL, status TEXT NOT NULL, task_id TEXT, heartbeat_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks (
 id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id), title TEXT NOT NULL, why TEXT NOT NULL, role TEXT NOT NULL,
 requirements TEXT NOT NULL, dependencies TEXT NOT NULL, inputs TEXT NOT NULL, status TEXT NOT NULL, revision INTEGER NOT NULL,
 attempt INTEGER NOT NULL, retry_count INTEGER NOT NULL, next_phase TEXT NOT NULL, assignee_id TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), agent_id TEXT NOT NULL REFERENCES agents(id), phase TEXT NOT NULL,
 status TEXT NOT NULL, revision INTEGER NOT NULL, attempt INTEGER NOT NULL, evidence TEXT, summary TEXT, created_at TEXT NOT NULL, finished_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run_per_task ON runs(task_id) WHERE status = 'ACTIVE';
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run_per_agent ON runs(agent_id) WHERE status = 'ACTIVE';
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, type TEXT NOT NULL, project_id TEXT, task_id TEXT, run_id TEXT, created_at TEXT NOT NULL, data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS defects (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), run_id TEXT NOT NULL REFERENCES runs(id), status TEXT NOT NULL,
 revision INTEGER NOT NULL, attempt INTEGER NOT NULL, summary TEXT NOT NULL, evidence TEXT NOT NULL, created_at TEXT NOT NULL, closed_at TEXT
);
CREATE TABLE IF NOT EXISTS requests (
 request_id TEXT PRIMARY KEY, command TEXT NOT NULL, payload TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, db_path: str | Path):
        self.path = str(db_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            connection.executescript(SCHEMA)
        from .lifecycle_store import migrate
        with self.transaction() as connection:
            migrate(connection)

    @contextmanager
    def transaction(self, *, write: bool = True) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def dumps(value: object) -> str:
        _validate_json_structure(value)
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except RecursionError as error:
            raise ValueError("JSON encoding exceeded host recursion capacity") from error

    @staticmethod
    def loads(value: str | None, default: object = None) -> object:
        if value is None:
            return default
        try:
            decoded = json.loads(value, parse_constant=Store._reject_nonfinite_constant)
        except RecursionError as error:
            raise ValueError("JSON nesting is too deep") from error
        _validate_json_structure(decoded)
        return decoded

    @staticmethod
    def _reject_nonfinite_constant(token: str):
        raise ValueError("non-finite JSON value: " + token)
