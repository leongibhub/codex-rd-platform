"""Independent CLI-level verification for TASK-V3-002.

These tests derive from REQ-V3-010 / NFR-V3-004 and the public stack-harness
contract.  They deliberately do not reuse the implementation test helpers.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from rd_platform.stack_harness import package_app, run_matrix


class IndependentStackHarnessTests(unittest.TestCase):
    """TC-V3-IND-201..211 / TASK-V3-002."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ind-v3-stack-")
        self.root = Path(self.temp.name)
        self.app = self.root / "trusted_app"
        self.app.mkdir()
        (self.app / "source.txt").write_text("source-v1\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, commands, **overrides):
        document = {
            "schema_version": 1,
            "id": "independent-demo",
            "stack": "python",
            "requirements": ["REQ-V3-010"],
            "commands": commands,
            "native_validation": "none",
            "entrypoint": "source.txt",
        }
        document.update(overrides)
        path = self.app / "manifest.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "rd_platform", *arguments],
            # The CLI is launched from the installed repository, while every
            # manifest/root under test remains in the isolated temp directory.
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )

    def test_tc_v3_ind_201_cli_probe_returns_all_observed_tools_without_state(self):
        untouched_db = self.root / "unused.db"
        result = self.run_cli("--db", str(untouched_db), "stack-probe")
        self.assertEqual(result.returncode, 0, result.stderr)
        observation = json.loads(result.stdout)
        self.assertEqual(set(observation), {"python", "node", "java", "javac", "cxx"})
        self.assertFalse(untouched_db.exists(), "probe must not initialize platform state")

    def test_tc_v3_ind_202_cli_executes_literal_argv_not_a_shell_command(self):
        sentinel = self.root / "must-not-exist"
        manifest = self.write_manifest({
            "unit": [
                "{python}", "-c", "import sys; print(sys.argv[1])",
                "literal; echo injected > " + str(sentinel),
            ]
        })
        result = self.run_cli("stack-run", str(manifest), "--root", str(self.root), "--phase", "unit")
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["status"], "PASS")
        self.assertIn("literal; echo injected", evidence["phases"]["unit"]["stdout"])
        self.assertFalse(sentinel.exists(), "argv text must not be interpreted by a shell")

    def test_tc_v3_ind_203_missing_tool_and_omitted_phase_are_not_pass(self):
        missing_tool = self.write_manifest({"unit": ["{node}", "-e", "process.exit(0)"]})
        result = run_matrix(missing_tool, root=self.root, tools={"node": None}, phases=["unit"])
        self.assertEqual(result["status"], "NOT_AVAILABLE")
        self.assertEqual(result["phases"]["unit"]["status"], "NOT_AVAILABLE")

        omitted = self.write_manifest({})
        result = run_matrix(omitted, root=self.root, phases=["integration"])
        self.assertEqual(result["status"], "NOT_EXECUTED")
        self.assertEqual(result["phases"]["integration"]["status"], "NOT_EXECUTED")

    def test_tc_v3_ind_204_failure_precedes_not_executed_and_stops_later_phase(self):
        manifest = self.write_manifest({
            "unit": ["{python}", "-c", "raise SystemExit(17)"],
            "integration": ["{python}", "-c", "raise SystemExit(99)"],
        })
        result = run_matrix(manifest, root=self.root)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["phases"]["build"]["status"], "NOT_EXECUTED")
        self.assertEqual(result["phases"]["unit"]["exit_code"], 17)
        self.assertNotIn("integration", result["phases"], "execution must stop after first actual failure")

    def test_tc_v3_ind_205_cli_rejects_manifest_outside_declared_root(self):
        outside = self.root.parent / (self.root.name + "-outside")
        outside.mkdir(exist_ok=True)
        try:
            manifest = outside / "manifest.json"
            manifest.write_text(json.dumps({"schema_version": 1, "id": "outside", "commands": {}}), encoding="utf-8")
            result = self.run_cli("stack-run", str(manifest), "--root", str(self.root))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest escapes root", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        finally:
            manifest.unlink(missing_ok=True)
            outside.rmdir()

    def test_tc_v3_ind_206_rejects_malicious_ids_and_duplicate_phases(self):
        for malicious_id in ("../escape", "nested/path", ".", "a b", "a;cmd"):
            with self.subTest(malicious_id=malicious_id):
                manifest = self.write_manifest({"unit": ["{python}", "-c", "pass"]}, id=malicious_id)
                with self.assertRaisesRegex(ValueError, "portable single path component"):
                    run_matrix(manifest, root=self.root, phases=["unit"])
        manifest = self.write_manifest({"unit": ["{python}", "-c", "pass"]})
        with self.assertRaisesRegex(ValueError, "phases must be selected"):
            run_matrix(manifest, root=self.root, phases=["unit", "unit"])

    def test_tc_v3_ind_207_rejects_symlink_in_source_tree(self):
        external = self.root / "external.txt"
        external.write_text("external", encoding="utf-8")
        link = self.app / "linked.txt"
        try:
            os.symlink(external, link)
        except (NotImplementedError, OSError) as error:
            self.skipTest(f"cannot create symlink in this environment: {type(error).__name__}")
        manifest = self.write_manifest({})
        with self.assertRaisesRegex(ValueError, "source symlinks or junctions"):
            package_app(manifest, root=self.root)

    def test_tc_v3_ind_208_package_excludes_runtime_and_secret_material(self):
        (self.app / ".env.production").write_text("token=do-not-package", encoding="utf-8")
        (self.app / "my_private_key.pem").write_text("do-not-package", encoding="utf-8")
        (self.app / ".npmrc").write_text("//registry.example/:_authToken=do-not-package", encoding="utf-8")
        (self.app / "credentials.json").write_text('{"token":"do-not-package"}', encoding="utf-8")
        (self.app / "id_rsa").write_text("do-not-package", encoding="utf-8")
        for directory, filename in (("node_modules", "library.js"), ("build", "generated.bin"), ("__pycache__", "cached.pyc")):
            target = self.app / directory
            target.mkdir()
            (target / filename).write_text("do-not-package", encoding="utf-8")
        manifest = self.write_manifest({})
        delivery = package_app(manifest, root=self.root)
        with zipfile.ZipFile(delivery["archive"]) as archive:
            names = archive.namelist()
        self.assertIn("source.txt", names)
        self.assertIn("manifest.json", names)
        for prohibited in (".env.production", "my_private_key.pem", ".npmrc", "credentials.json", "id_rsa", "node_modules/library.js", "build/generated.bin", "__pycache__/cached.pyc"):
            self.assertNotIn(prohibited, names)

    def test_tc_v3_ind_209_package_is_byte_deterministic_after_source_timestamp_change(self):
        manifest = self.write_manifest({})
        first = package_app(manifest, root=self.root)
        first_bytes = Path(first["archive"]).read_bytes()
        os.utime(self.app / "source.txt", (1_700_000_000, 1_700_000_000))
        second = package_app(manifest, root=self.root)
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertEqual(first_bytes, Path(second["archive"]).read_bytes())

    def test_tc_v3_ind_210_delivery_overwrite_protection_preserves_tampered_archive(self):
        manifest = self.write_manifest({})
        delivery = package_app(manifest, root=self.root)
        archive = Path(delivery["archive"])
        archive.write_bytes(b"tampered archive")
        with self.assertRaisesRegex(ValueError, "refusing to overwrite existing delivery archive"):
            package_app(manifest, root=self.root)
        self.assertEqual(archive.read_bytes(), b"tampered archive")

    def test_tc_v3_ind_211_root_placeholder_path_escape_is_rejected(self):
        """NFR-V3-004: a resolved workspace-path placeholder cannot escape root."""
        escaped = self.root.parent / "outside-target.txt"
        manifest = self.write_manifest({
            "unit": ["{python}", "-c", "pass", "{root}/../outside-target.txt"]
        })
        with self.assertRaisesRegex(ValueError, "escapes root"):
            run_matrix(manifest, root=self.root, phases=["unit"])
        self.assertFalse(escaped.exists())

    def test_tc_v3_ind_212_package_refuses_source_change_between_hash_and_archive_read(self):
        """TOCTOU: delivered bytes must equal the previously declared source hash."""
        manifest = self.write_manifest({})
        source = self.app / "source.txt"
        original_read_bytes = Path.read_bytes
        reads = 0

        def mutate_after_hash(path):
            nonlocal reads
            if Path(path).resolve() == source.resolve():
                reads += 1
                if reads == 1:
                    return b"version-used-for-hash\n"
                return b"version-written-to-archive\n"
            return original_read_bytes(path)

        with patch("pathlib.Path.read_bytes", new=mutate_after_hash):
            with self.assertRaisesRegex(ValueError, "source changed|source hash|source content"):
                package_app(manifest, root=self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
