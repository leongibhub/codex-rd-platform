import unittest
import tempfile
from pathlib import Path

from rd_platform.reporting import report
from rd_platform.runtime import Runtime


class ReportingTests(unittest.TestCase):
    def test_no_execution_is_not_a_pass_and_blocks_release(self):
        result = report(
            {
                "projects": [{"id": "project-1", "name": "demo", "idea": "x", "stage": "DEVELOPMENT"}],
                "tasks": [
                    {
                        "id": "task-1",
                        "project_id": "project-1",
                        "title": "Implement x",
                        "requirements": ["REQ-V2-008"],
                        "revision": 1,
                        "status": "READY",
                    }
                ],
                "runs": [],
                "defects": [],
                "agents": [],
                "events": [],
            }
        )

        self.assertEqual("NOT_EXECUTED", result["test_execution"]["status"])
        self.assertEqual(0, result["test_execution"]["executed"])
        self.assertEqual(1, result["test_execution"]["total"])
        self.assertEqual("DO_NOT_RELEASE", result["release_recommendation"]["status"])

    def test_failed_execution_blocks_release_and_is_counted(self):
        result = report(
            {
                "projects": [],
                "tasks": [{"id": "task-1", "project_id": "project-1", "requirements": ["REQ-1"], "revision": 1}],
                "runs": [
                    {
                        "id": "run-1",
                        "task_id": "task-1",
                        "phase": "unit",
                        "status": "FAIL",
                        "revision": 1,
                        "evidence": {"exit_code": 1},
                    }
                ],
                "defects": [
                    {"id": "BUG-1", "task_id": "task-1", "status": "OPEN"},
                    {"id": "BUG-2", "task_id": "task-1", "status": "RESOLVED"},
                ],
            }
        )

        self.assertEqual("FAIL", result["test_execution"]["status"])
        self.assertEqual(1, result["test_execution"]["failed"])
        self.assertEqual(2, result["defects"]["open"])
        self.assertEqual("DO_NOT_RELEASE", result["release_recommendation"]["status"])

    def test_previous_retry_evidence_cannot_pass_current_attempt(self):
        result = report(
            {
                "projects": [],
                "tasks": [{"id": "task-1", "project_id": "project-1", "requirements": ["REQ-1"], "revision": 1, "attempt": 2}],
                "runs": [
                    {
                        "id": "old-pass",
                        "task_id": "task-1",
                        "phase": "unit",
                        "status": "PASS",
                        "revision": 1,
                        "attempt": 1,
                        "evidence": {"exit_code": 0},
                    }
                ],
                "defects": [],
            }
        )

        self.assertEqual("NOT_EXECUTED", result["test_execution"]["status"])
        self.assertEqual(0, result["test_execution"]["passed"])
        self.assertEqual("NO_RELEASE_EVIDENCE", result["release_recommendation"]["status"])

    def test_passed_tests_without_final_review_do_not_recommend_release(self):
        result = report(
            {
                "projects": [],
                "tasks": [
                    {
                        "id": "task-1",
                        "project_id": "project-1",
                        "requirements": ["REQ-1"],
                        "revision": 1,
                        "attempt": 1,
                        "status": "READY",
                    }
                ],
                "runs": [
                    {"task_id": "task-1", "phase": "unit", "status": "PASS", "revision": 1, "attempt": 1, "evidence": {"exit_code": 0}},
                    {"task_id": "task-1", "phase": "integration", "status": "PASS", "revision": 1, "attempt": 1, "evidence": {"exit_code": 0}},
                ],
                "defects": [],
            }
        )

        self.assertEqual("PASS", result["test_execution"]["status"])
        self.assertEqual("DO_NOT_RELEASE", result["release_recommendation"]["status"])

    def test_blocked_and_skipped_are_not_executed_module_tests(self):
        result = report(
            {
                "projects": [],
                "tasks": [
                    {"id": "blocked", "project_id": "p", "requirements": [], "revision": 1, "attempt": 1},
                    {"id": "skipped", "project_id": "p", "requirements": [], "revision": 1, "attempt": 1},
                ],
                "runs": [
                    {"task_id": "blocked", "phase": "unit", "status": "BLOCKED", "revision": 1, "attempt": 1, "evidence": {}},
                    {"task_id": "skipped", "phase": "unit", "status": "SKIPPED", "revision": 1, "attempt": 1, "evidence": {}},
                ],
                "defects": [],
            }
        )

        self.assertEqual(0, result["test_execution"]["executed"])
        self.assertEqual(2, result["test_execution"]["total"])
        self.assertEqual("task", result["test_execution"]["denominator"])
        self.assertEqual("unit", result["test_execution"]["scope"])

    def test_runtime_snapshot_only_establishes_module_quality_not_release_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory) / "state.db")
            project = runtime.execute("project.create", {"name": "demo", "idea": "demo"})
            runtime.execute("agent.register", {"id": "developer", "role": "developer"})
            runtime.execute("agent.register", {"id": "tester", "role": "tester"})
            runtime.execute("agent.register", {"id": "reviewer", "role": "reviewer"})
            task = runtime.execute(
                "task.create",
                {
                    "project_id": project["id"], "title": "deliver", "why": "required",
                    "role": "developer", "requirements": ["REQ-1"], "dependencies": [], "inputs": {},
                },
            )
            for phase, agent_id in (("implementation", "developer"), ("unit", "tester"), ("integration", "tester"), ("review", "reviewer")):
                run = runtime.execute("run.start", {"task_id": task["id"], "agent_id": agent_id, "phase": phase})
                runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": phase, "evidence": {"exit_code": 0}})

            result = report(runtime.snapshot(project["id"]))

        self.assertEqual("PASS", result["test_execution"]["status"])
        self.assertEqual("PASS", result["module_quality"]["status"])
        self.assertEqual("PARTIAL", result["traceability"]["status"])
        self.assertEqual("MODULE_QUALITY", result["report_scope"])
        self.assertEqual("NOT_EXECUTED", result["human_acceptance"])
        self.assertEqual("NOT_EXECUTED", result["deployment"])
        self.assertEqual("NO_RELEASE_EVIDENCE", result["release_recommendation"]["status"])

    def test_skipped_current_runtime_task_cannot_inherit_prior_module_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory) / "state.db")
            project = runtime.execute("project.create", {"name": "demo", "idea": "demo"})
            runtime.execute("agent.register", {"id": "developer", "role": "developer"})
            runtime.execute("agent.register", {"id": "tester", "role": "tester"})
            task = runtime.execute(
                "task.create",
                {"project_id": project["id"], "title": "deliver", "why": "required", "role": "developer", "requirements": ["REQ-1"], "dependencies": [], "inputs": {}},
            )
            for phase, agent_id in (("implementation", "developer"), ("unit", "tester"), ("integration", "tester")):
                run = runtime.execute("run.start", {"task_id": task["id"], "agent_id": agent_id, "phase": phase})
                runtime.execute("run.finish", {"run_id": run["id"], "status": "PASS", "summary": phase, "evidence": {"exit_code": 0}})
            runtime.execute("task.control", {"task_id": task["id"], "action": "skip", "reason": "not proceeding"})

            result = report(runtime.snapshot(project["id"]))

        self.assertEqual("SKIPPED", result["test_execution"]["results"][0]["status"])
        self.assertEqual("NOT_EXECUTED", result["test_execution"]["status"])
        self.assertEqual(0, result["test_execution"]["passed"])


if __name__ == "__main__":
    unittest.main()
