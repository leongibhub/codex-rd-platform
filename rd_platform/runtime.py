"""Transactional state machine for the V2 local control plane.

The public ``Runtime`` methods are intentionally small; HTTP and CLI adapters
consume this module but do not duplicate its authorization or state checks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .store import Store


PHASES = ("implementation", "unit", "integration", "review")
ROLES = {"developer", "tester", "reviewer", "requirement_analyst", "product_manager", "architect", "researcher", "release_manager", "documentation_manager"}
MAX_RETRIES = 3


class Runtime:
    """A SQLite-backed runtime.  Every public operation uses one transaction."""

    def __init__(self, db_path: str | Path, *, approval_provider=None):
        self.db_path = str(db_path)
        self.store = Store(db_path)
        self.approval_provider = approval_provider

    def execute(self, command: str, data: dict, *, request_id: str | None = None) -> dict:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("command must be a non-empty string")
        if not isinstance(data, dict):
            raise ValueError("data must be an object")
        if request_id is not None:
            self._text(request_id, "request_id")
        try:
            payload = Store.dumps(data)
        except (RecursionError, TypeError, ValueError) as error:
            raise ValueError("data must be JSON-serializable") from error
        if command.startswith("work.") and "lease_token" in data:
            import hashlib
            token = self._text(data["lease_token"], "lease_token")
            payload = Store.dumps({**data, "lease_token": hashlib.sha256(token.encode()).hexdigest()})
        with self.store.transaction() as connection:
            if request_id is not None:
                old = connection.execute("SELECT command, payload, result FROM requests WHERE request_id = ?", (request_id,)).fetchone()
                if old:
                    if old["command"] != command or old["payload"] != payload:
                        raise ValueError("request_id was already used with different command or data")
                    if command == "work.claim":
                        from .lifecycle import LifecycleService
                        result = LifecycleService().recover_claim(connection, data, Store.loads(old["result"]))
                        cached = {key:value for key,value in result.items() if key != "lease_token"}
                        connection.execute("UPDATE requests SET result=? WHERE request_id=?", (Store.dumps(cached),request_id))
                        return result
                    return Store.loads(old["result"])
            if command in {"project.create", "agent.register", "task.create", "run.start", "run.heartbeat", "run.finish", "task.control", "project.control"}:
                handler = getattr(self, "_" + command.replace(".", "_"), None)
                result = handler(connection, data)
            else:
                from .lifecycle import LifecycleService
                if command not in LifecycleService.COMMANDS:
                    raise ValueError("unknown command")
                result = LifecycleService().execute(connection, command, data)
            if request_id is not None:
                persisted_result = result
                if command == "work.claim":
                    persisted_result = {key: value for key, value in result.items() if key != "lease_token"}
                    persisted_result["lease_token_redacted"] = True
                connection.execute("INSERT INTO requests VALUES (?, ?, ?, ?, ?)", (request_id, command, payload, Store.dumps(persisted_result), self._now()))
            return result

    def lifecycle_snapshot(self, project_id: str, *, after_sequence: int = 0, limit: int = 200) -> dict:
        from .lifecycle import LifecycleService
        with self.store.transaction(write=False) as connection:
            return LifecycleService().snapshot(connection, project_id, after_sequence=after_sequence, limit=limit)

    def lifecycle_collection(self, project_id: str, collection: str, *, limit: int = 200, after_cursor: str | None = None) -> dict:
        """Read one public lifecycle collection page without changing state."""
        from .lifecycle_query import LifecycleCollectionQuery
        with self.store.transaction(write=False) as connection:
            return LifecycleCollectionQuery().read(connection, project_id, collection, limit=limit, after_cursor=after_cursor)

    def register_human_approval(self, data: dict, *, operator: str) -> dict:
        """Authenticate an approval through a host-injected verification provider.

        No provider is configured by default. ``operator`` is only a claimed hint;
        the provider must authenticate it and return the exact computed binding.
        """
        from .lifecycle import LifecycleService
        with self.store.transaction() as connection:
            return LifecycleService().human_approval(connection, data, operator=operator, provider=self.approval_provider)

    def snapshot(self, project_id: str | None = None) -> dict:
        if project_id is not None:
            self._text(project_id, "project_id")
        with self.store.transaction(write=False) as connection:
            if project_id is not None and not self._one(connection, "projects", project_id):
                raise KeyError("project not found")
            where, parameters = ("", ()) if project_id is None else (" WHERE project_id = ?", (project_id,))
            tasks = [self._task(row, connection) for row in connection.execute("SELECT * FROM tasks" + where + " ORDER BY created_at, id", parameters)]
            task_ids = [task["id"] for task in tasks]
            runs = self._related(connection, "runs", task_ids, self._run)
            if project_id is None:
                events = [self._event(row) for row in connection.execute("SELECT rowid AS sequence, * FROM events ORDER BY rowid")]
            else:
                events = [self._event(row) for row in connection.execute("SELECT rowid AS sequence, * FROM events WHERE project_id=? ORDER BY rowid", (project_id,))]
            defects = self._related(connection, "defects", task_ids, self._defect)
            projects = [self._project(row) for row in connection.execute("SELECT * FROM projects" + ("" if project_id is None else " WHERE id = ?") + " ORDER BY created_at, id", (() if project_id is None else (project_id,)))]
            agents = [self._agent(row) for row in connection.execute("SELECT * FROM agents ORDER BY created_at, id")]
            return {"projects": projects, "agents": agents, "tasks": tasks, "runs": runs, "events": events, "defects": defects}

    # Commands
    def _project_create(self, c, data):
        name, idea = self._text(data.get("name"), "name"), self._text(data.get("idea"), "idea")
        row = {"id": self._id("project"), "name": name, "idea": idea, "stage": "ACTIVE", "created_at": self._now()}
        c.execute("INSERT INTO projects VALUES (:id,:name,:idea,:stage,:created_at)", row)
        self._event_add(c, "project.created", row["id"], None, None, {"name": name})
        return self._project(row)

    def _agent_register(self, c, data):
        ident, role = self._text(data.get("id"), "id"), self._role(data.get("role"))
        if self._one(c, "agents", ident):
            raise ValueError("agent id already exists")
        row = {"id": ident, "role": role, "status": "AVAILABLE", "task_id": None, "heartbeat_at": None, "created_at": self._now()}
        c.execute("INSERT INTO agents VALUES (:id,:role,:status,:task_id,:heartbeat_at,:created_at)", row)
        self._event_add(c, "agent.registered", None, None, None, {"agent_id": ident, "role": role})
        return self._agent(row)

    def _task_create(self, c, data):
        project = self._require(c, "projects", data.get("project_id"), "project")
        title, why, role = self._text(data.get("title"), "title"), self._text(data.get("why"), "why"), self._role(data.get("role"))
        requirements, dependencies, inputs = data.get("requirements"), data.get("dependencies"), data.get("inputs")
        if not isinstance(requirements, list) or not requirements or any(not isinstance(value, str) or not value.strip() for value in requirements): raise ValueError("requirements must be a non-empty list of strings")
        if not isinstance(dependencies, list) or any(not isinstance(value, str) or not value for value in dependencies):
            raise ValueError("dependencies must be a unique list of ids")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("dependencies must be a unique list of ids")
        if not isinstance(inputs, dict): raise ValueError("inputs must be an object")
        for dependency in dependencies:
            row = self._require(c, "tasks", dependency, "dependency")
            if row["project_id"] != project["id"]: raise ValueError("dependency must belong to the same project")
        row = {"id": self._id("task"), "project_id": project["id"], "title": title, "why": why, "role": role, "requirements": Store.dumps(requirements), "dependencies": Store.dumps(dependencies), "inputs": Store.dumps(inputs), "status": "READY", "revision": 1, "attempt": 1, "retry_count": 0, "next_phase": "implementation", "assignee_id": None, "created_at": self._now()}
        c.execute("INSERT INTO tasks VALUES (:id,:project_id,:title,:why,:role,:requirements,:dependencies,:inputs,:status,:revision,:attempt,:retry_count,:next_phase,:assignee_id,:created_at)", row)
        self._event_add(c, "task.created", project["id"], row["id"], None, {"requirements": requirements, "dependencies": dependencies})
        return self._task(row, c)

    def _run_start(self, c, data):
        task = self._require(c, "tasks", data.get("task_id"), "task")
        agent = self._require(c, "agents", data.get("agent_id"), "agent")
        phase = data.get("phase")
        if not isinstance(phase, str) or phase not in PHASES: raise ValueError("invalid phase")
        project = self._require(c, "projects", task["project_id"], "project")
        if project["stage"] != "ACTIVE" or task["status"] != "READY": raise ValueError("task is not startable")
        if phase != task["next_phase"]: raise ValueError("phase is not the next required quality check")
        if c.execute("SELECT 1 FROM runs WHERE task_id=? AND status='ACTIVE'", (task["id"],)).fetchone(): raise ValueError("task already has an active run")
        if agent["status"] != "AVAILABLE" or c.execute("SELECT 1 FROM runs WHERE agent_id=? AND status='ACTIVE'", (agent["id"],)).fetchone():
            raise ValueError("agent already has an active run")
        if task["assignee_id"] is not None and task["assignee_id"] != agent["id"]:
            raise ValueError("task is assigned to another agent")
        dependencies = Store.loads(task["dependencies"])
        if dependencies and c.execute("SELECT COUNT(*) FROM tasks WHERE id IN (%s) AND status='DONE'" % ",".join("?" * len(dependencies)), dependencies).fetchone()[0] != len(dependencies): raise ValueError("dependencies are not DONE")
        expected_role = task["role"] if phase == "implementation" else ("reviewer" if phase == "review" else "tester")
        if agent["role"] != expected_role: raise ValueError("agent role cannot execute this phase")
        if phase != "implementation":
            implementation = c.execute("SELECT agent_id FROM runs WHERE task_id=? AND revision=? AND attempt=? AND phase='implementation' AND status='PASS'", (task["id"], task["revision"], task["attempt"])).fetchone()
            if not implementation: raise ValueError("implementation has not passed")
            if agent["id"] == implementation["agent_id"]: raise ValueError("developer cannot self-validate")
        row = {"id": self._id("run"), "task_id": task["id"], "agent_id": agent["id"], "phase": phase, "status": "ACTIVE", "revision": task["revision"], "attempt": task["attempt"], "evidence": None, "summary": None, "created_at": self._now(), "finished_at": None}
        c.execute("INSERT INTO runs VALUES (:id,:task_id,:agent_id,:phase,:status,:revision,:attempt,:evidence,:summary,:created_at,:finished_at)", row)
        c.execute("UPDATE tasks SET status='ACTIVE' WHERE id=?", (task["id"],)); c.execute("UPDATE agents SET status='BUSY', task_id=?, heartbeat_at=? WHERE id=?", (task["id"], self._now(), agent["id"]))
        self._event_add(c, "run.started", task["project_id"], task["id"], row["id"], {"phase": phase, "agent_id": agent["id"]})
        return self._run(row)

    def _run_heartbeat(self, c, data):
        run = self._require(c, "runs", data.get("run_id"), "run")
        if run["status"] != "ACTIVE": raise ValueError("run is not active")
        now = self._now(); c.execute("UPDATE agents SET heartbeat_at=? WHERE id=?", (now, run["agent_id"])); c.execute("UPDATE runs SET created_at=created_at WHERE id=?", (run["id"],))
        result = dict(run); self._event_add(c, "run.heartbeat", self._task_project(c, run["task_id"]), run["task_id"], run["id"], {})
        return self._run(result)

    def _run_finish(self, c, data):
        run = self._require(c, "runs", data.get("run_id"), "run"); task = self._require(c, "tasks", run["task_id"], "task")
        status, summary, evidence = data.get("status"), self._text(data.get("summary"), "summary"), data.get("evidence")
        if not isinstance(status, str) or status not in {"PASS", "FAIL"}: raise ValueError("status must be PASS or FAIL")
        if not isinstance(evidence, dict) or not evidence: raise ValueError("evidence must be a non-empty object")
        self._validate_evidence(status, evidence)
        if run["status"] != "ACTIVE" or task["revision"] != run["revision"] or task["attempt"] != run["attempt"]: raise ValueError("run is stale or inactive")
        dependencies = Store.loads(task["dependencies"])
        if dependencies and c.execute("SELECT COUNT(*) FROM tasks WHERE id IN (%s) AND status='DONE'" % ",".join("?" * len(dependencies)), dependencies).fetchone()[0] != len(dependencies):
            raise ValueError("dependencies are no longer DONE")
        now = self._now(); c.execute("UPDATE runs SET status=?, summary=?, evidence=?, finished_at=? WHERE id=?", (status, summary, Store.dumps(evidence), now, run["id"])); c.execute("UPDATE agents SET status='AVAILABLE', task_id=NULL WHERE id=?", (run["agent_id"],))
        if status == "PASS":
            c.execute("UPDATE tasks SET assignee_id=NULL WHERE id=?", (task["id"],))
        if status == "FAIL":
            c.execute("UPDATE tasks SET status='FAILED', next_phase='implementation' WHERE id=?", (task["id"],))
            defect = {"id": self._id("defect"), "task_id": task["id"], "run_id": run["id"], "status": "OPEN", "revision": task["revision"], "attempt": task["attempt"], "summary": summary, "evidence": Store.dumps(evidence), "created_at": now, "closed_at": None}
            c.execute("INSERT INTO defects VALUES (:id,:task_id,:run_id,:status,:revision,:attempt,:summary,:evidence,:created_at,:closed_at)", defect)
            self._event_add(c, "defect.opened", task["project_id"], task["id"], run["id"], {"defect_id": defect["id"]})
        else:
            position = PHASES.index(run["phase"])
            if run["phase"] == "review":
                c.execute("UPDATE tasks SET status='DONE', next_phase='DONE' WHERE id=?", (task["id"],))
                c.execute("UPDATE defects SET status='CLOSED', closed_at=? WHERE task_id=? AND status='OPEN'", (now, task["id"]))
            else: c.execute("UPDATE tasks SET status='READY', next_phase=? WHERE id=?", (PHASES[position + 1], task["id"]))
        self._event_add(c, "run.finished", task["project_id"], task["id"], run["id"], {"status": status, "phase": run["phase"]})
        return self._task(self._require(c, "tasks", task["id"], "task"), c)

    def _task_control(self, c, data):
        task = self._require(c, "tasks", data.get("task_id"), "task"); action = data.get("action")
        if not isinstance(action, str) or action not in {"pause", "resume", "retry", "reject", "reassign", "modify", "skip"}: raise ValueError("invalid task action")
        reason = self._text(data.get("reason"), "reason")
        if action == "pause":
            if task["status"] not in {"READY", "ACTIVE"}: raise ValueError("only ready or active task can be paused")
            self._invalidate(c, task, "paused"); c.execute("UPDATE tasks SET status='PAUSED' WHERE id=?", (task["id"],))
        elif action == "resume":
            if task["status"] != "PAUSED": raise ValueError("only paused task can resume")
            c.execute("UPDATE tasks SET status='READY' WHERE id=?", (task["id"],))
        elif action == "retry":
            if task["status"] != "FAILED": raise ValueError("only failed task can retry")
            if task["retry_count"] >= MAX_RETRIES: raise ValueError("retry limit reached")
            c.execute("UPDATE tasks SET status='READY', attempt=attempt+1, retry_count=retry_count+1, next_phase='implementation', assignee_id=NULL WHERE id=?", (task["id"],))
        elif action == "reject":
            self._cancel(c, task, "REJECTED", "rejected")
        elif action == "skip":
            self._cancel(c, task, "SKIPPED", "skipped")
        elif action == "reassign":
            agent = self._require(c, "agents", data.get("agent_id"), "agent")
            if task["status"] != "READY": raise ValueError("only ready task can be reassigned")
            expected_role = task["role"] if task["next_phase"] == "implementation" else ("reviewer" if task["next_phase"] == "review" else "tester")
            if agent["role"] != expected_role: raise ValueError("assignee role must match next phase")
            if agent["status"] != "AVAILABLE": raise ValueError("assignee is not available")
            c.execute("UPDATE tasks SET assignee_id=? WHERE id=?", (agent["id"], task["id"]))
        else:
            changes = {}
            for field in ("title", "why"):
                if field in data: changes[field] = self._text(data[field], field)
            if "inputs" in data:
                if not isinstance(data["inputs"], dict): raise ValueError("inputs must be an object")
                changes["inputs"] = Store.dumps(data["inputs"])
            if not changes: raise ValueError("modify needs title, why, or inputs")
            self._invalidate(c, task, "modified"); changes.update({"revision": task["revision"] + 1, "attempt": 1, "retry_count": 0, "next_phase": "implementation", "status": "READY", "assignee_id": None})
            c.execute("UPDATE tasks SET " + ", ".join(key + "=?" for key in changes) + " WHERE id=?", tuple(changes.values()) + (task["id"],))
            self._invalidate_dependents(c, task, "upstream modified")
        self._event_add(c, "task." + action, task["project_id"], task["id"], None, {"reason": reason})
        return self._task(self._require(c, "tasks", task["id"], "task"), c)

    def _project_control(self, c, data):
        project = self._require(c, "projects", data.get("project_id"), "project"); action = data.get("action"); reason = self._text(data.get("reason"), "reason")
        if not isinstance(action, str) or action not in {"pause", "resume"}: raise ValueError("invalid project action")
        target = "PAUSED" if action == "pause" else "ACTIVE"
        if project["stage"] == target: raise ValueError("project already in requested state")
        c.execute("UPDATE projects SET stage=? WHERE id=?", (target, project["id"]))
        if action == "pause":
            active_tasks = c.execute("SELECT * FROM tasks WHERE project_id=? AND status='ACTIVE'", (project["id"],)).fetchall()
            for task in active_tasks:
                self._invalidate(c, task, "project paused")
                c.execute("UPDATE tasks SET status='READY' WHERE id=?", (task["id"],))
        self._event_add(c, "project." + action, project["id"], None, None, {"reason": reason})
        return self._project(self._require(c, "projects", project["id"], "project"))

    # Internal helpers
    def _invalidate(self, c, task, reason):
        active = c.execute("SELECT * FROM runs WHERE task_id=? AND status='ACTIVE'", (task["id"],)).fetchall()
        for run in active:
            c.execute("UPDATE runs SET status='INVALIDATED', finished_at=? WHERE id=?", (self._now(), run["id"])); c.execute("UPDATE agents SET status='AVAILABLE', task_id=NULL WHERE id=?", (run["agent_id"],))
            self._event_add(c, "run.invalidated", task["project_id"], task["id"], run["id"], {"reason": reason})

    def _cancel(self, c, task, status, reason):
        self._invalidate(c, task, reason)
        c.execute("UPDATE tasks SET revision=revision+1, attempt=1, next_phase=?, status=?, assignee_id=NULL WHERE id=?", (status, status, task["id"]))
        self._invalidate_dependents(c, task, "upstream " + reason)

    def _invalidate_dependents(self, c, source, reason):
        """Version every transitive dependent so old downstream evidence is stale."""
        frontier, seen = [source["id"]], {source["id"]}
        project_tasks = c.execute("SELECT * FROM tasks WHERE project_id=?", (source["project_id"],)).fetchall()
        while frontier:
            upstream_id = frontier.pop(0)
            for dependent in project_tasks:
                if dependent["id"] in seen or upstream_id not in Store.loads(dependent["dependencies"]):
                    continue
                seen.add(dependent["id"])
                frontier.append(dependent["id"])
                self._invalidate(c, dependent, reason)
                c.execute("UPDATE tasks SET revision=revision+1, attempt=1, retry_count=0, next_phase='implementation', status='READY', assignee_id=NULL WHERE id=?", (dependent["id"],))
                self._event_add(c, "task.invalidated", dependent["project_id"], dependent["id"], None, {"reason": reason, "upstream_task_id": upstream_id})

    def _task(self, row, c=None):
        result = dict(row); result["requirements"] = Store.loads(result["requirements"]); result["dependencies"] = Store.loads(result["dependencies"]); result["inputs"] = Store.loads(result["inputs"])
        if c is None: return result | {"checks_passed": 0, "checks_total": len(PHASES)}
        counts = c.execute("SELECT COUNT(*) FROM runs WHERE task_id=? AND revision=? AND attempt=? AND status='PASS'", (result["id"], result["revision"], result["attempt"])).fetchone()[0]
        return result | {"checks_passed": counts, "checks_total": len(PHASES)}
    def _project(self, row): return dict(row)
    def _agent(self, row): return dict(row)
    def _run(self, row):
        result = dict(row); result["evidence"] = Store.loads(result.get("evidence")); return result
    def _event(self, row):
        result = dict(row); result["data"] = Store.loads(result["data"]); return result
    def _defect(self, row):
        result = dict(row); result["evidence"] = Store.loads(result["evidence"]); return result
    def _related(self, c, table, ids, convert, field="task_id"):
        if not ids: return []
        return [convert(row) for row in c.execute("SELECT * FROM " + table + " WHERE " + field + " IN (" + ",".join("?" * len(ids)) + ") ORDER BY created_at, id", ids)]
    def _one(self, c, table, ident): return c.execute("SELECT * FROM " + table + " WHERE id=?", (ident,)).fetchone()
    def _require(self, c, table, ident, label):
        self._text(ident, label + " id"); row = self._one(c, table, ident)
        if row is None: raise KeyError(label + " not found")
        return row
    def _task_project(self, c, task_id): return self._require(c, "tasks", task_id, "task")["project_id"]
    def _event_add(self, c, type_, project_id, task_id, run_id, data): c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)", (self._id("event"), type_, project_id, task_id, run_id, self._now(), Store.dumps(data)))
    @staticmethod
    def _validate_evidence(status, evidence):
        """Permit host evidence, but reject explicit failed command evidence for PASS."""
        if status != "PASS":
            return
        if "status" in evidence and evidence["status"] != "PASS":
            raise ValueError("PASS evidence has a contradictory status")
        if evidence.get("timed_out") is True or evidence.get("output_truncated") is True:
            raise ValueError("PASS evidence cannot be timed out or truncated")
        if evidence.get("start_error") or evidence.get("launch_error"):
            raise ValueError("PASS evidence cannot contain a launch error")
        if "exit_code" in evidence:
            exit_code = evidence["exit_code"]
            if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code != 0:
                raise ValueError("PASS command evidence requires integer exit_code 0")
    @staticmethod
    def _id(prefix): return prefix + "-" + uuid4().hex
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    @staticmethod
    def _text(value, field):
        if not isinstance(value, str) or not value.strip(): raise ValueError(field + " must be a non-empty string")
        return value.strip()
    @staticmethod
    def _role(value):
        value = Runtime._text(value, "role")
        if value not in ROLES: raise ValueError("unknown role")
        return value
