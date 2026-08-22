import json
import shutil
import subprocess
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.platform_validation import validate_runtime_prerequisites
from scripts.validate_platform import validate_platform


ROOT = Path(__file__).resolve().parents[2]


class ValidatorContractTests(unittest.TestCase):
    def test_full_validation_runs_runtime_and_passes_template_mode(self):
        report = validate_platform(ROOT)

        self.assertTrue(report.ok, report.issues)
        self.assertTrue(report.runtime_executed)
        self.assertEqual(report.lifecycle_mode, "template")
        self.assertEqual(report.evaluated_gates, [])

    def test_static_only_never_claims_full_runtime_pass(self):
        report = validate_platform(ROOT, static_only=True)

        self.assertTrue(report.ok, report.issues)
        self.assertFalse(report.runtime_executed)

    def test_cli_reports_template_mode_without_gate_pass(self):
        completed = subprocess.run(
            [sys.executable, "scripts/validate_platform.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PLATFORM VALIDATION: PASS (TEMPLATE MODE)", completed.stdout)
        self.assertIn("Evaluated Gates: NONE", completed.stdout)

    def test_static_only_cli_reports_runtime_not_executed_without_full_pass(self):
        completed = subprocess.run(
            [sys.executable, "scripts/validate_platform.py", "--static-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("STATIC VALIDATION: PASS (TEMPLATE MODE)", completed.stdout)
        self.assertIn("RUNTIME CHECK: NOT EXECUTED", completed.stdout)
        self.assertNotIn("PLATFORM VALIDATION: PASS", completed.stdout)

    def test_manifest_break_returns_stable_error_code(self):
        with self._temporary_root() as root:
            manifest_path = root / "platform-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["agents"] = ["wrong-agent"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            report = validate_platform(root, static_only=True)

            self.assertIn("MANIFEST_AGENTS_MISMATCH", self._codes(report))

    def test_gate_template_break_returns_stable_error_code(self):
        with self._temporary_root() as root:
            template = root / "templates" / "gate-register-template.md"
            template.write_text(
                template.read_text(encoding="utf-8").replace(
                    "| G11 | Project Closure |", "| REMOVED | Project Closure |"
                ),
                encoding="utf-8",
            )

            self.assertIn(
                "GOVERNANCE_GATE_TEMPLATE_INVALID",
                self._codes(validate_platform(root, static_only=True)),
            )

    def test_rtm_header_break_returns_stable_error_code(self):
        with self._temporary_root() as root:
            rtm = root / "docs" / "03-requirements" / "requirement-traceability-matrix.md"
            rtm.write_text(
                rtm.read_text(encoding="utf-8").replace("Last Verified", "Verified On"),
                encoding="utf-8",
            )

            self.assertIn(
                "GOVERNANCE_RTM_HEADER_INVALID",
                self._codes(validate_platform(root, static_only=True)),
            )

    def test_git_repository_without_head_returns_stable_error_code(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)

            report = validate_platform(root, static_only=True)

            self.assertIn("GIT_INVALID", self._codes(report))

    def test_dirty_git_is_warning_unless_strict(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "validator@example.test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Validator Test"], check=True)
            tracked = root / "tracked.txt"
            tracked.write_text("initial\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
            tracked.write_text("dirty\n", encoding="utf-8")

            default_report = validate_platform(root, static_only=True)
            strict_report = validate_platform(root, static_only=True, strict=True)

            self.assertEqual([warning for warning in default_report.warnings], ["Git working tree is dirty"])
            self.assertNotIn("GIT_DIRTY", self._codes(default_report))
            self.assertIn("GIT_DIRTY", self._codes(strict_report))

    def test_runtime_rejects_unsupported_python_version(self):
        with patch("scripts.platform_validation.sys.version_info", (3, 10, 0)):
            self.assertEqual(
                self._codes(validate_runtime_prerequisites(ROOT)),
                ["PYTHON_VERSION_UNSUPPORTED"],
            )

    def test_runtime_rejects_unsupported_mcp_major_versions(self):
        for version in ("1.9.9", "3.0.0"):
            with self.subTest(version=version), patch(
                "scripts.platform_validation.importlib_metadata.version", return_value=version
            ):
                self.assertEqual(
                    self._codes(validate_runtime_prerequisites(ROOT)),
                    ["MCP_VERSION_UNSUPPORTED"],
                )

    def test_runtime_rejects_missing_or_invalid_mcp_version(self):
        with patch(
            "scripts.platform_validation.importlib_metadata.version",
            side_effect=ModuleNotFoundError,
        ):
            self.assertEqual(
                self._codes(validate_runtime_prerequisites(ROOT)),
                ["MCP_VERSION_UNSUPPORTED"],
            )
        with patch(
            "scripts.platform_validation.importlib_metadata.version", return_value="not-a-version"
        ):
            self.assertEqual(
                self._codes(validate_runtime_prerequisites(ROOT)),
                ["MCP_VERSION_UNSUPPORTED"],
            )

    def test_runtime_rejects_requirements_without_exact_mcp_bounds(self):
        with self._temporary_root() as root:
            requirements = root / "tools" / "mcp" / "company-context" / "requirements.txt"
            requirements.write_text("mcp>=2.0.0\n", encoding="utf-8")

            self.assertIn(
                "MCP_REQUIREMENT_INVALID",
                self._codes(validate_runtime_prerequisites(root)),
            )

    @staticmethod
    def _codes(report):
        return [issue.code for issue in report.issues] if hasattr(report, "issues") else [issue.code for issue in report]

    @contextmanager
    def _temporary_root(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            shutil.copytree(
                ROOT,
                root,
                ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"),
            )
            yield root


if __name__ == "__main__":
    unittest.main()
