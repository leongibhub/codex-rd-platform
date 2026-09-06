from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from rd_platform.stack_harness import package_app, probe_tools, run_matrix


class StackHarnessTests(unittest.TestCase):
    """TC-V3-201..206 / TASK-V3-002 / REQ-V3-010, NFR-V3-004."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rd-stack-")
        self.root = Path(self.temp.name)
        self.app = self.root / "app"
        self.app.mkdir()
        (self.app / "main.py").write_text("print('source')\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, commands):
        path = self.app / "manifest.json"
        path.write_text(json.dumps({"schema_version": 1, "id": "demo", "stack": "python", "requirements": [],
                                    "commands": commands, "native_validation": "none", "entrypoint": "main.py"}), encoding="utf-8")
        return path

    def test_missing_required_tool_is_not_available(self):
        result = run_matrix(self.manifest({"unit": ["{node}", "-e", "0"]}), root=self.root,
                            tools={"node": None})
        self.assertEqual(result["status"], "NOT_AVAILABLE")
        self.assertEqual(result["phases"]["unit"]["status"], "NOT_AVAILABLE")

    def test_missing_command_never_passes(self):
        result = run_matrix(self.manifest({}), root=self.root)
        self.assertEqual(result["status"], "NOT_EXECUTED")
        self.assertEqual(result["phases"]["build"]["status"], "NOT_EXECUTED")

    def test_selected_phase_and_failed_command_preserve_runner_evidence(self):
        result = run_matrix(self.manifest({"unit": ["{python}", "-c", "raise SystemExit(7)"]}), root=self.root,
                            phases=["unit"])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["phases"]["unit"]["exit_code"], 7)
        self.assertIn("source_sha256", result)

    def test_escape_and_unknown_placeholder_are_rejected(self):
        outside = self.root.parent / "outside-manifest.json"
        outside.write_text("{}", encoding="utf-8")
        with self.assertRaises(ValueError):
            run_matrix(outside, root=self.root)
        with self.assertRaises(ValueError):
            run_matrix(self.manifest({"unit": ["{unknown}"]}), root=self.root, phases=["unit"])

    def test_list_elements_must_be_strings(self):
        with self.assertRaises(ValueError):
            run_matrix(self.manifest({"unit": [sys.executable, 3]}), root=self.root, phases=["unit"])

    def test_real_python_manifest_and_deterministic_package_hash(self):
        manifest = self.manifest({"unit": ["{python}", "-c", "print('actual python evidence')"]})
        result = run_matrix(manifest, root=self.root, phases=["unit"])
        self.assertEqual(result["status"], "PASS", result)
        first = package_app(manifest, root=self.root)
        second = package_app(manifest, root=self.root)
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertTrue(Path(first["archive"]).is_file())
        self.assertTrue(Path(first["sha256_manifest"]).is_file())
        self.assertTrue(Path(first["archive"]).is_relative_to((self.root / ".rd-platform" / "deliveries").resolve()))

    def test_output_budget_is_bounded(self):
        path = self.manifest({"unit": ["{python}", "-c", "pass"]})
        content = json.loads(path.read_text(encoding="utf-8"))
        content["output_budget"] = 65_537
        path.write_text(json.dumps(content), encoding="utf-8")
        with self.assertRaises(ValueError):
            run_matrix(path, root=self.root)

    def test_portable_id_secret_runtime_exclusion_and_failure_stop(self):
        manifest = self.manifest({"build": ["{python}", "-c", "raise SystemExit(1)"],
                                  "unit": ["{python}", "-c", "print('must not run')"]})
        (self.app / ".env.local").write_text("secret", encoding="utf-8")
        (self.app / "__pycache__").mkdir()
        (self.app / "__pycache__" / "generated.pyc").write_bytes(b"runtime")
        result = run_matrix(manifest, root=self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(list(result["phases"]), ["build"])
        self.assertNotIn(".env.local", {item["path"] for item in result["source_files"]})
        self.assertNotIn("__pycache__/generated.pyc", {item["path"] for item in result["source_files"]})
        content = json.loads(manifest.read_text(encoding="utf-8"))
        content["id"] = "../escape"
        manifest.write_text(json.dumps(content), encoding="utf-8")
        with self.assertRaises(ValueError):
            package_app(manifest, root=self.root)

    def test_duplicate_phases_and_deep_manifest_are_rejected(self):
        path = self.manifest({"unit": ["{python}", "-c", "pass"]})
        with self.assertRaises(ValueError):
            run_matrix(path, root=self.root, phases=["unit", "unit"])
        path.write_text("[" * 65 + "0" + "]" * 65, encoding="utf-8")
        with self.assertRaises(ValueError):
            run_matrix(path, root=self.root)

    def test_workspace_placeholder_path_cannot_escape_declared_root(self):
        path = self.manifest({"unit": ["{python}", "-c", "pass", "{root}/../outside.txt"]})
        with self.assertRaisesRegex(ValueError, "escapes root"):
            run_matrix(path, root=self.root, phases=["unit"])
        path = self.manifest({"unit": ["{python}", "-c", "pass", "--output={build}/evidence.txt"]})
        self.assertEqual(run_matrix(path, root=self.root, phases=["unit"])["status"], "PASS")

    def test_sensitive_configuration_is_reported_excluded_and_known_content_refuses_package(self):
        for name in (".npmrc", ".pypirc", ".netrc", "credentials-prod.json", "release-secret.json", "service-account.json", "deploy.pem"):
            (self.app / name).write_text("excluded", encoding="utf-8")
        (self.app / ".aws").mkdir()
        (self.app / ".aws" / "credentials").write_text("excluded", encoding="utf-8")
        delivery = package_app(self.manifest({}), root=self.root)
        excluded = {item["path"] for item in delivery["excluded_sources"]}
        self.assertTrue({".npmrc", ".pypirc", ".netrc", "credentials-prod.json", "release-secret.json", "service-account.json", "deploy.pem", ".aws/"} <= excluded)
        (self.app / "leaked.txt").write_text("-----BEGIN PRIVATE KEY-----\nnot-a-real-key", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, r"sensitive source content \(pem_private_key\)"):
            package_app(self.manifest({}), root=self.root)
        (self.app / "leaked.txt").unlink()
        (self.app / "auth.txt").write_text("Authorization: Bearer SYNTHETIC_NOT_REAL_123", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, r"sensitive source content \(bearer_token\)") as caught:
            package_app(self.manifest({}), root=self.root)
        self.assertNotIn("SYNTHETIC_NOT_REAL_123", str(caught.exception))

    def test_package_rejects_source_drift_after_verified_snapshot(self):
        manifest = self.manifest({})
        from rd_platform.stack_harness import _source_manifest

        def mutate_after_snapshot(app, **kwargs):
            snapshot = _source_manifest(app, **kwargs)
            (self.app / "main.py").write_text("changed after snapshot\n", encoding="utf-8")
            return snapshot

        with patch("rd_platform.stack_harness._source_manifest", side_effect=mutate_after_snapshot):
            with self.assertRaisesRegex(ValueError, "source changed after snapshot"):
                package_app(manifest, root=self.root)
        self.assertEqual((self.app / "main.py").read_text(encoding="utf-8"), "changed after snapshot\n")
        self.assertEqual(list((self.root / ".rd-platform" / "deliveries").glob("*")), [])

    def test_probe_reports_all_contract_tools(self):
        self.assertEqual(set(probe_tools()), {"python", "node", "java", "javac", "cxx"})


if __name__ == "__main__":
    unittest.main()
