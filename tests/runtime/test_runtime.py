import tempfile
import threading
import unittest
from pathlib import Path

from rd_platform.runtime import Runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.temp_dir.name) / "state.db")
        self.project = self.runtime.execute("project.create", {"name": "demo", "idea": "deliver value"})
        self.runtime.execute("agent.register", {"id": "dev", "role": "developer"})
        self.runtime.execute("agent.register", {"id": "test", "role": "tester"})
        self.runtime.execute("agent.register", {"id": "review", "role": "reviewer"})

    def tearDown(self):
        self.temp_dir.cleanup()

    def task(self, **overrides):
        data = {"project_id": self.project["id"], "title": "task", "why": "required", "role": "developer",
                "requirements": ["REQ-V2-001"], "dependencies": [], "inputs": {"source": "test"}}
        data.update(overrides)
        return self.runtime.execute("task.create", data)

    def complete_until_review(self, task, include_implementation=True):
        phases = (("implementation", "dev"), ("unit", "test"), ("integration", "test"))
        if not include_implementation:
            phases = phases[1:]
        for phase, agent in phases:
            run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": agent, "phase": phase})
            self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": phase, "evidence": {"result": phase}})

    def test_request_id_is_idempotent_across_reopen(self):
        first = self.runtime.execute("project.create", {"name": "once", "idea": "same"}, request_id="once")
        second = Runtime(self.runtime.db_path).execute("project.create", {"name": "once", "idea": "same"}, request_id="once")
        self.assertEqual(first["id"], second["id"])
        with self.assertRaises(ValueError):
            self.runtime.execute("project.create", {"name": "changed", "idea": "same"}, request_id="once")

    def test_dependencies_must_exist_same_project_and_done(self):
        upstream = self.task(title="upstream")
        blocked = self.task(title="blocked", dependencies=[upstream["id"]])
        with self.assertRaises(ValueError):
            self.runtime.execute("run.start", {"task_id": blocked["id"], "agent_id": "dev", "phase": "implementation"})
        other = self.runtime.execute("project.create", {"name": "other", "idea": "other"})
        with self.assertRaises(ValueError):
            self.runtime.execute("task.create", {"project_id": other["id"], "title": "bad", "why": "bad", "role": "developer", "requirements": ["REQ"], "dependencies": [upstream["id"]], "inputs": {}})

    def test_developer_cannot_self_validate_and_only_review_completes_task(self):
        task = self.task()
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "implemented", "evidence": {"log": "ok"}})
        with self.assertRaises(ValueError):
            self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "unit"})
        self.complete_until_review(task, include_implementation=False)
        review = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "review", "phase": "review"})
        done = self.runtime.execute("run.finish", {"run_id": review["id"], "status": "PASS", "summary": "reviewed", "evidence": {"review": "pass"}})
        self.assertEqual("DONE", done["status"])
        self.assertEqual(4, done["checks_passed"])

    def test_failure_retry_requires_fresh_complete_chain_and_closes_defect(self):
        task = self.task()
        failed = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("run.finish", {"run_id": failed["id"], "status": "FAIL", "summary": "broken", "evidence": {"log": "failure"}})
        state = self.runtime.snapshot(self.project["id"])
        self.assertEqual("OPEN", state["defects"][0]["status"])
        retried = self.runtime.execute("task.control", {"task_id": task["id"], "action": "retry", "reason": "fix it"})
        self.assertEqual(2, retried["attempt"])
        self.complete_until_review(retried)
        review = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "review", "phase": "review"})
        self.runtime.execute("run.finish", {"run_id": review["id"], "status": "PASS", "summary": "fixed", "evidence": {"review": "ok"}})
        self.assertEqual("CLOSED", self.runtime.snapshot(self.project["id"])["defects"][0]["status"])

    def test_pause_and_modify_invalidate_late_run_and_reset_quality(self):
        task = self.task()
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("task.control", {"task_id": task["id"], "action": "pause", "reason": "wait"})
        with self.assertRaises(ValueError):
            self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "late", "evidence": {"x": 1}})
        self.runtime.execute("task.control", {"task_id": task["id"], "action": "resume", "reason": "go"})
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "one", "evidence": {"x": 1}})
        changed = self.runtime.execute("task.control", {"task_id": task["id"], "action": "modify", "reason": "new input", "inputs": {"version": 2}})
        self.assertEqual(2, changed["revision"])
        self.assertEqual(0, changed["checks_passed"])
        self.assertEqual("implementation", changed["next_phase"])

    def test_concurrent_start_has_only_one_active_run(self):
        task = self.task()
        errors, successes = [], []
        def start():
            try:
                successes.append(self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"}))
            except ValueError as error:
                errors.append(error)
        threads = [threading.Thread(target=start) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(1, len(successes))
        self.assertEqual(1, len(errors))

    def test_rejects_boolean_and_empty_required_values(self):
        with self.assertRaises(ValueError):
            self.runtime.execute("project.create", {"name": True, "idea": "x"})
        with self.assertRaises(ValueError):
            self.runtime.execute("agent.register", {"id": "", "role": "developer"})

    def test_snapshot_has_ordered_related_events_and_pause_invalidates_active_run(self):
        task = self.task()
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("project.control", {"project_id": self.project["id"], "action": "pause", "reason": "operator pause"})
        snapshot = self.runtime.snapshot(self.project["id"])
        self.assertTrue(snapshot["events"])
        self.assertTrue(all(event["project_id"] == self.project["id"] for event in snapshot["events"]))
        self.assertEqual(sorted(event["sequence"] for event in snapshot["events"]), [event["sequence"] for event in snapshot["events"]])
        self.assertEqual("INVALIDATED", next(item for item in snapshot["runs"] if item["id"] == run["id"])["status"])
        with self.assertRaises(ValueError):
            self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "late", "evidence": {"x": 1}})

    def test_snapshot_counts_only_current_revision_attempt_passes(self):
        task = self.task()
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "ok", "evidence": {"x": 1}})
        observed = self.runtime.snapshot(self.project["id"])["tasks"][0]
        self.assertEqual(1, observed["checks_passed"])

    def test_modify_invalidates_transitive_dependents(self):
        source = self.task(title="source")
        child = self.task(title="child", dependencies=[source["id"]])
        grandchild = self.task(title="grandchild", dependencies=[child["id"]])
        self.runtime.execute("task.control", {"task_id": source["id"], "action": "modify", "reason": "changed", "title": "source v2"})
        tasks = {item["id"]: item for item in self.runtime.snapshot(self.project["id"])["tasks"]}
        self.assertEqual(2, tasks[child["id"]]["revision"])
        self.assertEqual(2, tasks[grandchild["id"]]["revision"])

    def test_one_agent_cannot_run_two_tasks_and_reassignment_is_enforced(self):
        first, second = self.task(title="first"), self.task(title="second")
        self.runtime.execute("task.control", {"task_id": first["id"], "action": "reassign", "reason": "owner", "agent_id": "dev"})
        with self.assertRaises(ValueError):
            self.runtime.execute("run.start", {"task_id": first["id"], "agent_id": "test", "phase": "implementation"})
        self.runtime.execute("run.start", {"task_id": first["id"], "agent_id": "dev", "phase": "implementation"})
        with self.assertRaises(ValueError):
            self.runtime.execute("run.start", {"task_id": second["id"], "agent_id": "dev", "phase": "implementation"})
        with self.assertRaises(ValueError):
            self.runtime.execute("task.control", {"task_id": first["id"], "action": "reassign", "reason": "late", "agent_id": "dev"})

    def test_invalid_structured_values_raise_value_error_without_mutation(self):
        baseline = self.runtime.snapshot(self.project["id"])
        task = self.task(title="validation target")
        baseline = self.runtime.snapshot(self.project["id"])
        for command, data in (
            ("task.create", {"project_id": self.project["id"], "title": "x", "why": "x", "role": "developer", "requirements": ["REQ"], "dependencies": [{}], "inputs": {}}),
            ("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": {}}),
            ("task.control", {"task_id": task["id"], "action": {}, "reason": "x"}),
        ):
            with self.assertRaises(ValueError):
                self.runtime.execute(command, data)
        self.assertEqual(baseline, self.runtime.snapshot(self.project["id"]))

    def test_failed_task_cannot_pause_resume_to_bypass_retry(self):
        task = self.task()
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("run.finish", {"run_id": run["id"], "status": "FAIL", "summary": "bad", "evidence": {"x": 1}})
        with self.assertRaises(ValueError):
            self.runtime.execute("task.control", {"task_id": task["id"], "action": "pause", "reason": "bypass"})

    def test_reassignment_is_scoped_to_next_phase_and_clears_after_pass(self):
        task = self.task()
        self.runtime.execute("task.control", {"task_id": task["id"], "action": "reassign", "reason": "implementation owner", "agent_id": "dev"})
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "done", "evidence": {"result": "ok"}})
        unit = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "test", "phase": "unit"})
        self.assertEqual("unit", unit["phase"])

    def test_skip_invalidates_downstream_active_run_and_finish_rechecks_dependencies(self):
        upstream = self.task(title="upstream")
        downstream = self.task(title="downstream", dependencies=[upstream["id"]])
        self.complete_until_review(upstream)
        review = self.runtime.execute("run.start", {"task_id": upstream["id"], "agent_id": "review", "phase": "review"})
        self.runtime.execute("run.finish", {"run_id": review["id"], "status": "PASS", "summary": "done", "evidence": {"review": "ok"}})
        self.complete_until_review(downstream)
        down_run = self.runtime.execute("run.start", {"task_id": downstream["id"], "agent_id": "review", "phase": "review"})
        self.runtime.execute("task.control", {"task_id": upstream["id"], "action": "skip", "reason": "cancelled"})
        with self.assertRaises(ValueError):
            self.runtime.execute("run.finish", {"run_id": down_run["id"], "status": "PASS", "summary": "late", "evidence": {"result": "ok"}})

    def test_pass_rejects_explicit_failed_command_evidence(self):
        task = self.task()
        run = self.runtime.execute("run.start", {"task_id": task["id"], "agent_id": "dev", "phase": "implementation"})
        for evidence in (
            {"timed_out": True, "exit_code": None, "status": "FAIL"},
            {"exit_code": True},
            {"exit_code": 1},
            {"output_truncated": True, "exit_code": 0},
            {"start_error": "could not start", "exit_code": 0},
            {"argv": ["missing-command"], "cwd": ".", "exit_code": 0, "launch_error": "FileNotFoundError: failed", "timed_out": False, "output_truncated": False, "status": "PASS"},
        ):
            with self.assertRaises(ValueError):
                self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "invalid", "evidence": evidence})
        self.runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": "host review", "evidence": {"review": "pass"}})

    def test_nonfinite_nested_json_is_rejected_without_write(self):
        before = self.runtime.snapshot(self.project["id"])
        with self.assertRaises(ValueError):
            self.runtime.execute("task.create", {
                "project_id": self.project["id"], "title": "bad JSON", "why": "validation",
                "role": "developer", "requirements": ["REQ-V2-001"], "dependencies": [],
                "inputs": {"nested": [{"number": float("nan")}]},
            })
        self.assertEqual(before, self.runtime.snapshot(self.project["id"]))

    def test_deep_host_json_is_value_error_without_write(self):
        nested = {}
        for _ in range(5000):
            nested = {"next": nested}
        before = self.runtime.snapshot(self.project["id"])
        with self.assertRaises(ValueError):
            self.runtime.execute("task.create", {
                "project_id": self.project["id"], "title": "deep JSON", "why": "validation",
                "role": "developer", "requirements": ["REQ-V2-001"], "dependencies": [],
                "inputs": nested,
            })
        self.assertEqual(before, self.runtime.snapshot(self.project["id"]))


if __name__ == "__main__":
    unittest.main()
