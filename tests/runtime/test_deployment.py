"""TASK-V3-018 deployment executor contracts (isolated local targets only)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from rd_platform.deployment import execute_deployment
from rd_platform.runtime import Runtime


class SyntheticFormalRuntime:
    """Synthetic formal-state contract fixture; never a project approval."""
    def __init__(self, root, project_id, *, drift_after_preflight=False):
        self.root, self.project_id, self.drift_after_preflight = root, project_id, drift_after_preflight
        self.snapshots, self.commands = 0, []

    def lifecycle_snapshot(self, project_id):
        self.assert_project(project_id)
        self.snapshots += 1
        gate = "PASS" if not self.drift_after_preflight or self.snapshots < 3 else None
        return {"lifecycle": {"repository_root": str(self.root)}, "releases": [{"id": "REL-SYNTHETIC", "status": "READY"}],
                "gates": [{"gate_id": "G10", "gate_status": gate}]}

    def assert_project(self, project_id):
        if project_id != self.project_id:
            raise AssertionError("wrong synthetic project")

    def execute(self, command, data):
        self.commands.append(command)
        if command == "evidence.register": return {"id": data["evidence_id"], "version": 1}
        if command == "release.rollback": return {"id": data["release_id"], "status": "ROLLED_BACK"}
        if command == "release.record_deployment": return {"id": data["release_id"], "status": "RELEASED"}
        raise AssertionError("unexpected command " + command)


class DeploymentExecutorTests(unittest.TestCase):
    """Real subprocess/HTTP coverage; fixtures are never release evidence."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.root / "state.db")
        self.project = self.runtime.execute("project.create", {"name": "deploy", "idea": "fixture"})
        self.runtime.execute("lifecycle.initialize", {
            "project_id": self.project["id"], "repository_root": str(self.root), "mode": "active",
        })
        self.app = self.root / "app"
        self.app.mkdir()
        self.source = self.app / "source.txt"
        self.source.write_text("v1", encoding="utf-8")
        self.deploy_script = self.app / "deploy.py"
        self.deploy_script.write_text("from pathlib import Path\nPath('served.txt').write_text('ready', encoding='utf-8')\n", encoding="utf-8")
        self.rollback_script = self.app / "rollback.py"
        self.rollback_script.write_text("from pathlib import Path\nPath('served.txt').unlink(missing_ok=True)\n", encoding="utf-8")
        self.port = self._port()
        self.server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(self.port), "--bind", "127.0.0.1"],
            cwd=self.app, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self._wait_http("/")

    def tearDown(self):
        server = self.server
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        self.assertIsNotNone(server.poll(), "owned HTTP child must exit before fixture cleanup")
        # On Windows the child's cwd remains undeletable until its Popen owner
        # releases the completed process handle.  This is synchronization, not
        # a timing retry: cleanup starts only after the observed child exit.
        self.server = None
        del server
        self.temp.cleanup()

    @staticmethod
    def _port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def _wait_http(self, path):
        until = time.monotonic() + 5
        while time.monotonic() < until:
            try:
                with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=.2):
                    return
            except OSError:
                time.sleep(.03)
        self.fail("isolated HTTP target did not start")

    def config(self, *, health=None, rollback=None, operation_id="op-001"):
        health = health or [sys.executable, "-c", (
            "from urllib.request import urlopen; "
            f"assert urlopen('http://127.0.0.1:{self.port}/served.txt', timeout=2).read()==b'ready'"
        )]
        return {
            "project_id": self.project["id"], "environment": "isolated-local",
            "mode": "trial", "operation_id": operation_id, "cwd": str(self.app),
            "source_hashes": {
                "source.txt": hashlib.sha256(self.source.read_bytes()).hexdigest(),
                "deploy.py": hashlib.sha256(self.deploy_script.read_bytes()).hexdigest(),
                "rollback.py": hashlib.sha256(self.rollback_script.read_bytes()).hexdigest(),
            },
            "deploy": {"argv": [sys.executable, str(self.deploy_script)], "timeout_seconds": 5, "output_limit_bytes": 4096, "idempotent": True},
            "health": {"argv": health, "timeout_seconds": 5, "output_limit_bytes": 4096},
            "rollback": {"argv": rollback or [sys.executable, str(self.rollback_script)], "timeout_seconds": 5, "output_limit_bytes": 4096},
            "rollback_health": {"argv": [sys.executable, "-c", "from pathlib import Path; assert not Path('served.txt').exists()"], "timeout_seconds": 5, "output_limit_bytes": 4096},
            "receipt_dir": str(self.root / "receipts"),
        }

    def _ready_formal_release(self):
        """Create an isolated real Runtime READY release with synthetic approvals only."""
        from datetime import datetime, timezone
        from tests.runtime.test_lifecycle import LifecycleTests, SyntheticApprovalVerifier
        from rd_platform.lifecycle_governance import POLICY, REVIEW_CRITERIA, TEST_CRITERIA

        self.runtime.approval_provider = SyntheticApprovalVerifier()
        for ident, role in (("dev", "developer"), ("test", "tester"),
                            ("review", "reviewer"), ("fixture-review", "reviewer"),
                            ("fixture-test", "tester"), ("fixture-release", "release_manager")):
            self.runtime.execute("agent.register", {"id": ident, "role": role})
        fixture = LifecycleTests()
        fixture.r, fixture.root, fixture.p = self.runtime, self.root, self.project["id"]
        fixture.model_case(); execution = fixture.execution()
        for ident, kind in (("DES-FORMAL", "DES"), ("TASK-FORMAL", "TASK"), ("CODE-FORMAL", "CODE_CHANGE"), ("DOC-ROLLBACK", "DOC")):
            fixture.artifact(ident, kind)
        ref = fixture.ref
        for source, target, relation in ((ref("REQ", "REQ-001"), ref("DES", "DES-FORMAL"), "realized_by"),
                                         (ref("DES", "DES-FORMAL"), ref("TASK", "TASK-FORMAL"), "planned_by"),
                                         (ref("TASK", "TASK-FORMAL"), ref("CODE_CHANGE", "CODE-FORMAL"), "implemented_by")):
            self.runtime.execute("trace.link", {"project_id": self.project["id"], "from": source, "to": target, "relation": relation})
        release = self.runtime.execute("release.create", {"project_id": self.project["id"], "release_id": "REL-FORMAL", "version": "fixture",
            "artifact_refs": [ref("CODE_CHANGE", "CODE-FORMAL")], "requirement_refs": [ref("REQ", "REQ-001")],
            "known_issue_refs": [], "rollback_ref": ref("DOC", "DOC-ROLLBACK")})
        for n in range(11):
            gate = "G" + str(n); fixture.artifact("DOC-" + gate, "DOC"); subject = [ref("DOC", "DOC-" + gate)]
            ordinary = [item for item in POLICY[gate] if item not in TEST_CRITERIA | REVIEW_CRITERIA | {"human_acceptance"}]
            if ordinary: fixture.evidence(metadata={"gate_id": gate, "criteria": ordinary, "artifact_refs": subject})
            tests = [item for item in POLICY[gate] if item in TEST_CRITERIA]
            if tests: fixture.evidence("test_execution", actor="fixture-test", metadata={"gate_id": gate, "criteria": tests, "execution_id": execution["id"], "result": "PASS", "artifact_refs": [ref("TEST_CASE", "TC-001")]})
            reviews = [item for item in POLICY[gate] if item in REVIEW_CRITERIA]
            if reviews: fixture.evidence("review", actor="fixture-review", metadata={"gate_id": gate, "criteria": reviews, "subject_id": "DOC-" + gate, "result": "PASS", "artifact_refs": subject})
            if n >= 9:
                self.runtime.register_human_approval({"project_id": self.project["id"], "kind": "human_approval", "status": "VERIFIED",
                    "locator": {"inline_json": {"synthetic_fixture": True}}, "observed_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"gate_id": gate, "criteria": ["human_acceptance"] if n == 9 else [], "decision": "APPROVE",
                                 "statement": "Synthetic signature fixture, never a human approval", "artifact_refs": subject}}, operator="unit-test-fixture-human")
            assessment = self.runtime.execute("gate.assess", {"project_id": self.project["id"], "gate_id": gate})
            self.assertEqual("PASS", assessment["candidate"], (gate, assessment["missing"]))
            decision = fixture.evidence("gate_decision", actor="fixture-review", metadata={"assessment_id": assessment["id"], "status": "PASS"})
            self.runtime.execute("gate.decide", {"assessment_id": assessment["id"], "status": "PASS", "decided_by": "fixture-review", "decision_evidence_refs": [decision]})
            if n == 10:
                self.runtime.execute("release.ready", {"release_id": release["id"], "assessment_id": assessment["id"], "decision_evidence_refs": [decision]})
        environment = fixture.evidence("deployment_environment", actor="fixture-release")
        return release, environment, ref("REL", release["id"])

    def test_real_isolated_deploy_and_independent_http_health_succeed(self):
        result = execute_deployment(self.runtime, self.config())
        self.assertEqual("TRIAL_SUCCEEDED", result["status"])
        self.assertEqual("PASS", result["deploy"]["status"])
        self.assertEqual("PASS", result["health"]["status"])
        self.assertEqual(b"ready", urlopen(f"http://127.0.0.1:{self.port}/served.txt", timeout=2).read())
        lines = (self.root / "receipts" / "operations.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual("COMPLETED", json.loads(lines[-1])["state"])

    def test_health_failure_runs_real_rollback_and_preserves_failure_receipt(self):
        result = execute_deployment(self.runtime, self.config(health=[sys.executable, "-c", "raise SystemExit(9)"]))
        self.assertEqual("TRIAL_ROLLED_BACK", result["status"])
        self.assertEqual("FAIL", result["health"]["status"])
        self.assertEqual("PASS", result["rollback"]["status"])
        self.assertFalse((self.app / "served.txt").exists())

    def test_health_failure_with_failed_rollback_is_retained(self):
        result = execute_deployment(self.runtime, self.config(
            health=[sys.executable, "-c", "raise SystemExit(9)"],
            rollback=[sys.executable, "-c", "raise SystemExit(8)"],
        ))
        self.assertEqual("TRIAL_ROLLBACK_FAILED", result["status"])
        self.assertEqual("FAIL", result["rollback"]["status"])

    def test_source_hash_drift_prevents_command_launch(self):
        config = self.config()
        self.source.write_text("drift", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source hash drift"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_relative_project_argv_script_must_be_hash_pinned_before_launch(self):
        config = self.config()
        config["source_hashes"].pop("deploy.py")
        config["deploy"]["argv"] = [sys.executable, "deploy.py"]
        with self.assertRaisesRegex(ValueError, "project command source"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_absolute_in_cwd_project_script_must_be_hash_pinned_before_launch(self):
        config = self.config()
        config["source_hashes"].pop("deploy.py")
        with self.assertRaisesRegex(ValueError, "project command source must have a declared source hash"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    @unittest.skipUnless(os.name == "nt", "Windows short-path fixture")
    def test_windows_short_absolute_project_script_is_not_classified_as_external_tool(self):
        import ctypes
        def convert(function, path):
            buffer = ctypes.create_unicode_buffer(32768)
            written = function(str(path), buffer, len(buffer))
            if not written or written >= len(buffer): self.skipTest("host does not expose compatible 8.3 path")
            return buffer.value
        long_cwd = convert(ctypes.windll.kernel32.GetLongPathNameW, self.app)
        short_script = convert(ctypes.windll.kernel32.GetShortPathNameW, self.deploy_script)
        config = self.config()
        config["cwd"] = long_cwd
        config["source_hashes"].pop("deploy.py")
        config["deploy"]["argv"] = [sys.executable, short_script]
        with self.assertRaisesRegex(ValueError, "project command source must have a declared source hash"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_project_argv_symlink_to_outside_is_rejected_before_launch(self):
        outside = self.root.parent / (self.root.name + "-outside-deploy.py")
        marker = self.root / "outside-executed.txt"
        outside.write_text(f"from pathlib import Path\nPath(r'{marker}').write_text('outside')\n", encoding="utf-8")
        linked = self.app / "linked-deploy.py"
        try:
            linked.symlink_to(outside)
        except OSError as error:
            self.skipTest(f"host cannot create symlink fixture: {error}")
        try:
            config = self.config()
            config["source_hashes"].pop("deploy.py")
            config["source_hashes"]["linked-deploy.py"] = hashlib.sha256(linked.read_bytes()).hexdigest()
            config["deploy"]["argv"] = [sys.executable, "linked-deploy.py"]
            with self.assertRaisesRegex(ValueError, "link|beneath cwd"):
                execute_deployment(self.runtime, config)
            self.assertFalse(marker.exists())
        finally:
            outside.unlink(missing_ok=True)

    @unittest.skipUnless(os.name == "nt", "Windows junction fixture")
    def test_project_argv_junction_to_outside_is_rejected_before_launch(self):
        outside = self.root.parent / (self.root.name + "-outside-dir")
        outside.mkdir()
        marker = self.root / "outside-junction-executed.txt"
        (outside / "deploy.py").write_text(f"from pathlib import Path\nPath(r'{marker}').write_text('outside')\n", encoding="utf-8")
        linked = self.app / "linked-dir"
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(outside)], capture_output=True, text=True)
        if made.returncode:
            self.skipTest("host cannot create junction fixture: " + made.stderr)
        try:
            config = self.config()
            config["source_hashes"]["linked-dir/deploy.py"] = hashlib.sha256((linked / "deploy.py").read_bytes()).hexdigest()
            config["deploy"]["argv"] = [sys.executable, "linked-dir/deploy.py"]
            with self.assertRaisesRegex(ValueError, "link|beneath cwd"):
                execute_deployment(self.runtime, config)
            self.assertFalse(marker.exists())
        finally:
            subprocess.run(["cmd", "/c", "rmdir", str(linked)], check=False, capture_output=True)
            (outside / "deploy.py").unlink(missing_ok=True)
            outside.rmdir()

    def test_completed_operation_id_rejects_different_target_or_payload(self):
        self.assertEqual("TRIAL_SUCCEEDED", execute_deployment(self.runtime, self.config())["status"])
        changed = self.config()
        changed["environment"] = "other-isolated-target"
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            execute_deployment(self.runtime, changed)

    def test_secret_bearing_configuration_is_rejected_before_launch(self):
        config = self.config()
        config["deploy"]["argv"].append("--token=not-for-receipts")
        with self.assertRaisesRegex(ValueError, "secrets"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_operation_id_cannot_be_reused_for_opposite_action(self):
        for first, second in (("deploy", "rollback"), ("rollback", "deploy")):
            with self.subTest(first=first):
                config = self.config(operation_id="direction-" + first)
                execute_deployment(self.runtime, config, action=first)
                before = (self.app / "served.txt").exists()
                with self.assertRaisesRegex(ValueError, "fingerprint"):
                    execute_deployment(self.runtime, config, action=second)
                self.assertEqual(before, (self.app / "served.txt").exists())

    def test_non_idempotent_unknown_operation_is_not_relaunched(self):
        receipts = self.root / "receipts"
        receipts.mkdir()
        config = self.config()
        config["deploy"]["idempotent"] = False
        fingerprint = hashlib.sha256(json.dumps({"config": config, "action": "deploy"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        (receipts / "operations.jsonl").write_text(json.dumps({"operation_id": "op-001", "state": "STARTED", "fingerprint": fingerprint}) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unknown"):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_formal_release_requires_ready_release_before_command(self):
        config = self.config()
        config.update(mode="formal", release_id="REL-MISSING", operator="human-operator", executor_id="release-executor", evidence_artifact_refs=[{"type": "DOC", "id": "DOC-ANY", "version": 1}])
        with self.assertRaises(KeyError):
            execute_deployment(self.runtime, config)
        self.assertFalse((self.app / "served.txt").exists())

    def test_formal_gate_drift_after_real_command_fails_overall_but_preserves_actual_pass(self):
        config = self.config(operation_id="formal-drift")
        config.update(mode="formal", release_id="REL-SYNTHETIC", operator="synthetic-human", executor_id="synthetic-release-manager",
                      environment_ref={"type": "EVIDENCE", "id": "EVD-ENV", "version": 1}, evidence_artifact_refs=[{"type": "DOC", "id": "DOC-SYNTHETIC", "version": 1}])
        runtime = SyntheticFormalRuntime(self.root, self.project["id"], drift_after_preflight=True)
        result = execute_deployment(runtime, config)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual("PASS", result["actual_status"])
        self.assertEqual("PASS", result["deploy"]["status"])
        self.assertIn("formal_registration_error", result)
        self.assertNotIn("release.record_deployment", runtime.commands)

    def test_formal_rollback_records_only_release_rollback_after_real_compensation_health(self):
        release, environment, release_ref = self._ready_formal_release()
        deploy = self.config(operation_id="formal-rollback-prior-deploy")
        deploy.update(mode="formal", release_id=release["id"], operator="unit-test-fixture-human", executor_id="fixture-release",
                      environment_ref=environment, evidence_artifact_refs=[release_ref])
        self.assertEqual("PASS", execute_deployment(self.runtime, deploy)["status"])
        config = self.config(operation_id="formal-rollback")
        config.update(mode="formal", release_id=release["id"], operator="unit-test-fixture-human", executor_id="fixture-release",
                      environment_ref=environment, evidence_artifact_refs=[release_ref])
        result = execute_deployment(self.runtime, config, action="rollback")
        self.assertEqual("PASS", result["status"])
        self.assertEqual("PASS", result["rollback"]["status"])
        self.assertEqual("PASS", result["rollback_health"]["status"])
        current = next(item for item in self.runtime.lifecycle_snapshot(self.project["id"])["releases"] if item["id"] == release["id"])
        self.assertEqual("ROLLED_BACK", current["status"])
        self.assertEqual(1, len(current["deployments"]))
        self.assertEqual(1, len(current["rollbacks"]))

    def test_real_runtime_formal_deploy_then_rollback_uses_synthetic_gate_fixture_only(self):
        release, environment, release_ref = self._ready_formal_release()
        deploy = self.config(operation_id="real-formal-deploy")
        deploy.update(mode="formal", release_id=release["id"], operator="unit-test-fixture-human", executor_id="fixture-release",
                      environment_ref=environment, evidence_artifact_refs=[release_ref])
        self.assertEqual("PASS", execute_deployment(self.runtime, deploy)["status"])
        self.assertEqual("RELEASED", next(item for item in self.runtime.lifecycle_snapshot(self.project["id"])["releases"] if item["id"] == release["id"])["status"])
        rollback = self.config(operation_id="real-formal-rollback")
        rollback.update(mode="formal", release_id=release["id"], operator="unit-test-fixture-human", executor_id="fixture-release",
                        environment_ref=environment, evidence_artifact_refs=[release_ref])
        self.assertEqual("PASS", execute_deployment(self.runtime, rollback, action="rollback")["status"])
        current = next(item for item in self.runtime.lifecycle_snapshot(self.project["id"])["releases"] if item["id"] == release["id"])
        self.assertEqual("ROLLED_BACK", current["status"])
        self.assertEqual(1, len(current["deployments"]))
        self.assertEqual(1, len(current["rollbacks"]))

    def test_formal_external_receipt_directory_is_rejected_before_real_command(self):
        release, environment, release_ref = self._ready_formal_release()
        external = tempfile.TemporaryDirectory()
        try:
            config = self.config(operation_id="formal-external-receipt")
            config.update(mode="formal", release_id=release["id"], operator="unit-test-fixture-human", executor_id="fixture-release",
                          environment_ref=environment, evidence_artifact_refs=[release_ref], receipt_dir=external.name)
            with self.assertRaisesRegex(ValueError, "formal receipt_dir"):
                execute_deployment(self.runtime, config)
            self.assertFalse((self.app / "served.txt").exists())
            current = next(item for item in self.runtime.lifecycle_snapshot(self.project["id"])["releases"] if item["id"] == release["id"])
            self.assertEqual("READY", current["status"])
            self.assertEqual([], current["deployments"])
        finally:
            external.cleanup()

    def test_formal_second_mutation_failure_rolls_back_evidence_and_release_but_keeps_receipt(self):
        from rd_platform.lifecycle import LifecycleService
        release, environment, release_ref = self._ready_formal_release()
        config = self.config(operation_id="formal-transaction-second")
        config.update(mode="formal", release_id=release["id"], operator="unit-test-fixture-human", executor_id="fixture-release",
                      environment_ref=environment, evidence_artifact_refs=[release_ref])
        before = self.runtime.lifecycle_snapshot(self.project["id"])
        original = LifecycleService.execute
        def fail_second(service, connection, command, data):
            if command == "release.record_deployment": raise ValueError("injected second mutation failure")
            return original(service, connection, command, data)
        with patch.object(LifecycleService, "execute", fail_second):
            result = execute_deployment(self.runtime, config)
        after = self.runtime.lifecycle_snapshot(self.project["id"])
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(len(before["evidence"]), len(after["evidence"]))
        current = next(item for item in after["releases"] if item["id"] == release["id"])
        self.assertEqual("READY", current["status"]); self.assertEqual([], current["deployments"])
        self.assertTrue((self.root / "receipts" / "operation-formal-transaction-second-completed.json").is_file())

    def test_formal_third_mutation_failure_rolls_back_failed_deploy_record_but_keeps_receipt(self):
        from rd_platform.lifecycle import LifecycleService
        release, environment, release_ref = self._ready_formal_release()
        config = self.config(health=[sys.executable, "-c", "raise SystemExit(9)"], operation_id="formal-transaction-third")
        config.update(mode="formal", release_id=release["id"], operator="unit-test-fixture-human", executor_id="fixture-release",
                      environment_ref=environment, evidence_artifact_refs=[release_ref])
        before = self.runtime.lifecycle_snapshot(self.project["id"])
        original = LifecycleService.execute
        def fail_third(service, connection, command, data):
            if command == "evidence.register" and data.get("kind") == "rollback": raise ValueError("injected third mutation failure")
            return original(service, connection, command, data)
        with patch.object(LifecycleService, "execute", fail_third):
            result = execute_deployment(self.runtime, config)
        after = self.runtime.lifecycle_snapshot(self.project["id"])
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(len(before["evidence"]), len(after["evidence"]))
        current = next(item for item in after["releases"] if item["id"] == release["id"])
        self.assertEqual("READY", current["status"]); self.assertEqual([], current["deployments"])
        self.assertTrue((self.root / "receipts" / "operation-formal-transaction-third-completed.json").is_file())
