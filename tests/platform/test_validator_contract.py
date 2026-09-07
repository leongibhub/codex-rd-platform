import json
import io
import shutil
import subprocess
import sys
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.platform_validation import _has_mcp_v2_bounds, ValidationIssue, validate_runtime_prerequisites
from scripts import validate_platform as validator_cli
from scripts.validate_platform import validate_platform


ROOT = Path(__file__).resolve().parents[2]


class ValidatorContractTests(unittest.TestCase):
    def test_fixture_copies_source_without_live_runtime_state(self):
        # Parallel lifecycle tests create/remove state underneath .rd-platform.
        # Validator fixtures need the source contracts, never this live state.
        with TemporaryDirectory() as directory:
            source = Path(directory)
            (source / '.rd-platform').mkdir()
            (source / '.rd-platform' / 'transient.db').write_bytes(b'fixture')
            (source / 'source-contract.txt').write_text('keep', encoding='utf-8')
            with patch.dict(self._temporary_root.__wrapped__.__globals__, ROOT=source):
                with self._temporary_root() as copied:
                    self.assertEqual('keep', (copied / 'source-contract.txt').read_text(encoding='utf-8'))
                    self.assertFalse((copied / '.rd-platform').exists())

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

    def test_static_only_runs_runtime_prerequisites_without_stdio(self):
        with patch("scripts.validate_platform.validate_runtime_prerequisites", return_value=[
            ValidationIssue("MCP_VERSION_UNSUPPORTED", "installed MCP version is unsupported")
        ]) as prerequisites, patch("scripts.validate_platform.importlib.import_module") as health_import:
            report = validate_platform(ROOT, static_only=True)

        self.assertIn("MCP_VERSION_UNSUPPORTED", self._codes(report))
        self.assertFalse(report.runtime_executed)
        prerequisites.assert_called_once_with(ROOT)
        health_import.assert_not_called()

    def test_static_only_reports_prerequisite_failures_without_runtime_execution(self):
        cases = (
            ("PYTHON_VERSION_UNSUPPORTED", "scripts.platform_validation.sys.version_info", (3, 10, 0)),
            ("MCP_VERSION_UNSUPPORTED", "scripts.platform_validation.importlib_metadata.version", ModuleNotFoundError()),
            ("MCP_VERSION_UNSUPPORTED", "scripts.platform_validation.importlib_metadata.version", "3.0.0"),
        )
        for expected, target, replacement in cases:
            with self.subTest(expected=expected), patch(target, side_effect=replacement) if isinstance(replacement, Exception) else patch(target, return_value=replacement):
                report = validate_platform(ROOT, static_only=True)
                self.assertIn(expected, self._codes(report))
                self.assertFalse(report.runtime_executed)

    def test_static_only_reports_invalid_requirements_without_runtime_execution(self):
        with self._temporary_root() as root:
            requirements = root / "tools" / "mcp" / "company-context" / "requirements.txt"
            requirements.write_text("mcp>=2.0.0\n", encoding="utf-8")

            report = validate_platform(root, static_only=True)

            self.assertIn("MCP_REQUIREMENT_INVALID", self._codes(report))
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

    def test_static_only_cli_returns_one_for_prerequisite_issue_without_stdio(self):
        stdout = io.StringIO()
        with patch("scripts.validate_platform.validate_runtime_prerequisites", return_value=[
            ValidationIssue("MCP_REQUIREMENT_INVALID", "MCP dependency requirement is invalid")
        ]), redirect_stdout(stdout):
            exit_code = validator_cli.main(["--static-only"])

        self.assertEqual(exit_code, 1)
        self.assertIn("MCP_REQUIREMENT_INVALID", stdout.getvalue())
        self.assertIn("RUNTIME CHECK: NOT EXECUTED", stdout.getvalue())

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

    def test_runtime_accepts_split_spaced_comments_and_supported_pep440_subset(self):
        with self._temporary_root() as root:
            requirements = root / "tools" / "mcp" / "company-context" / "requirements.txt"
            requirements.write_text("mcp >= 2.0.0  # minimum\nmcp < 3.0.0\n", encoding="utf-8")
            for version in ("2.0.0", "2.0.0+vendor.1", "2.0.0.post1", "2.0.0.1"):
                with self.subTest(version=version), patch(
                    "scripts.platform_validation.importlib_metadata.version", return_value=version
                ):
                    self.assertEqual(validate_runtime_prerequisites(root), [])

    def test_runtime_rejects_prerelease_and_unsatisfiable_or_indirect_requirements(self):
        with patch("scripts.platform_validation.importlib_metadata.version", return_value="2.0.0rc1"):
            self.assertEqual(self._codes(validate_runtime_prerequisites(ROOT)), ["MCP_VERSION_UNSUPPORTED"])
        for contents in ("mcp>=2.0.0\nmcp<3.0.0\nmcp>=3.0.0\n", "-r constraints.txt\nmcp>=2.0.0,<3.0.0\n"):
            with self.subTest(contents=contents), self._temporary_root() as root:
                (root / "tools" / "mcp" / "company-context" / "requirements.txt").write_text(contents, encoding="utf-8")
                self.assertEqual(self._codes(validate_runtime_prerequisites(root)), ["MCP_REQUIREMENT_INVALID"])

    def test_runtime_rejects_all_indirect_requirement_forms(self):
        for directive in (
            "-rconstraints.txt", "-r constraints.txt", "--requirement constraints.txt", "--requirement=constraints.txt",
            "-cconstraints.txt", "-c constraints.txt", "--constraint constraints.txt", "--constraint=constraints.txt",
        ):
            with self.subTest(directive=directive):
                contents = f"mcp>=2.0.0,<3.0.0\n{directive}\n"
                self.assertFalse(_has_mcp_v2_bounds(contents))

    def test_runtime_rejects_bom_prefixed_indirect_requirement(self):
        with self._temporary_root() as root:
            requirements = root / "tools" / "mcp" / "company-context" / "requirements.txt"
            requirements.write_bytes(b"\xef\xbb\xbf-r constraints.txt\nmcp>=2.0.0,<3.0.0\n")

            self.assertEqual(
                self._codes(validate_runtime_prerequisites(root)),
                ["MCP_REQUIREMENT_INVALID"],
            )

    def test_runtime_ignores_similar_distribution_names_but_accepts_exact_mcp(self):
        contents = "mcp-tools>=1.0\nmcp_sdk>=1.0\nmcp>=2.0.0,<3.0.0\n"

        self.assertTrue(_has_mcp_v2_bounds(contents))

    def test_runtime_rejects_pathological_numeric_versions_without_exception(self):
        versions = (
            "2." + "9" * 1000 + ".0",
            ".".join(["2"] * 100),
            "2.0.0.post" + "9" * 1000,
            "2.0.0+bad..local",
        )
        for version in versions:
            with self.subTest(version=version), patch(
                "scripts.platform_validation.importlib_metadata.version", return_value=version
            ):
                self.assertEqual(
                    self._codes(validate_runtime_prerequisites(ROOT)),
                    ["MCP_VERSION_UNSUPPORTED"],
                )

    def test_runtime_rejects_undecodable_requirements_without_leaking_error(self):
        with self._temporary_root() as root:
            requirements = root / "tools" / "mcp" / "company-context" / "requirements.txt"
            requirements.write_bytes(b"mcp>=2.0.0,<3.0.0\xffAuthorization: sentinel")

            issues = validate_runtime_prerequisites(root)

            self.assertEqual(self._codes(issues), ["MCP_REQUIREMENT_INVALID"])
            self.assertNotIn("sentinel", issues[0].message)

    def test_runtime_health_import_and_call_fail_closed_without_secret_leakage(self):
        sentinel = "Authorization: Token private-path-sentinel"
        with patch("scripts.validate_platform.importlib.import_module", side_effect=RuntimeError(sentinel)):
            import_report = validate_platform(ROOT)
        self.assertEqual(self._codes(import_report)[-1], "MCP_HEALTH_IMPORT_FAILED")
        self.assertFalse(import_report.runtime_executed)
        health = type("Health", (), {"check_company_context": staticmethod(lambda root: (_ for _ in ()).throw(RuntimeError(sentinel)))})
        with patch("scripts.validate_platform.importlib.import_module", return_value=health):
            call_report = validate_platform(ROOT)
        self.assertEqual(self._codes(call_report)[-1], "MCP_HEALTH_CHECK_FAILED")
        self.assertTrue(call_report.runtime_executed)
        self.assertNotIn("private-path-sentinel", " ".join(issue.message for issue in call_report.issues))

    def test_cli_unexpected_exception_is_sanitized(self):
        sentinel = "Authorization: Token private-path-sentinel"
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("scripts.validate_platform.validate_platform", side_effect=RuntimeError(sentinel)), redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = validator_cli.main([])

        self.assertEqual(exit_code, 1)
        self.assertIn("VALIDATION_INTERNAL_ERROR", stdout.getvalue())
        self.assertNotIn("private-path-sentinel", stdout.getvalue() + stderr.getvalue())

    def test_active_report_lists_only_decided_gate_register_rows(self):
        with self._temporary_root() as root:
            manifest_path = root / "platform-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["lifecycle_mode"] = "active"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            register = root / manifest["active_gate_register"]
            register.parent.mkdir(parents=True, exist_ok=True)
            register.write_text(self._active_register(("DECIDED", "IN_REVIEW", "NOT_EVALUATED")), encoding="utf-8")

            report = validate_platform(root, static_only=True)

            self.assertEqual(report.evaluated_gates, ["G0", "G3", "G6", "G9"])

    @staticmethod
    def _codes(report):
        return [issue.code for issue in report.issues] if hasattr(report, "issues") else [issue.code for issue in report]

    @staticmethod
    def _active_register(states):
        headers = [
            "Gate ID", "Gate Name", "Gate Status", "Evaluation State", "Baseline", "Evaluated At", "Evaluator Role", "Recorder",
            "Criteria Result", "Evidence IDs", "Blockers/Links", "Rationale", "Next Action", "Owner", "Target Date", "Human Approval Evidence",
        ]
        lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        for index in range(12):
            lines.append("| " + " | ".join([f"G{index}", f"Gate {index}", "BLOCKED", states[index % len(states)]] + [""] * 12) + " |")
        return "\n".join(lines) + "\n"

    @contextmanager
    def _temporary_root(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            shutil.copytree(
                ROOT,
                root,
                ignore=shutil.ignore_patterns(".git", ".venv", ".rd-platform", "__pycache__", ".pytest_cache"),
            )
            yield root


if __name__ == "__main__":
    unittest.main()
