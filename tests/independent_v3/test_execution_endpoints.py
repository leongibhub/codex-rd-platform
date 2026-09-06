"""Independent black-box checks for CR-V3-003 execution endpoints.

These tests derive from REQ-V3-016..020 and use a temporary Runtime database,
real local subprocesses, and a real loopback HTTP server.  They intentionally
do not reuse developer test helpers or call private worker functions.
"""
from __future__ import annotations

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

    def work(self, *, minimum=1, role="developer", dependencies=None, input_refs=None):
        return self.runtime.execute("work.create", {
            "project_id": self.project, "gate_id": "G0", "activity": "independent execution",
            "required_role": role, "why": "verify bounded external execution",
            "input_refs": input_refs or [], "dependencies": dependencies or [],
            "output_contract": {"required_types": ["DOC"], "min_outputs": minimum},
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


class LinuxSetupIndependentTests(unittest.TestCase):
    """TC-V3-IND-911: public Linux launcher fail-closed observation."""

    @unittest.skipUnless(shutil.which("wsl.exe"), "WSL is unavailable")
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
