"""Independent black-box checks for CR-V3-003 execution endpoints.

These tests derive from REQ-V3-016..020 and use a temporary Runtime database,
real local subprocesses, and a real loopback HTTP server.  They intentionally
do not reuse developer test helpers or call private worker functions.
"""
from __future__ import annotations

import ast
import hashlib
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from unittest.mock import patch

from rd_platform.runtime import Runtime
from rd_platform.store import Store


class ExecutionEndpointIndependentTests(unittest.TestCase):
    """TC-V3-IND-901..906: worker, projection, and HTTP control boundary."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-execution-")
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        self.runtime = Runtime(Path(self.temp.name) / "state.db")
        self.project = self.runtime.execute("project.create", {
            "name": "independent execution fixture", "idea": "temporary black-box test",
        })["id"]
        self.runtime.execute("lifecycle.initialize", {
            "project_id": self.project, "repository_root": str(self.root), "mode": "active",
        })
        for agent in ("ind-worker-a", "ind-worker-b"):
            self.runtime.execute("agent.register", {"id": agent, "role": "developer"})
        self.runtime.execute("agent.register", {"id": "ind-worker-test", "role": "tester"})

    def tearDown(self):
        self.temp.cleanup()

    def work(self, *, minimum=1, role="developer", dependencies=None, input_refs=None, required_types=None):
        return self.runtime.execute("work.create", {
            "project_id": self.project, "gate_id": "G0", "activity": "independent execution",
            "required_role": role, "why": "verify bounded external execution",
            "input_refs": input_refs or [], "dependencies": dependencies or [],
            "output_contract": {"required_types": ["DOC"] if required_types is None else required_types, "min_outputs": minimum},
        })

    def config(self, agent, argv, *, output=4096, timeout=10):
        return {
            "project_id": self.project, "repository_root": str(self.root), "poll_interval_seconds": 0.05,
            "workers": [{
                "agent_id": agent, "role": "developer", "backend": {"type": "argv", "argv": argv},
                "lease_seconds": 30, "timeout_seconds": timeout, "max_output_bytes": output,
            }],
        }

    def envelope_script(self, *, delay=0):
        artifact = self.root / "worker-result.md"
        artifact.write_text("independent observable output\n", encoding="utf-8")
        envelope = {
            "status": "DONE", "summary": "independent bounded command completed", "output_refs": [],
            "artifacts": [{
                "id": "DOC-IND-EXEC-001", "type": "DOC", "title": "Independent worker output",
                "relative_path": artifact.name, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }],
        }
        script = self.root / "emit-envelope.py"
        script.write_text(
            "import json, time\n" + (f"time.sleep({delay!r})\n" if delay else "") +
            "print(json.dumps(" + repr(envelope) + "))\n", encoding="utf-8",
        )
        return [sys.executable, str(script)]

    def test_competing_services_claim_once_and_publish_observable_artifact(self):
        """TC-V3-IND-901 / REQ-V3-016: two services cannot duplicate one work item."""
        self.work()
        from rd_platform.worker_service import run_service

        barrier = threading.Barrier(3)
        results = []

        def invoke(agent):
            barrier.wait()
            instance = Runtime(self.runtime.db_path)
            results.append(run_service(instance, self.config(agent, self.envelope_script(delay=.2)), once=True))

        threads = [threading.Thread(target=invoke, args=(agent,)) for agent in ("ind-worker-a", "ind-worker-b")]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(10)
            self.assertFalse(thread.is_alive(), "competing worker did not finish")

        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual(1, sum(result["claimed"] for result in results))
        self.assertEqual(1, sum(result["completed"] for result in results))
        self.assertEqual("DONE", snapshot["work_orders"][0]["status"])
        self.assertEqual(1, len(snapshot["artifacts"]))
        self.assertEqual("DOC-IND-EXEC-001", snapshot["artifacts"][0]["id"])

    def test_pause_cancels_owned_process_and_late_output_is_not_registered(self):
        """TC-V3-IND-902 / REQ-V3-016: lifecycle pause fences a live child process."""
        self.work()
        started = self.root / "started"
        late = self.root / "late.md"
        script = self.root / "slow-worker.py"
        script.write_text(
            "from pathlib import Path\nimport time\n"
            f"Path({str(started)!r}).write_text('started')\n"
            "time.sleep(10)\n"
            f"Path({str(late)!r}).write_text('late')\n"
            "print('{\"status\":\"DONE\",\"summary\":\"late\",\"output_refs\":[],\"artifacts\":[]}')\n",
            encoding="utf-8",
        )
        from rd_platform.worker_service import run_service

        result_box = {}
        service = threading.Thread(target=lambda: result_box.setdefault(
            "result", run_service(self.runtime, self.config("ind-worker-a", [sys.executable, str(script)]), once=True),
        ))
        service.start()
        deadline = time.monotonic() + 5
        while not started.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(started.exists(), "test subprocess never started")
        active = self.runtime.snapshot(self.project)["agents"]
        worker = next(row for row in active if row["id"] == "ind-worker-a")
        self.assertEqual("WORKING", worker["effective_status"])
        self.assertIsNotNone(worker["current_work"])
        self.assertIn("lease_until", worker["current_work"])
        self.runtime.execute("lifecycle.control", {
            "project_id": self.project, "action": "pause", "reason": "independent cancellation test",
        })
        service.join(10)
        self.assertFalse(service.is_alive(), "paused worker process was not cancelled")
        self.assertEqual(1, result_box["result"]["cancelled"])
        self.assertFalse(late.exists(), "late child output survived pause cancellation")
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual([], snapshot["artifacts"])
        self.assertNotEqual("DONE", snapshot["work_orders"][0]["status"])

    def test_restart_reaps_unknown_lease_only_on_safe_retry_and_pause_resume_services_do_not_duplicate_argv(self):
        """TC-V3-IND-906: unknown external attempts require an explicit safe retry."""
        from rd_platform.worker_service import run_service

        def plain_envelope_script(name, *, append_to=None, delay=0):
            script = self.root / f"{name}.py"
            writes = ""
            if append_to:
                writes = f"Path({str(append_to)!r}).open('a', encoding='utf-8').write('argv\\n')\n"
            script.write_text(
                "from pathlib import Path\nimport json, time\n" + writes +
                (f"time.sleep({delay!r})\n" if delay else "") +
                "print(json.dumps({'status':'DONE','summary':'safe retry observable','output_refs':[],'artifacts':[]}))\n",
                encoding="utf-8",
            )
            return [sys.executable, str(script)]

        def service_config(agent, argv, *, safe=False):
            configured = self.config(agent, argv)
            configured["workers"][0]["safe_to_retry"] = safe
            return configured

        # First, an expired lease is a durable "unknown external effect" fence.
        expired = self.work(minimum=0, required_types=[])
        self.runtime.execute("work.claim", {"work_order_id": expired["id"], "agent_id": "ind-worker-a", "lease_seconds": 1})
        with patch("rd_platform.lifecycle_base.LifecycleBase.now", return_value="2099-01-01T00:00:00+00:00"):
            self.assertEqual([expired["id"]], self.runtime.execute("work.reap", {"project_id": self.project})["expired"])
        expired_marker = self.root / "expired-argv.txt"
        unsafe = run_service(Runtime(self.runtime.db_path), service_config("ind-worker-b", plain_envelope_script("expired", append_to=expired_marker), safe=False), once=True)
        self.assertEqual((0, 1), (unsafe["claimed"], unsafe["recovery_skipped"]))
        self.assertFalse(expired_marker.exists(), "unsafe lease recovery must not re-run argv")
        safe = run_service(Runtime(self.runtime.db_path), service_config("ind-worker-b", plain_envelope_script("expired-safe", append_to=expired_marker), safe=True), once=True)
        self.assertEqual((1, 1), (safe["claimed"], safe["completed"]), safe)
        self.assertEqual("argv\n", expired_marker.read_text(encoding="utf-8"))

        # A prior expiry no longer blocks an ordinary retry after a later safe claim.
        retryable = self.work(minimum=0, required_types=[])
        self.runtime.execute("work.claim", {"work_order_id": retryable["id"], "agent_id": "ind-worker-a", "lease_seconds": 1})
        with patch("rd_platform.lifecycle_base.LifecycleBase.now", return_value="2099-01-01T00:00:00+00:00"):
            self.runtime.execute("work.reap", {"project_id": self.project})
        broken = self.root / "broken-safe.py"; broken.write_text("print('not an envelope')\n", encoding="utf-8")
        failed_safe = run_service(Runtime(self.runtime.db_path), service_config("ind-worker-b", [sys.executable, str(broken)], safe=True), once=True)
        self.assertEqual(1, failed_safe["failed"])
        self.runtime.execute("work.control", {"work_order_id": retryable["id"], "action": "retry", "reason": "independent safe retry recovery"})
        retried_marker = self.root / "retried-argv.txt"
        ordinary_retry = run_service(Runtime(self.runtime.db_path), service_config("ind-worker-a", plain_envelope_script("ordinary-retry", append_to=retried_marker), safe=False), once=True)
        self.assertEqual((1, 1), (ordinary_retry["claimed"], ordinary_retry["completed"]))
        self.assertEqual("argv\n", retried_marker.read_text(encoding="utf-8"))

        # Pause/resume is another unknown-effect fence.  Two services may resume
        # it with an explicit safe policy, but exactly one may launch argv.
        paused = self.work(minimum=0, required_types=[])
        self.runtime.execute("work.claim", {"work_order_id": paused["id"], "agent_id": "ind-worker-a", "lease_seconds": 30})
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "pause", "reason": "independent pause/restart test"})
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "resume", "reason": "independent pause/restart test"})
        side_effect = self.root / "resumed-argv.txt"
        shared = service_config("ind-worker-a", plain_envelope_script("resumed", append_to=side_effect, delay=.2), safe=True)
        other = dict(shared["workers"][0]); other["agent_id"] = "ind-worker-b"
        shared["workers"].append(other); shared["max_concurrency"] = 2
        barrier, outcomes = threading.Barrier(3), []
        def invoke():
            barrier.wait()
            outcomes.append(run_service(Runtime(self.runtime.db_path), shared, once=True))
        first, second = threading.Thread(target=invoke), threading.Thread(target=invoke)
        first.start(); second.start(); barrier.wait(); first.join(10); second.join(10)
        self.assertFalse(first.is_alive()); self.assertFalse(second.is_alive())
        self.assertEqual(1, sum(item["claimed"] for item in outcomes))
        self.assertEqual(1, sum(item["completed"] for item in outcomes))
        self.assertEqual("argv\n", side_effect.read_text(encoding="utf-8"), "second service must not duplicate argv side effect")

    def test_claim_version_and_reassign_unknown_attempt_are_atomic_fences(self):
        """TC-V3-IND-936: stale snapshots and reassign cannot replay unknown argv."""
        from rd_platform.worker_service import run_service

        versioned = self.work(minimum=0, required_types=[])
        version = versioned["version"]
        self.runtime.execute("work.claim", {"work_order_id": versioned["id"], "agent_id": "ind-worker-a", "lease_seconds": 30})
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "pause", "reason": "independent stale snapshot test"})
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "resume", "reason": "independent stale snapshot test"})
        with self.assertRaisesRegex(ValueError, "version changed"):
            self.runtime.execute("work.claim", {"work_order_id": versioned["id"], "agent_id": "ind-worker-b", "lease_seconds": 30, "expected_version": version, "safe_to_retry": True})
        latest = next(row for row in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if row["id"] == versioned["id"])
        with self.assertRaisesRegex(ValueError, "safe_to_retry"):
            self.runtime.execute("work.claim", {"work_order_id": versioned["id"], "agent_id": "ind-worker-b", "lease_seconds": 30, "expected_version": latest["version"]})
        safe = self.runtime.execute("work.claim", {"work_order_id": versioned["id"], "agent_id": "ind-worker-b", "lease_seconds": 30, "expected_version": latest["version"], "safe_to_retry": True})
        self.runtime.execute("work.finish", {"work_order_id": versioned["id"], "agent_id": "ind-worker-b", "lease_token": safe["lease_token"], "status": "DONE", "summary": "explicit safe retry", "output_refs": []})

        reassigned = self.work(minimum=0, required_types=[])
        marker = self.root / "reassign-argv.txt"
        script = self.root / "reassign-slow.py"
        script.write_text(
            "from pathlib import Path\nimport json, time\n" +
            f"Path({str(marker)!r}).open('a', encoding='utf-8').write('argv\\n')\n" +
            "time.sleep(2)\nprint(json.dumps({'status':'DONE','summary':'slow','output_refs':[],'artifacts':[]}))\n",
            encoding="utf-8",
        )
        first_result = {}
        first = threading.Thread(target=lambda: first_result.setdefault("value", run_service(
            self.runtime, self.config("ind-worker-a", [sys.executable, str(script)]), once=True)),
        )
        first.start()
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(marker.exists(), "first argv never began")
        self.runtime.execute("work.control", {"work_order_id": reassigned["id"], "action": "reassign", "agent_id": "ind-worker-b", "reason": "independent unknown external attempt"})
        denied = run_service(Runtime(self.runtime.db_path), self.config("ind-worker-b", [sys.executable, str(script)]), once=True)
        self.assertEqual((0, 1), (denied["claimed"], denied["recovery_skipped"]))
        self.assertEqual("argv\n", marker.read_text(encoding="utf-8"), "reassign fence must prevent duplicate argv")
        first.join(8)
        self.assertFalse(first.is_alive(), "first service did not reconcile invalidated claim")
        safe_config = self.config("ind-worker-b", [sys.executable, str(script)])
        safe_config["workers"][0]["safe_to_retry"] = True
        allowed = run_service(Runtime(self.runtime.db_path), safe_config, once=True)
        self.assertEqual((1, 1), (allowed["claimed"], allowed["completed"]))
        self.assertEqual("argv\nargv\n", marker.read_text(encoding="utf-8"))

    def test_rollback_refuses_claimed_pause_or_expiry_unknown_attempt_without_compensation(self):
        """TC-V3-IND-938: rollback never masks an unreconciled external attempt."""
        def assert_rejected(work):
            before = self.runtime.lifecycle_snapshot(self.project)["work_orders"]
            with self.assertRaisesRegex(ValueError, "reconcile original external outcome"):
                self.runtime.execute("work.control", {"work_order_id": work["id"], "action": "rollback", "reason": "independent unknown attempt"})
            after = self.runtime.lifecycle_snapshot(self.project)["work_orders"]
            self.assertEqual(len(before), len(after), "rejected rollback must not create compensation")
            self.assertIsNone(next(row for row in after if row["id"] == work["id"]).get("compensation_work_id"))

        claimed = self.work(minimum=0, required_types=[])
        self.runtime.execute("work.claim", {"work_order_id": claimed["id"], "agent_id": "ind-worker-a", "lease_seconds": 30})
        assert_rejected(claimed)

        paused = self.work(minimum=0, required_types=[])
        self.runtime.execute("work.claim", {"work_order_id": paused["id"], "agent_id": "ind-worker-b", "lease_seconds": 30})
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "pause", "reason": "independent rollback pause"})
        self.runtime.execute("lifecycle.control", {"project_id": self.project, "action": "resume", "reason": "independent rollback resume"})
        assert_rejected(paused)

        expired = self.work(minimum=0, required_types=[])
        self.runtime.execute("work.claim", {"work_order_id": expired["id"], "agent_id": "ind-worker-b", "lease_seconds": 1})
        with patch("rd_platform.lifecycle_base.LifecycleBase.now", return_value="2099-01-01T00:00:00+00:00"):
            self.runtime.execute("work.reap", {"project_id": self.project})
        assert_rejected(expired)

        completed = self.work(minimum=0, required_types=[])
        claim = self.runtime.execute("work.claim", {"work_order_id": completed["id"], "agent_id": "ind-worker-b", "lease_seconds": 30})
        self.runtime.execute("work.finish", {"work_order_id": completed["id"], "agent_id": "ind-worker-b", "lease_token": claim["lease_token"], "status": "DONE", "summary": "completed before compensation", "output_refs": []})
        rolled = self.runtime.execute("work.control", {"work_order_id": completed["id"], "action": "rollback", "reason": "completed compensation is allowed"})
        records = {row["id"]: row for row in self.runtime.lifecycle_snapshot(self.project)["work_orders"]}
        self.assertEqual("ROLLBACK_PENDING", records[completed["id"]]["status"])
        self.assertEqual("READY", records[rolled["compensation_work_id"]]["status"])

    def test_artifact_trace_invalidation_is_canonical_and_lifecycle_rollback_fails_closed(self):
        """TC-V3-IND-939 / REQ-V3-016: changed inputs fence claims and rollback is atomic."""
        def ref(kind, ident, version=1):
            return {"type": kind, "id": ident, "version": version}

        def artifact(ident, kind):
            return self.runtime.execute("artifact.create", {
                "project_id": self.project, "artifact_id": ident, "artifact_type": kind,
                "title": ident, "state": "BASELINED",
                "content_ref": {"inline_json": {"independent": ident}},
                "source": {"kind": "host", "actor": "ind-worker-a"},
            })

        artifact("REQ-IND-939", "REQ")
        artifact("CR-IND-939", "CR")
        artifact_work = self.work(minimum=0, required_types=[], input_refs=[ref("REQ", "REQ-IND-939")])
        self.runtime.execute("work.claim", {"work_order_id": artifact_work["id"], "agent_id": "ind-worker-a", "lease_seconds": 30})
        self.runtime.execute("artifact.revise", {
            "artifact_id": "REQ-IND-939", "expected_version": 1, "state": "BASELINED",
            "content_ref": {"inline_json": {"independent": "revised"}}, "material": True,
            "reason": "independent active-input invalidation", "change_id": "CR-IND-939",
        })
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        fenced = next(row for row in snapshot["work_orders"] if row["id"] == artifact_work["id"])
        event = next(item for item in snapshot["events"] if item["type"] == "work.invalidated" and item["entity_id"] == artifact_work["id"])
        self.assertEqual("REVIEW_REQUIRED", fenced["status"])
        self.assertIs(event["data"]["external_process_cancelled"], False)
        self.runtime.execute("work.control", {"work_order_id": artifact_work["id"], "action": "modify", "reason": "use current ref", "input_refs": [ref("REQ", "REQ-IND-939", 2)]})
        with self.assertRaisesRegex(ValueError, "safe_to_retry"):
            self.runtime.execute("work.claim", {"work_order_id": artifact_work["id"], "agent_id": "ind-worker-b", "lease_seconds": 30})

        artifact("REQ-TRACE-939", "REQ")
        artifact("DES-TRACE-939", "DES")
        trace = self.runtime.execute("trace.link", {
            "project_id": self.project, "from": ref("REQ", "REQ-TRACE-939"),
            "to": ref("DES", "DES-TRACE-939"), "relation": "realized_by",
        })
        trace_work = self.work(minimum=0, required_types=[], input_refs=[ref("DES", "DES-TRACE-939")])
        self.runtime.execute("work.claim", {"work_order_id": trace_work["id"], "agent_id": "ind-worker-b", "lease_seconds": 30})
        self.runtime.execute("trace.invalidate", {"link_id": trace["id"], "reason": "independent trace invalidation", "change_id": "CR-IND-939"})
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        trace_event = next(item for item in snapshot["events"] if item["type"] == "work.invalidated" and item["entity_id"] == trace_work["id"])
        self.assertIs(trace_event["data"]["external_process_cancelled"], False)
        self.assertEqual("REVIEW_REQUIRED", next(row for row in snapshot["work_orders"] if row["id"] == trace_work["id"])["status"])

        # Move only G0 through its public evidence/assessment/decision protocol,
        # then verify a rollback touching an active input performs no partial
        # gate reset or compensation-work creation.
        self.runtime.execute("agent.register", {"id": "ind-review-939", "role": "reviewer"})
        artifact("DOC-G0-939", "DOC")
        from rd_platform.lifecycle_governance import POLICY
        evidence = self.runtime.execute("evidence.register", {
            "project_id": self.project, "kind": "document", "status": "VERIFIED",
            "source": {"kind": "host", "actor": "ind-review-939"},
            "locator": {"inline_json": {"fixture": "independent rollback boundary"}},
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"gate_id": "G0", "criteria": list(POLICY["G0"]), "artifact_refs": [ref("DOC", "DOC-G0-939")]},
        })
        assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": "G0"})
        self.assertEqual("PASS", assessment["candidate"], assessment)
        decision = self.runtime.execute("evidence.register", {
            "project_id": self.project, "kind": "gate_decision", "status": "VERIFIED",
            "source": {"kind": "host", "actor": "ind-review-939"},
            "locator": {"inline_json": {"fixture": "independent gate decision"}},
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"assessment_id": assessment["id"], "status": "PASS"},
        })
        self.runtime.execute("gate.decide", {"assessment_id": assessment["id"], "status": "PASS", "decided_by": "ind-review-939", "decision_evidence_refs": [ref("EVIDENCE", decision["id"])]})
        active = self.work(minimum=0, required_types=[], input_refs=[ref("DOC", "DOC-G0-939")])
        self.runtime.execute("work.claim", {"work_order_id": active["id"], "agent_id": "ind-worker-a", "lease_seconds": 30})
        before = self.runtime.lifecycle_snapshot(self.project)
        with self.assertRaisesRegex(ValueError, "reconcile original external outcome"):
            self.runtime.execute("lifecycle.control", {
                "project_id": self.project, "action": "rollback", "target_gate": "G0",
                "change_id": "CR-IND-939", "affected_refs": [ref("DOC", "DOC-G0-939")],
                "reason": "independent claimed-input rollback",
            })
        after = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual(before["lifecycle"]["current_gate"], after["lifecycle"]["current_gate"])
        self.assertEqual(len(before["work_orders"]), len(after["work_orders"]), "rejected lifecycle rollback must not create compensation")
        self.assertEqual("CLAIMED", next(row for row in after["work_orders"] if row["id"] == active["id"])["status"])

    def test_empty_invalid_and_over_budget_output_do_not_complete_work(self):
        """TC-V3-IND-903 / REQ-V3-016: exit 0 is not output-contract evidence."""
        from rd_platform.worker_service import run_service
        for name, source, budget in (
            ("empty", "print('')", 4096),
            ("invalid", "print('not an execution envelope')", 4096),
            ("over-budget", "print('x' * 2048)", 128),
        ):
            with self.subTest(name=name):
                work = self.work()
                script = self.root / f"{name}.py"
                script.write_text(source + "\n", encoding="utf-8")
                result = run_service(self.runtime, self.config("ind-worker-a", [sys.executable, str(script)], output=budget), once=True)
                record = next(item for item in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if item["id"] == work["id"])
                self.assertEqual(1, result["failed"])
                self.assertEqual("FAILED", record["status"])
        self.assertEqual([], self.runtime.lifecycle_snapshot(self.project)["artifacts"])

    def test_loopback_http_rejects_execution_and_approval_commands(self):
        """TC-V3-IND-904 / REQ-V3-020: HTTP cannot become anonymous argv or approval surface."""
        from rd_platform.web import create_server
        server = create_server(Path(self.temp.name) / "http-state.db", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for command in ("work.claim", "worker.run", "deployment.execute", "approval.submit"):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                body = json.dumps({"command": command, "data": {"argv": [sys.executable, "-c", "raise SystemExit(0)"]}})
                connection.request("POST", "/api/commands", body=body, headers={
                    "Host": f"127.0.0.1:{server.server_port}", "Content-Type": "application/json",
                    "Origin": f"http://127.0.0.1:{server.server_port}",
                })
                response = connection.getresponse()
                payload = json.loads(response.read())
                connection.close()
                self.assertEqual(403, response.status)
                self.assertIn("not available", payload["error"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)

    def test_empty_service_remains_available_until_explicit_stop(self):
        """TC-V3-IND-913 / REQ-V3-016: an empty queue is not terminal service completion."""
        from rd_platform.worker_service import run_service
        stopped = threading.Event()
        result = {}
        service = threading.Thread(target=lambda: result.setdefault(
            "value", run_service(self.runtime, self.config("ind-worker-a", [sys.executable, "-c", "pass"]), stop_event=stopped),
        ))
        service.start()
        time.sleep(.25)
        self.assertTrue(service.is_alive(), "empty queue incorrectly terminated the persistent service")
        stopped.set()
        service.join(5)
        self.assertFalse(service.is_alive())
        self.assertEqual({"claimed": 0, "status": "STOPPED"}, {key: result["value"][key] for key in ("claimed", "status")})

    def test_concurrency_one_still_scans_a_later_eligible_role_worker(self):
        """TC-V3-IND-914 / REQ-V3-016: max=1 limits slots, not eligible worker lookup."""
        target = self.work(role="developer")
        from rd_platform.worker_service import run_service
        config = self.config("ind-worker-test", [sys.executable, "-c", "raise SystemExit(31)"])
        config["workers"][0]["role"] = "tester"
        config["workers"].append({
            "agent_id": "ind-worker-a", "role": "developer", "backend": {"type": "argv", "argv": self.envelope_script()},
            "lease_seconds": 30, "timeout_seconds": 5, "max_output_bytes": 4096,
        })
        config["max_concurrency"] = 1
        result = run_service(self.runtime, config, once=True)
        records = {item["id"]: item for item in self.runtime.lifecycle_snapshot(self.project, limit=500)["work_orders"]}
        self.assertEqual(1, result["claimed"])
        self.assertEqual(1, result["completed"], result)
        self.assertEqual("DONE", records[target["id"]]["status"])

    def test_ready_work_beyond_first_200_is_dispatched(self):
        """TC-V3-IND-919 / REQ-V3-016: service reads every public work-order page."""
        for _ in range(205):
            self.work(role="tester")
        target = self.work(role="developer")
        from rd_platform.worker_service import run_service
        result = run_service(self.runtime, self.config("ind-worker-a", self.envelope_script()), once=True)
        records = {item["id"]: item for item in self.runtime.lifecycle_collection(self.project, "work_orders", limit=500)["items"]}
        self.assertEqual(1, result["completed"], result)
        self.assertEqual("DONE", records[target["id"]]["status"])

    def test_second_invalid_artifact_rolls_back_all_artifact_registration(self):
        """TC-V3-IND-915 / REQ-V3-016: an all-or-nothing output declaration is durable."""
        self.work()
        good = self.root / "good.md"; bad = self.root / "bad.md"
        good.write_text("good", encoding="utf-8"); bad.write_text("bad", encoding="utf-8")
        envelope = {"status": "DONE", "summary": "two artifacts", "output_refs": [], "artifacts": [
            {"id": "DOC-IND-ATOMIC-001", "type": "DOC", "title": "first", "relative_path": good.name, "sha256": hashlib.sha256(good.read_bytes()).hexdigest()},
            {"id": "DOC-IND-ATOMIC-002", "type": "DOC", "title": "second", "relative_path": bad.name, "sha256": "0" * 64},
        ]}
        script = self.root / "atomic.py"; script.write_text("import json\nprint(json.dumps(" + repr(envelope) + "))\n", encoding="utf-8")
        from rd_platform.worker_service import run_service
        result = run_service(self.runtime, self.config("ind-worker-a", [sys.executable, str(script)]), once=True)
        snapshot = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual(1, result["failed"])
        self.assertEqual([], snapshot["artifacts"])
        self.assertEqual("FAILED", snapshot["work_orders"][0]["status"])

    def test_stale_dependency_reference_never_reaches_responses_context(self):
        """TC-V3-IND-916 / CR-V3-004: revised dependency outputs cannot call Responses."""
        artifact = self.runtime.execute("artifact.create", {
            "project_id": self.project, "artifact_type": "DOC", "artifact_id": "DOC-IND-CONTEXT",
            "title": "old context", "state": "BASELINED", "content_ref": {"inline_json": {"revision": 1}},
            "source": {"kind": "host", "actor": "ind-worker-a"},
        })
        predecessor = self.work(minimum=0)
        claim = self.runtime.execute("work.claim", {"work_order_id": predecessor["id"], "agent_id": "ind-worker-a", "lease_seconds": 30})
        self.runtime.execute("work.finish", {"work_order_id": predecessor["id"], "agent_id": "ind-worker-a", "lease_token": claim["lease_token"],
                                              "status": "DONE", "summary": "old output", "output_refs": [{"type": "DOC", "id": artifact["id"], "version": 1}]})
        self.runtime.execute("artifact.revise", {"artifact_id": artifact["id"], "expected_version": 1, "state": "BASELINED",
                                                  "content_ref": {"inline_json": {"revision": 2}}, "reason": "independent stale-context test", "material": False})
        dependent = self.work(dependencies=[predecessor["id"]])
        from rd_platform.worker_service import run_service
        config = self.config("ind-worker-a", [sys.executable, "-c", "raise SystemExit(87)"])
        config["workers"][0]["backend"] = {
            "type": "responses", "model": "fixture-model", "api_key_env": "INTENTIONALLY_UNSET_TEST_KEY",
            "endpoint": "https://api.openai.com/v1/responses", "max_output_tokens": 64,
        }
        result = run_service(self.runtime, config, once=True)
        state = next(item for item in self.runtime.lifecycle_snapshot(self.project)["work_orders"] if item["id"] == dependent["id"])
        self.assertEqual(1, result["failed"], "stale context must result in a durable refusal")
        self.assertIn(state["status"], {"FAILED", "REJECTED"}, "stale context must not leave a work lease CLAIMED")

    def test_codex_backend_is_rejected_before_any_unsafe_argv_is_constructed(self):
        """TC-V3-IND-920 / CR-V3-004: unsafe Codex execution has no compatibility fallback."""
        from rd_platform.worker_backends import validate_backend
        with self.assertRaisesRegex(ValueError, "not production-safe"):
            validate_backend({"type": "codex", "prompt": "must never execute", "approval_mode": "auto-review", "executable": sys.executable},
                             repository_root=self.root, control_db=self.runtime.db_path)

    def test_responses_schema_and_host_cas_update_are_executable(self):
        """TC-V3-IND-926 / CR-V3-004: strict model schema can request a host CAS update."""
        from rd_platform.proposal_backend import response_schema
        from rd_platform.worker_service import run_service
        source = self.root / "allowed.py"; source.write_text("old = 1\n", encoding="utf-8")
        properties = response_schema()["properties"]["proposals"]["items"]["properties"]
        self.assertTrue({"action", "expected_sha256"}.issubset(properties))
        expected = hashlib.sha256(source.read_bytes()).hexdigest()
        envelope = {"status": "DONE", "summary": "CAS update", "proposals": [{
            "action": "update", "id": "DOC-IND-CAS-001", "type": "DOC", "title": "updated source",
            "relative_path": "allowed.py", "content": "new = 2\n", "expected_sha256": expected,
        }]}
        self.work()
        config = self.config("ind-worker-a", [sys.executable, "-c", "raise SystemExit(98)"])
        config["workers"][0].update({"source_paths": ["allowed.py"], "backend": {"type": "responses", "model": "fixture", "api_key_env": "UNSET_INDEPENDENT_KEY"}})

        def transport(*args, **kwargs):
            context = kwargs["context_bundle"]
            self.assertEqual(expected, context["allowed_sources"][0]["sha256"])
            return {"status": "PASS", "stdout": json.dumps(envelope), "exit_code": 0, "duration_seconds": 0}

        with patch("rd_platform.worker_service.execute_backend", side_effect=transport):
            result = run_service(self.runtime, config, once=True)
        self.assertEqual(1, result["completed"])
        self.assertEqual("new = 2\n", source.read_text(encoding="utf-8"))
        artifact = self.runtime.lifecycle_snapshot(self.project)["artifacts"][0]
        self.assertEqual("DRAFT", artifact["state"])

    def test_responses_batch_registration_failure_rolls_back_all_files(self):
        """TC-V3-IND-927 / CR-V3-004: SQLite rejection cannot leave an applied proposal batch."""
        from rd_platform.worker_service import run_service
        self.runtime.execute("artifact.create", {"project_id": self.project, "artifact_type": "DOC", "artifact_id": "DOC-IND-DUP",
            "title": "existing", "state": "DRAFT", "content_ref": {"inline_json": {"fixture": True}}, "source": {"kind": "host", "actor": "ind-worker-a"}})
        self.work()
        envelope = {"status": "DONE", "summary": "batch", "proposals": [
            {"action": "create", "id": "DOC-IND-NEW", "type": "DOC", "title": "first", "relative_path": "first.py", "content": "first\n", "expected_sha256": None},
            {"action": "create", "id": "DOC-IND-DUP", "type": "DOC", "title": "duplicate", "relative_path": "second.py", "content": "second\n", "expected_sha256": None},
        ]}
        config = self.config("ind-worker-a", [sys.executable, "-c", "raise SystemExit(98)"])
        config["workers"][0].update({"source_paths": ["first.py", "second.py"], "backend": {"type": "responses", "model": "fixture", "api_key_env": "UNSET_INDEPENDENT_KEY"}})
        with patch("rd_platform.worker_service.execute_backend", return_value={"status": "PASS", "stdout": json.dumps(envelope), "exit_code": 0, "duration_seconds": 0}):
            result = run_service(self.runtime, config, once=True)
        self.assertEqual(1, result["failed"])
        self.assertFalse((self.root / "first.py").exists())
        self.assertFalse((self.root / "second.py").exists())
        journals = list((self.root / ".rd-platform" / "proposal-journal").glob("*.json"))
        self.assertEqual("ROLLED_BACK", json.loads(journals[0].read_text(encoding="utf-8"))["state"])

    def test_responses_connect_cancellation_returns_without_claiming_remote_completion(self):
        """TC-V3-IND-928 / CR-V3-004: a stuck connect is locally bounded but remote outcome stays unknown."""
        from rd_platform.proposal_backend import run_responses
        entered, release, cancel, box = threading.Event(), threading.Event(), threading.Event(), {}
        spec = {"model": "fixture", "api_key_env": "IND_RESPONSES_TEST_KEY", "endpoint": "https://api.openai.com/v1/responses", "max_output_tokens": 32}

        def blocked_connect(*_):
            entered.set(); release.wait(5)
            raise OSError("released independent transport")

        with patch.dict(os.environ, {"IND_RESPONSES_TEST_KEY": "temporary"}):
            caller = threading.Thread(target=lambda: box.setdefault("result", run_responses(spec, prompt="{}", timeout_seconds=5,
                max_output_bytes=1024, transport=blocked_connect, cancel_event=cancel)))
            caller.start()
            try:
                self.assertTrue(entered.wait(1), "test transport did not enter connect")
                cancel.set(); caller.join(1)
                self.assertFalse(caller.is_alive(), "caller was blocked by transport connect")
                result = box["result"]
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(result["cancelled"])
                self.assertTrue(result["request_may_still_be_running"])
                self.assertIn("remote outcome unknown", result["launch_error"])
            finally:
                release.set(); caller.join(6)

    def _prepared_recovery_batch(self, name):
        from rd_platform.proposal_files import apply, prepare
        item = {"action": "create", "id": "DOC-IND-REC-" + name, "type": "DOC", "title": "recovery",
                "relative_path": name + ".txt", "content": "proposed", "expected_sha256": None}
        journal, _ = prepare(self.root, [item], [item["relative_path"]], binding={"project_id": self.project, "work_id": "temporary", "attempt": 1, "db": str(Path(self.runtime.db_path).resolve())})
        apply(journal)
        return journal, self.root / item["relative_path"]

    def test_recovery_uncommitted_batch_restores_original_absence(self):
        """TC-V3-IND-929 / CR-V3-004: uncommitted applied create is removed on recovery."""
        from rd_platform.proposal_files import recover
        journal, target = self._prepared_recovery_batch("recover-rollback")
        recover(journal, lambda _: False)
        self.assertFalse(target.exists())
        self.assertEqual("ROLLED_BACK", json.loads(journal.read_text(encoding="utf-8"))["state"])

    def test_recovery_refuses_external_drift_without_overwrite(self):
        """TC-V3-IND-930 / CR-V3-004: recovery does not overwrite a later external edit."""
        from rd_platform.proposal_files import recover
        journal, target = self._prepared_recovery_batch("recover-drift")
        target.write_text("external", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "external drift"):
            recover(journal, lambda _: False)
        self.assertEqual("external", target.read_text(encoding="utf-8"))

    def test_recovery_with_exact_persisted_refs_commits_without_rewrite(self):
        """TC-V3-IND-931 / CR-V3-004: recovery retains only exact persisted artifact identity."""
        from rd_platform.proposal_files import recover
        journal, target = self._prepared_recovery_batch("recover-commit")
        record = json.loads(journal.read_text(encoding="utf-8")); change = record["changes"][0]
        recover(journal, lambda _: [{"type": change["type"], "id": change["id"], "version": 1}])
        self.assertEqual("proposed", target.read_text(encoding="utf-8"))
        self.assertEqual("COMMITTED", json.loads(journal.read_text(encoding="utf-8"))["state"])

    def test_recovery_does_not_delete_preexisting_empty_parent_directory(self):
        """TC-V3-IND-932 / CR-V3-004: rollback cleans only directories it created."""
        from rd_platform.proposal_files import apply, prepare, recover
        parent = self.root / "preexisting"; parent.mkdir()
        item = {"action": "create", "id": "DOC-IND-REC-PARENT", "type": "DOC", "title": "parent",
                "relative_path": "preexisting/proposed.txt", "content": "proposed", "expected_sha256": None}
        journal, _ = prepare(self.root, [item], [item["relative_path"]])
        apply(journal); recover(journal, lambda _: False)
        self.assertTrue(parent.is_dir(), "recovery must not remove a preexisting empty parent")
        self.assertFalse((parent / "proposed.txt").exists())

    def test_recovery_proof_cannot_commit_when_target_bytes_drifted(self):
        """TC-V3-IND-933 / CR-V3-004: DB proof never authorizes overwriting external byte drift."""
        from rd_platform.proposal_files import recover
        journal, target = self._prepared_recovery_batch("recover-proof-drift")
        record = json.loads(journal.read_text(encoding="utf-8")); change = record["changes"][0]
        target.write_text("external", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "drift"):
            recover(journal, lambda _: [{"type": change["type"], "id": change["id"], "version": 1}])
        self.assertEqual("external", target.read_text(encoding="utf-8"))
        self.assertNotEqual("COMMITTED", json.loads(journal.read_text(encoding="utf-8"))["state"])

class ApprovalEndpointIndependentTests(unittest.TestCase):
    """TC-V3-IND-907/908: real temporary SSH signatures, never human approval."""

    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is unavailable")
    def test_signature_scope_tamper_agent_identity_and_replay_are_rejected(self):
        from rd_platform.approval_provider import (
            SshApprovalProvider, create_approval_challenge, register_signed_approval,
        )
        with tempfile.TemporaryDirectory(prefix="ind-v3-approval-") as folder:
            root = Path(folder)
            key = root / "temporary_ed25519"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
            signer = root / "allowed_signers"
            signer.write_text(
                "ind-human namespaces=\"rd-platform-approval\" " + key.with_suffix(".pub").read_text(encoding="utf-8").strip() + "\n",
                encoding="utf-8",
            )
            bootstrap = Runtime(root / "state.db")
            project = bootstrap.execute("project.create", {"name": "independent approval", "idea": "temporary signature fixture"})["id"]
            bootstrap.execute("agent.register", {"id": "ind-dev", "role": "developer"})
            bootstrap.execute("lifecycle.initialize", {"project_id": project, "repository_root": str(root), "mode": "active"})
            bootstrap.execute("artifact.create", {
                "project_id": project, "artifact_type": "REQ", "artifact_id": "REQ-IND-APPROVAL",
                "title": "temporary approval scope", "state": "BASELINED",
                "content_ref": {"inline_json": {"temporary": True}}, "source": {"kind": "host", "actor": "ind-dev"},
            })
            provider = SshApprovalProvider({
                "provider_id": "independent-ssh", "allowed_signers": str(signer), "ssh_keygen": "ssh-keygen",
                "authorizations": [{"operator": "ind-human", "projects": [project], "gates": ["G9"]}],
            })
            runtime = Runtime(root / "state.db", approval_provider=provider)
            data = {
                "project_id": project, "kind": "human_approval", "status": "VERIFIED",
                "locator": {"inline_json": {"fixture": "not a human approval"}},
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"gate_id": "G9", "decision": "APPROVE", "statement": "temporary fixture only",
                             "artifact_refs": [{"type": "REQ", "id": "REQ-IND-APPROVAL", "version": 1}]},
            }
            with self.assertRaises(ValueError):
                bootstrap.register_human_approval(data, operator="ind-human")
            challenge = create_approval_challenge(runtime, data, operator="ind-human", provider=provider)
            challenge_file = root / "challenge.json"
            challenge_file.write_text(Store.dumps(challenge), encoding="utf-8")
            subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "rd-platform-approval", str(challenge_file)], check=True, capture_output=True)
            response = {"challenge": challenge, "signature_path": str(challenge_file) + ".sig"}
            wrong_key = root / "wrong_ed25519"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(wrong_key)], check=True, capture_output=True)
            wrong_file = root / "wrong.json"; wrong_file.write_text(Store.dumps(challenge), encoding="utf-8")
            subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(wrong_key), "-n", "rd-platform-approval", str(wrong_file)], check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "signature"):
                register_signed_approval(runtime, data, operator="ind-human", provider=provider,
                                         response={"challenge": challenge, "signature_path": str(wrong_file) + ".sig"})
            expired = create_approval_challenge(runtime, data, operator="ind-human", provider=provider,
                                                now=datetime.now(timezone.utc) - timedelta(minutes=10))
            expired_file = root / "expired.json"; expired_file.write_text(Store.dumps(expired), encoding="utf-8")
            subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "rd-platform-approval", str(expired_file)], check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "expired"):
                register_signed_approval(runtime, data, operator="ind-human", provider=provider,
                                         response={"challenge": expired, "signature_path": str(expired_file) + ".sig"})
            wrong_scope = SshApprovalProvider({"provider_id": "wrong-scope", "allowed_signers": str(signer), "ssh_keygen": "ssh-keygen",
                                               "authorizations": [{"operator": "ind-human", "projects": [project], "gates": ["G10"]}]})
            with self.assertRaisesRegex(ValueError, "authorized"):
                create_approval_challenge(runtime, data, operator="ind-human", provider=wrong_scope)
            tampered = dict(data, metadata={**data["metadata"], "statement": "scope was replaced"})
            with self.assertRaisesRegex(ValueError, "binding"):
                register_signed_approval(runtime, tampered, operator="ind-human", provider=provider, response=response)
            approval = register_signed_approval(runtime, data, operator="ind-human", provider=provider, response=response)
            self.assertEqual("human", approval["recorded_role"])
            self.assertEqual("independent-ssh", approval["metadata"]["provider_id"])
            with self.assertRaisesRegex(ValueError, "consumed"):
                register_signed_approval(runtime, data, operator="ind-human", provider=provider, response=response)
            runtime.execute("agent.register", {"id": "ind-human", "role": "reviewer"})
            another = create_approval_challenge(runtime, data, operator="ind-human", provider=provider)
            another_file = root / "agent.json"
            another_file.write_text(Store.dumps(another), encoding="utf-8")
            subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "rd-platform-approval", str(another_file)], check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "agent identity"):
                register_signed_approval(runtime, data, operator="ind-human", provider=provider,
                                         response={"challenge": another, "signature_path": str(another_file) + ".sig"})


class CliEndpointIndependentTests(unittest.TestCase):
    """TC-V3-IND-923/924: public CLI protocol, bootstrap, and human signature seam."""

    @unittest.skipUnless(shutil.which("ssh-keygen"), "ssh-keygen is unavailable")
    def test_cli_challenge_sign_and_register_are_bound_and_single_use(self):
        """TC-V3-IND-923 / REQ-V3-017/020: no private key reaches the platform CLI."""
        with tempfile.TemporaryDirectory(prefix="ind-v3-cli-approval-") as folder:
            root = Path(folder); repository = root / "repository"; repository.mkdir()
            db = root / "state.db"; runtime = Runtime(db)
            project = runtime.execute("project.create", {"name": "CLI approval", "idea": "temporary independent fixture"})["id"]
            runtime.execute("agent.register", {"id": "ind-cli-dev", "role": "developer"})
            runtime.execute("lifecycle.initialize", {"project_id": project, "repository_root": str(repository), "mode": "active"})
            artifact = runtime.execute("artifact.create", {"project_id": project, "artifact_type": "REQ", "artifact_id": "REQ-IND-CLI",
                "title": "CLI approval scope", "state": "BASELINED", "content_ref": {"inline_json": {"fixture": True}},
                "source": {"kind": "host", "actor": "ind-cli-dev"}})
            key = root / "temporary_ed25519"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True, capture_output=True)
            allowed = root / "allowed_signers"
            allowed.write_text("ind-cli-human namespaces=\"rd-platform-approval\" " + key.with_suffix(".pub").read_text(encoding="utf-8").strip() + "\n", encoding="utf-8")
            provider = root / "provider.json"; provider.write_text(json.dumps({"provider_id": "ind-cli-ssh", "allowed_signers": str(allowed), "ssh_keygen": "ssh-keygen",
                "authorizations": [{"operator": "ind-cli-human", "projects": [project], "gates": ["G9"]}]}), encoding="utf-8")
            request = root / "request.json"; request.write_text(json.dumps({"project_id": project, "kind": "human_approval", "status": "VERIFIED",
                "locator": {"inline_json": {"fixture": "temporary only"}}, "observed_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {"gate_id": "G9", "decision": "APPROVE", "statement": "temporary SSH CLI fixture", "artifact_refs": [{"type": "REQ", "id": artifact["id"], "version": artifact["version"]}]}}), encoding="utf-8")
            challenge = root / "challenge.json"
            cli = [sys.executable, "-m", "rd_platform", "--db", str(db)]
            made = subprocess.run(cli + ["approval-challenge", "--provider-config", str(provider), "--request", str(request), "--operator", "ind-cli-human", "--challenge", str(challenge)],
                                  cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(0, made.returncode, made.stderr)
            self.assertEqual("WAITING_FOR_SIGNATURE", json.loads(made.stdout)["status"])
            self.assertTrue(challenge.is_file())
            subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", "rd-platform-approval", str(challenge)], check=True, capture_output=True)
            registered = subprocess.run(cli + ["approval-register", "--provider-config", str(provider), "--request", str(request), "--operator", "ind-cli-human", "--challenge", str(challenge), "--signature", str(challenge) + ".sig"],
                                       cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(0, registered.returncode, registered.stderr)
            self.assertEqual("human", json.loads(registered.stdout)["recorded_role"])
            replay = subprocess.run(cli + ["approval-register", "--provider-config", str(provider), "--request", str(request), "--operator", "ind-cli-human", "--challenge", str(challenge), "--signature", str(challenge) + ".sig"],
                                    cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertNotEqual(0, replay.returncode)
            self.assertIn("consumed", replay.stderr)

    def test_cli_orchestrate_start_is_idempotent_and_creates_one_work_chain(self):
        """TC-V3-IND-924 / REQ-V3-020: repeat bootstrap is not duplicate project creation."""
        with tempfile.TemporaryDirectory(prefix="ind-v3-cli-bootstrap-") as folder:
            root = Path(folder); repository = root / "repository"; repository.mkdir(); db = root / "state.db"
            command = [sys.executable, "-m", "rd_platform", "--db", str(db), "orchestrate-start", "--name", "independent bootstrap", "--idea", "one bounded idea", "--repository-root", str(repository), "--request-id", "independent-request-001"]
            first = subprocess.run(command, cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", check=False)
            second = subprocess.run(command, cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(0, first.returncode, first.stderr); self.assertEqual(0, second.returncode, second.stderr)
            one, two = json.loads(first.stdout), json.loads(second.stdout)
            self.assertEqual(one["project_id"], two["project_id"])
            self.assertEqual("PLANNED", two["status"])
            snapshot = Runtime(db).lifecycle_snapshot(one["project_id"], limit=500)
            self.assertEqual(12, len(snapshot["work_orders"]))
            self.assertEqual(1, len(Runtime(db).snapshot()["projects"]))

    def test_status_cli_http_board_and_bilingual_skill_keep_read_only_stage_boundary(self):
        """TC-V3-IND-937 / REQ-V3-020: user-facing routes agree without granting execution."""
        from rd_platform.web import create_server
        with tempfile.TemporaryDirectory(prefix="ind-v3-cli-status-") as folder:
            root = Path(folder); repository = root / "repository"; repository.mkdir(); db = root / "state.db"
            cli = [sys.executable, "-m", "rd_platform", "--db", str(db)]
            created = subprocess.run(cli + ["orchestrate-start", "--name", "independent status", "--idea", "read-only boundary", "--repository-root", str(repository), "--request-id", "ind-status-020"], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(0, created.returncode, created.stderr)
            project = json.loads(created.stdout)["project_id"]
            before = hashlib.sha256(db.read_bytes()).hexdigest()
            status = subprocess.run(cli + ["orchestrate-status", "--project-id", project], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(0, status.returncode, status.stderr)
            data = json.loads(status.stdout)
            self.assertEqual(before, hashlib.sha256(db.read_bytes()).hexdigest())
            self.assertFalse(data["execution_authorized"])
            self.assertEqual("ALLOWED", data["work_orders"][0]["stage_admission"])
            self.assertTrue(all(row["stage_admission"] == "WAITING_PREREQUISITE" for row in data["work_orders"][1:]))
            server = create_server(db, port=0); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                connection.request("GET", f"/api/orchestration?project_id={project}", headers={"Host": f"127.0.0.1:{server.server_port}"})
                response = connection.getresponse(); board = json.loads(response.read()); connection.close()
                self.assertEqual(200, response.status)
                self.assertEqual(data["work_orders"], board["work_orders"])
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                connection.request("GET", "/", headers={"Host": f"127.0.0.1:{server.server_port}"})
                response = connection.getresponse(); page = response.read().decode("utf-8"); connection.close()
                self.assertEqual(200, response.status); self.assertIn("阶段工作与推进条件", page)
            finally:
                server.shutdown(); server.server_close(); thread.join(5)
            repository_root = Path(__file__).resolve().parents[2]
            chinese = (repository_root / "README.md").read_text(encoding="utf-8")
            english = (repository_root / "README.en.md").read_text(encoding="utf-8")
            skill = (repository_root / ".agents" / "skills" / "platform-orchestration" / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(all("orchestrate-status" in text for text in (chinese, english, skill)))
            self.assertIn("不是执行授权", chinese)
            self.assertIn("not execution authority", english)
            self.assertIn("DRAFT work DONE cannot unlock", skill)


class ValidatorFixtureIndependentTests(unittest.TestCase):
    """TC-V3-IND-940: validator fixture isolation is a test-environment contract."""

    def test_temporary_validator_fixture_explicitly_excludes_live_runtime_state(self):
        """TC-V3-IND-940 / REQ-V3-020: a copied fixture must never inherit `.rd-platform`."""
        fixture = Path(__file__).resolve().parents[2] / "tests" / "platform" / "test_validator_contract.py"
        tree = ast.parse(fixture.read_text(encoding="utf-8"), filename=str(fixture))
        copy_call = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "copytree"
        )
        ignored = next(keyword.value for keyword in copy_call.keywords if keyword.arg == "ignore")
        self.assertIsInstance(ignored, ast.Call)
        patterns = [item.value for item in ignored.args if isinstance(item, ast.Constant) and isinstance(item.value, str)]
        self.assertIn(".rd-platform", patterns)

        # Independently exercise the declared copy contract, rather than
        # importing the developer test helper.  A volatile control database is
        # deliberately placed next to a source contract and must not appear in
        # the fixture seen by a validator test.
        with tempfile.TemporaryDirectory(prefix="ind-v3-validator-source-") as source_dir, tempfile.TemporaryDirectory(prefix="ind-v3-validator-copy-") as copy_dir:
            source, copied = Path(source_dir), Path(copy_dir) / "platform"
            (source / ".rd-platform").mkdir()
            (source / ".rd-platform" / "state.db").write_bytes(b"volatile-runtime-state")
            (source / "platform-manifest.json").write_text('{"fixture":"contract"}', encoding="utf-8")
            shutil.copytree(source, copied, ignore=shutil.ignore_patterns(*patterns))
            self.assertTrue((copied / "platform-manifest.json").is_file())
            self.assertFalse((copied / ".rd-platform").exists())


class DeploymentEndpointIndependentTests(unittest.TestCase):
    """TC-V3-IND-909/910: isolated HTTP target, hash fence, and compensation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-deploy-")
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        self.app.mkdir()
        self.source = self.app / "source.txt"
        self.source.write_text("independent-v1", encoding="utf-8")
        self.deploy = self.app / "deploy.py"
        self.deploy.write_text("from pathlib import Path\nPath('served.txt').write_text('ready', encoding='utf-8')\n", encoding="utf-8")
        self.rollback = self.app / "rollback.py"
        self.rollback.write_text("from pathlib import Path\nPath('served.txt').unlink(missing_ok=True)\n", encoding="utf-8")
        self.runtime = Runtime(self.root / "state.db")
        self.project = self.runtime.execute("project.create", {"name": "independent deploy", "idea": "isolated local target"})["id"]
        self.runtime.execute("lifecycle.initialize", {"project_id": self.project, "repository_root": str(self.root), "mode": "active"})
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.server = subprocess.Popen([sys.executable, "-m", "http.server", str(self.port), "--bind", "127.0.0.1"], cwd=self.app,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        until = time.monotonic() + 5
        while time.monotonic() < until:
            try:
                urlopen(f"http://127.0.0.1:{self.port}/", timeout=.2).read()
                break
            except OSError:
                time.sleep(.03)
        else:
            self.fail("isolated HTTP target did not start")

    def tearDown(self):
        self.server.terminate()
        self.server.wait(timeout=5)
        self.temp.cleanup()

    def config(self, operation, *, health=None, rollback=None):
        rollback_health = [sys.executable, "-c", "from pathlib import Path; assert not Path('served.txt').exists()"]
        return {
            "project_id": self.project, "environment": "independent-isolated", "mode": "trial", "operation_id": operation,
            "cwd": str(self.app), "source_hashes": {
                "source.txt": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                "deploy.py": hashlib.sha256(self.deploy.read_bytes()).hexdigest(),
                "rollback.py": hashlib.sha256(self.rollback.read_bytes()).hexdigest(),
            },
            "deploy": {"argv": [sys.executable, str(self.deploy)], "timeout_seconds": 5, "output_limit_bytes": 4096, "idempotent": True},
            "health": {"argv": health or [sys.executable, "-c", f"from urllib.request import urlopen; assert urlopen('http://127.0.0.1:{self.port}/served.txt', timeout=2).read() == b'ready'"], "timeout_seconds": 5, "output_limit_bytes": 4096},
            "rollback": {"argv": rollback or [sys.executable, str(self.rollback)], "timeout_seconds": 5, "output_limit_bytes": 4096},
            "rollback_health": {"argv": rollback_health, "timeout_seconds": 5, "output_limit_bytes": 4096},
            "receipt_dir": str(self.root / "receipts"),
        }

    def test_real_health_failure_compensates_and_receipts_preserve_outcome(self):
        from rd_platform.deployment import execute_deployment
        passed = execute_deployment(self.runtime, self.config("ind-pass"))
        self.assertEqual("TRIAL_SUCCEEDED", passed["status"])
        self.assertEqual(b"ready", urlopen(f"http://127.0.0.1:{self.port}/served.txt", timeout=2).read())
        failed = execute_deployment(self.runtime, self.config("ind-health-fail", health=[sys.executable, "-c", "raise SystemExit(17)"]))
        self.assertEqual("TRIAL_ROLLED_BACK", failed["status"])
        self.assertEqual("FAIL", failed["health"]["status"])
        self.assertEqual("PASS", failed["rollback"]["status"])
        self.assertFalse((self.app / "served.txt").exists())
        receipt_lines = (self.root / "receipts" / "operations.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(receipt_lines), 4)
        self.assertIn("COMPLETED", {json.loads(line)["state"] for line in receipt_lines})

    def test_hash_drift_and_unknown_nonidempotent_operation_do_not_launch(self):
        from rd_platform.deployment import execute_deployment
        drift = self.config("ind-drift")
        self.source.write_text("mutated", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source hash drift"):
            execute_deployment(self.runtime, drift)
        self.assertFalse((self.app / "served.txt").exists())
        (self.root / "receipts").mkdir(exist_ok=True)
        (self.root / "receipts" / "operations.jsonl").write_text(json.dumps({"operation_id": "ind-unknown", "state": "STARTED"}) + "\n", encoding="utf-8")
        config = self.config("ind-unknown")
        config["deploy"]["idempotent"] = False
        with self.assertRaisesRegex(ValueError, "fingerprint conflicts"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_failed_compensation_and_conflicting_reuse_are_retained_or_refused(self):
        """TC-V3-IND-917 / REQ-V3-018: failure history is durable and operation IDs bind config."""
        from rd_platform.deployment import execute_deployment
        failed = execute_deployment(self.runtime, self.config(
            "ind-compensation-failure", health=[sys.executable, "-c", "raise SystemExit(17)"],
            rollback=[sys.executable, "-c", "raise SystemExit(18)"],
        ))
        self.assertEqual("TRIAL_ROLLBACK_FAILED", failed["status"])
        self.assertEqual("FAIL", failed["rollback"]["status"])
        receipt = self.root / "receipts" / "operations.jsonl"
        self.assertIn("COMPLETED", [json.loads(line)["state"] for line in receipt.read_text(encoding="utf-8").splitlines()])
        execute_deployment(self.runtime, self.config("ind-conflicting-reuse"))
        conflict = self.config("ind-conflicting-reuse", health=[sys.executable, "-c", "raise SystemExit(19)"])
        with self.assertRaisesRegex(ValueError, "fingerprint conflicts"):
            execute_deployment(self.runtime, conflict)

    def test_same_operation_id_cannot_switch_from_deploy_to_rollback(self):
        """TC-V3-IND-925 / REQ-V3-018: the action is part of durable operation identity."""
        from rd_platform.deployment import execute_deployment
        config = self.config("ind-action-conflict")
        self.assertEqual("TRIAL_SUCCEEDED", execute_deployment(self.runtime, config)["status"])
        with self.assertRaisesRegex(ValueError, "fingerprint conflicts"):
            execute_deployment(self.runtime, config, action="rollback")
        self.assertTrue((self.app / "served.txt").exists(), "rejected rollback must not change prior deployed state")

    def test_project_script_without_declared_hash_never_starts(self):
        """TC-V3-IND-918 / REQ-V3-018: cwd pinning includes every local argv script."""
        from rd_platform.deployment import execute_deployment
        config = self.config("ind-unpinned-script")
        del config["source_hashes"]["deploy.py"]
        with self.assertRaisesRegex(ValueError, "project command source"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_formal_external_receipt_directory_is_rejected_before_launch(self):
        """TC-V3-IND-922 / REQ-V3-018: formal evidence cannot be stored outside its project."""
        from rd_platform.deployment import execute_deployment

        class ReadyFormalRuntime:
            def __init__(self, root, project_id):
                self.root, self.project_id, self.commands = root, project_id, []

            def lifecycle_snapshot(self, project_id):
                if project_id != self.project_id:
                    raise AssertionError("unexpected project")
                return {"lifecycle": {"repository_root": str(self.root)},
                        "releases": [{"id": "REL-IND-FORMAL", "status": "READY"}],
                        "gates": [{"gate_id": "G10", "gate_status": "PASS"}]}

            def execute(self, command, data):
                self.commands.append((command, data))
                raise AssertionError("formal receipt rejection must precede Runtime mutation")

        with tempfile.TemporaryDirectory(prefix="ind-v3-external-receipt-") as outside:
            runtime = ReadyFormalRuntime(self.root, self.project)
            config = self.config("ind-external-receipt")
            config.update({
                "mode": "formal", "release_id": "REL-IND-FORMAL", "operator": "temporary-human",
                "executor_id": "temporary-release", "environment_ref": {"type": "EVIDENCE", "id": "EVD-ENV", "version": 1},
                "evidence_artifact_refs": [{"type": "DOC", "id": "DOC-IND", "version": 1}], "receipt_dir": outside,
            })
            with self.assertRaisesRegex(ValueError, "formal receipt_dir"):
                execute_deployment(runtime, config)
            self.assertEqual([], runtime.commands)
            self.assertFalse((self.app / "served.txt").exists())
            self.assertFalse((Path(outside) / "operations.jsonl").exists())

    @staticmethod
    def _ref(kind, ident, version=1):
        return {"type": kind, "id": ident, "version": version}

    def _ready_formal_release(self):
        """Build a real, isolated READY release through public Runtime commands.

        The approval verifier is a synthetic test mechanism only; it does not
        represent a person or a repository approval.
        """
        from rd_platform.lifecycle_base import LifecycleBase
        from rd_platform.lifecycle_governance import POLICY, REVIEW_CRITERIA, TEST_CRITERIA

        class SyntheticFixtureApproval:
            def verify(self, *, binding, approval_request):
                return {
                    "authenticated": True, "operator": "independent-fixture-human",
                    "provider_id": "independent-test-only",
                    "verification_id": "independent-" + binding["gate_id"],
                    "binding_digest": LifecycleBase.digest(binding),
                }

        self.runtime = Runtime(self.root / "state.db", approval_provider=SyntheticFixtureApproval())
        for ident, role in (("ind-dev", "developer"), ("ind-test", "tester"),
                            ("ind-review", "reviewer"), ("ind-release", "release_manager")):
            self.runtime.execute("agent.register", {"id": ident, "role": role})

        def artifact(ident, kind):
            return self.runtime.execute("artifact.create", {
                "project_id": self.project, "artifact_id": ident, "artifact_type": kind,
                "title": ident, "state": "BASELINED",
                "content_ref": {"inline_json": {"fixture": "isolated independent formal contract"}},
                "source": {"kind": "host", "actor": "ind-dev"},
            })

        def evidence(kind="document", actor="ind-review", metadata=None):
            return self.runtime.execute("evidence.register", {
                "project_id": self.project, "kind": kind, "status": "VERIFIED",
                "source": {"kind": "host", "actor": actor},
                "locator": {"inline_json": {"fixture": "independent test only"}},
                "observed_at": datetime.now(timezone.utc).isoformat(), "metadata": metadata or {},
            })

        artifact("REQ-IND", "REQ")
        self.runtime.execute("test_model.create", {
            "project_id": self.project, "artifact_id": "TM-IND",
            "source": {"kind": "host", "actor": "ind-test"}, "requirement_refs": ["REQ-IND"],
            "function_tree": {"name": "formal", "children": ["atomicity"]},
            "risks": [{"risk_id": "RISK-IND", "description": "partial formal mutation", "likelihood": "HIGH", "impact": "HIGH", "priority": "P0", "requirement_refs": ["REQ-IND"]}],
            "objects": [{"object_id": "OBJ-IND", "description": "formal deployment"}], "types": ["FUNCTIONAL"],
            "test_points": [{"point_id": "TP-IND", "object_id": "OBJ-IND", "type": "FUNCTIONAL", "rationale": "atomic formal registration", "risk_refs": ["RISK-IND"], "requirement_refs": ["REQ-IND"], "coverage_rule": "failure paths"}],
        })
        self.runtime.execute("test_case.create", {
            "project_id": self.project, "case_id": "TC-IND", "test_model_id": "TM-IND", "test_point_refs": ["TP-IND"], "requirement_refs": ["REQ-IND"],
            "test_type": "FUNCTIONAL", "module": "deployment", "priority": "P0", "risk": "HIGH", "preconditions": [], "test_data": {},
            "steps": [{"order": 1, "action": "inject formal registration failure", "expected_observation": "all Runtime writes roll back"}],
            "expected_result": "atomic rollback", "automation": {"status": "MANUAL"}, "state": "BASELINED",
        })
        environment = evidence("test_environment", "ind-test")
        execution = self.runtime.execute("test_execution.start", {"case_id": "TC-IND", "case_version": 1, "executor_id": "ind-test", "environment_ref": self._ref("EVIDENCE", environment["id"])})
        execution_evidence = evidence("test_execution", "ind-test", {"execution_id": execution["id"], "result": "PASS", "artifact_refs": [self._ref("TEST_CASE", "TC-IND")]})
        self.runtime.execute("test_execution.finish", {"execution_id": execution["id"], "result": "PASS", "actual_result": "isolated fixture", "evidence_refs": [self._ref("EVIDENCE", execution_evidence["id"]) ]})

        for ident, kind in (("DES-IND", "DES"), ("TASK-IND", "TASK"), ("CODE-IND", "CODE_CHANGE"), ("DOC-ROLLBACK-IND", "DOC")):
            artifact(ident, kind)
        for left, right, relation in ((self._ref("REQ", "REQ-IND"), self._ref("DES", "DES-IND"), "realized_by"),
                                      (self._ref("DES", "DES-IND"), self._ref("TASK", "TASK-IND"), "planned_by"),
                                      (self._ref("TASK", "TASK-IND"), self._ref("CODE_CHANGE", "CODE-IND"), "implemented_by")):
            self.runtime.execute("trace.link", {"project_id": self.project, "from": left, "to": right, "relation": relation})
        release = self.runtime.execute("release.create", {"project_id": self.project, "release_id": "REL-IND-FORMAL", "version": "0.0-test", "artifact_refs": [self._ref("CODE_CHANGE", "CODE-IND")], "requirement_refs": [self._ref("REQ", "REQ-IND")], "known_issue_refs": [], "rollback_ref": self._ref("DOC", "DOC-ROLLBACK-IND")})
        for number in range(12):
            gate = f"G{number}"; doc = f"DOC-{gate}-IND"; artifact(doc, "DOC"); subject = [self._ref("DOC", doc)]
            ordinary = [item for item in POLICY[gate] if item not in TEST_CRITERIA | REVIEW_CRITERIA | {"human_acceptance"}]
            if ordinary: evidence(metadata={"gate_id": gate, "criteria": ordinary, "artifact_refs": subject})
            tests = [item for item in POLICY[gate] if item in TEST_CRITERIA]
            if tests: evidence("test_execution", "ind-test", {"gate_id": gate, "criteria": tests, "execution_id": execution["id"], "result": "PASS", "artifact_refs": [self._ref("TEST_CASE", "TC-IND")]})
            reviews = [item for item in POLICY[gate] if item in REVIEW_CRITERIA]
            if reviews: evidence("review", "ind-review", {"gate_id": gate, "criteria": reviews, "subject_id": doc, "result": "PASS", "artifact_refs": subject})
            if number >= 9:
                self.runtime.register_human_approval({"project_id": self.project, "kind": "human_approval", "status": "VERIFIED", "locator": {"inline_json": {"synthetic_fixture": True}}, "observed_at": datetime.now(timezone.utc).isoformat(), "metadata": {"gate_id": gate, "criteria": ["human_acceptance"] if number == 9 else [], "decision": "APPROVE", "statement": "Synthetic independent fixture, not a human approval", "artifact_refs": subject}}, operator="independent-fixture-human")
            assessment = self.runtime.execute("gate.assess", {"project_id": self.project, "gate_id": gate})
            self.assertEqual("PASS", assessment["candidate"], assessment["missing"])
            decision = evidence("gate_decision", "ind-review", {"assessment_id": assessment["id"], "status": "PASS"})
            self.runtime.execute("gate.decide", {"assessment_id": assessment["id"], "status": "PASS", "decided_by": "ind-review", "decision_evidence_refs": [self._ref("EVIDENCE", decision["id"]) ]})
            if number == 10:
                self.assertEqual("READY", self.runtime.execute("release.ready", {"release_id": release["id"], "assessment_id": assessment["id"], "decision_evidence_refs": [self._ref("EVIDENCE", decision["id"]) ]})["status"])
                env = evidence("deployment_environment", "ind-release")
                return release, self._ref("EVIDENCE", env["id"]), self._ref("CODE_CHANGE", "CODE-IND")
        self.fail("formal fixture did not reach a READY release")

    def test_formal_second_and_third_registration_failures_rollback_runtime_but_keep_receipts(self):
        """TC-V3-IND-935: formal Runtime writes are all-or-nothing after real command output."""
        from rd_platform.deployment import execute_deployment
        from rd_platform.lifecycle import LifecycleService

        release, environment, release_ref = self._ready_formal_release()
        base = self.config("ind-formal-second")
        base.update({"mode": "formal", "release_id": release["id"], "operator": "independent-fixture-human", "executor_id": "ind-release", "environment_ref": environment, "evidence_artifact_refs": [release_ref]})
        before = self.runtime.lifecycle_snapshot(self.project)
        original = LifecycleService.execute
        def fail_second(service, connection, command, data):
            if command == "release.record_deployment":
                raise ValueError("independent injected second registration failure")
            return original(service, connection, command, data)
        with patch.object(LifecycleService, "execute", fail_second):
            second = execute_deployment(self.runtime, base)
        after_second = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual("FAIL", second["status"])
        self.assertEqual(len(before["evidence"]), len(after_second["evidence"]))
        current = next(item for item in after_second["releases"] if item["id"] == release["id"])
        self.assertEqual("READY", current["status"]); self.assertEqual([], current["deployments"])
        self.assertTrue((self.root / "receipts" / "operation-ind-formal-second-completed.json").is_file())

        third = self.config("ind-formal-third", health=[sys.executable, "-c", "raise SystemExit(17)"])
        third.update({"mode": "formal", "release_id": release["id"], "operator": "independent-fixture-human", "executor_id": "ind-release", "environment_ref": environment, "evidence_artifact_refs": [release_ref]})
        before_third = self.runtime.lifecycle_snapshot(self.project)
        def fail_third(service, connection, command, data):
            if command == "evidence.register" and data.get("kind") == "rollback":
                raise ValueError("independent injected third registration failure")
            return original(service, connection, command, data)
        with patch.object(LifecycleService, "execute", fail_third):
            third_result = execute_deployment(self.runtime, third)
        after_third = self.runtime.lifecycle_snapshot(self.project)
        self.assertEqual("FAIL", third_result["status"])
        self.assertEqual(len(before_third["evidence"]), len(after_third["evidence"]))
        current = next(item for item in after_third["releases"] if item["id"] == release["id"])
        self.assertEqual("READY", current["status"]); self.assertEqual([], current["deployments"])
        self.assertTrue((self.root / "receipts" / "operation-ind-formal-third-completed.json").is_file())

    def test_public_deploy_cli_maps_trial_success_to_zero_and_formal_error_to_nonzero(self):
        """TC-V3-IND-921 / REQ-V3-018/020: CLI exit status follows trustworthy outcome."""
        trial_path = self.root / "trial.json"
        trial_path.write_text(json.dumps(self.config("ind-cli-trial")), encoding="utf-8")
        passed = subprocess.run([sys.executable, "-m", "rd_platform", "--db", str(self.runtime.db_path), "deploy-run", "--config", str(trial_path)],
                                cwd=Path(__file__).resolve().parents[2], text=True, encoding="utf-8", capture_output=True, check=False)
        self.assertEqual(0, passed.returncode, passed.stdout + passed.stderr)
        self.assertEqual("TRIAL_SUCCEEDED", json.loads(passed.stdout)["status"])
        (self.app / "served.txt").unlink()
        formal = self.config("ind-cli-formal")
        formal.update({"mode": "formal", "release_id": "REL-NOT-READY", "operator": "temporary-human", "executor_id": "temporary-release", "environment_ref": {"type": "DEPLOYMENT_ENVIRONMENT", "id": "ENV-TEST", "version": 1}, "evidence_artifact_refs": [{"type": "DOC", "id": "DOC-TEST", "version": 1}]})
        formal_path = self.root / "formal.json"; formal_path.write_text(json.dumps(formal), encoding="utf-8")
        rejected = subprocess.run([sys.executable, "-m", "rd_platform", "--db", str(self.runtime.db_path), "deploy-run", "--config", str(formal_path)],
                                  cwd=Path(__file__).resolve().parents[2], text=True, encoding="utf-8", capture_output=True, check=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn("release not found", rejected.stderr)
        self.assertFalse((self.app / "served.txt").exists())


def wsl_bash_ready(command, *, runner=subprocess.run):
    """A Windows WSL client is insufficient; a distribution must start Bash."""
    if not command:
        return False
    try:
        result = runner([command, "-e", "bash", "-lc", "printf IND_V3_WSL_BASH_READY"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "IND_V3_WSL_BASH_READY"


WSL_BASH_READY = wsl_bash_ready(shutil.which("wsl.exe"))


class LinuxSetupIndependentTests(unittest.TestCase):
    """TC-V3-IND-911: public Linux launcher fail-closed observation."""

    def test_wsl_readiness_requires_a_real_distribution_and_bash(self):
        """TC-V3-IND-934: no installed distro is NOT_AVAILABLE, not a product assertion failure."""
        self.assertFalse(wsl_bash_ready(None))
        self.assertFalse(wsl_bash_ready("wsl.exe", runner=lambda *args, **kwargs:
            subprocess.CompletedProcess(args[0], 4294967295, "", "no distribution")))
        self.assertTrue(wsl_bash_ready("wsl.exe", runner=lambda *args, **kwargs:
            subprocess.CompletedProcess(args[0], 0, "IND_V3_WSL_BASH_READY", "")))

    @unittest.skipUnless(WSL_BASH_READY, "NOT_AVAILABLE: WSL cannot start a Linux distribution and Bash")
    def test_public_wsl_launcher_rejects_python_below_required_version(self):
        root = Path(__file__).resolve().parents[2].as_posix().replace("D:", "/mnt/d")
        result = subprocess.run(
            ["wsl.exe", "-e", "bash", "-lc", f"cd {root!r} && ./scripts/setup.sh --skip-dependency-install --python-command python3"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Python version must be 3.11 or newer.", result.stdout + result.stderr)
        self.assertNotIn("Setup complete.", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
