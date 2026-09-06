"""Independent CI-build regressions for TASK-V3-012 and TASK-V3-013.

The Java checks use a new temporary workspace and invoke the documented
``stack-run`` CLI.  Native compiler execution is deliberately not simulated:
an online Windows workflow result is required before it can be called native
validation evidence.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rd_platform.stack_harness import probe_tools


ROOT = Path(__file__).resolve().parents[2]
JAVA_APP = ROOT / "examples" / "multistack" / "java_booking"


def file_snapshot(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()
    }


class IndependentCiBuildTests(unittest.TestCase):
    """TC-CI-IND-1201..1205 / REQ-MATRIX-JAVA, TASK-V3-012/013."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ind-ci-build-")
        self.workspace = Path(self.temporary.name) / "workspace"
        self.app = self.workspace / "examples" / "multistack" / "java_booking"
        self.app.parent.mkdir(parents=True)
        shutil.copytree(JAVA_APP, self.app, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.class", ".rd-platform"))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def stack_cli(self, *arguments: str, timeout: float = 120) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "rd_platform", "stack-run", str(self.app / "manifest.json"),
             "--root", str(self.workspace), *arguments],
            cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=timeout, check=False,
        )

    def build_cli(self, compiler: str, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(self.app / "build.py"), "--javac", compiler, "--build", str(target)],
            cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=120, check=False,
        )

    def require_real_java8(self) -> dict:
        tools = probe_tools()
        for name in ("javac", "java"):
            self.assertEqual("AVAILABLE", tools[name]["status"], f"{name} is NOT_AVAILABLE; this is not a Java 8 PASS")
            observed = subprocess.run([tools[name]["path"], "-version"], text=True, encoding="utf-8", capture_output=True, timeout=20, check=False)
            self.assertEqual(0, observed.returncode, observed.stderr)
            self.assertRegex(observed.stdout + observed.stderr, r"(?:javac |version \"?)1\.8\.")
        return tools

    def test_tc_ci_ind_1201_clean_java8_cli_build_unit_integration_preserves_source(self) -> None:
        """Functional/regression: an absent classes directory is created only under the workspace build root."""
        self.require_real_java8()
        before = file_snapshot(self.app)
        classes = self.workspace / ".rd-platform" / "build" / "java_booking" / "classes"
        self.assertFalse(classes.exists())
        completed = self.stack_cli()
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(["PASS", "PASS", "PASS"], [result["phases"][phase]["status"] for phase in ("build", "unit", "integration")])
        self.assertTrue((classes / "booking" / "BookingCli.class").is_file())
        self.assertTrue((classes / "booking" / "BookingStoreTest.class").is_file())
        self.assertEqual(before, file_snapshot(self.app), "build must not alter copied Java source")
        self.assertFalse(list(self.app.rglob("*.class")), "classes must not be written into the app source")

    def test_tc_ci_ind_1202_java_driver_rejects_outside_and_parent_build_targets(self) -> None:
        """Security: the Java build helper rejects traversal/outside targets before compiler execution."""
        compiler = self.require_real_java8()["javac"]["path"]
        safe_root = self.workspace / ".rd-platform" / "build"
        forbidden = (self.workspace, self.workspace / "examples" / "outside", self.workspace.parent / "outside",
                     safe_root, safe_root / "allowed" / ".." / "escaped", Path("relative-output"))
        for target in forbidden:
            with self.subTest(target=str(target)):
                rejected = self.build_cli(compiler, target)
                self.assertNotEqual(0, rejected.returncode)
                self.assertIn("build path", rejected.stderr)
        self.assertFalse((self.workspace.parent / "outside").exists())

    def test_tc_ci_ind_1203_java_driver_rejects_linked_build_ancestor(self) -> None:
        """Security/reliability: a symlink or Windows junction cannot redirect generated classes."""
        driver = importlib.import_module("examples.multistack.java_booking.build")
        build = self.workspace / ".rd-platform" / "build"
        classes = build / "java" / "classes"
        classes.mkdir(parents=True)
        outside = self.workspace / "outside"
        outside.mkdir()
        linked = classes / "booking"
        try:
            linked.symlink_to(outside, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            junction = subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(outside)], capture_output=True, timeout=20, check=False)
            diagnostic = (junction.stdout or b"").decode("mbcs", errors="replace") + (junction.stderr or b"").decode("mbcs", errors="replace")
            self.assertEqual(0, junction.returncode, diagnostic)
        with patch.object(driver, "ROOT", self.workspace):
            with self.assertRaisesRegex(ValueError, "symlink|junction|reparse"):
                driver.classes_directory(classes.parent)
        self.assertEqual([], list(outside.iterdir()))

    def test_tc_ci_ind_1204_current_os_java_home_uses_native_executable_name(self) -> None:
        """Compatibility: each real CI OS resolves its own JAVA_HOME binary spelling."""
        module_root = str(ROOT)
        code = "\n".join((
            "import os, sys, tempfile",
            "from pathlib import Path",
            f"sys.path.insert(0, {module_root!r})",
            "from rd_platform.stack_harness import _java_tool",
            "with tempfile.TemporaryDirectory() as directory:",
            "    home = Path(directory) / 'jdk'",
            "    candidate = home / 'bin' / ('java.exe' if os.name == 'nt' else 'java')",
            "    candidate.parent.mkdir(parents=True)",
            "    candidate.touch()",
            "    os.environ['JAVA_HOME'] = str(home)",
            "    assert _java_tool('java') == candidate, _java_tool('java')",
        ))
        completed = subprocess.run([sys.executable, "-c", code], text=True, encoding="utf-8", capture_output=True, timeout=30, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_tc_ci_ind_1205_native_probe_and_workflow_do_not_claim_unobserved_windows_execution(self) -> None:
        """Contract: probe reports availability only; the workflow requires DLL setup but no local run proves native PASS."""
        probe = subprocess.run([sys.executable, "-m", "rd_platform", "stack-probe"], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=30, check=False)
        self.assertEqual(0, probe.returncode, probe.stderr)
        tools = json.loads(probe.stdout)
        self.assertEqual({"python", "node", "java", "javac", "cxx"}, set(tools))
        self.assertIn(tools["cxx"]["status"], {"AVAILABLE", "NOT_AVAILABLE"})
        if tools["cxx"]["status"] == "AVAILABLE":
            self.assertTrue(Path(tools["cxx"]["path"]).is_file())
        workflow = (ROOT / ".github" / "workflows" / "platform-validation.yml").read_text(encoding="utf-8")
        self.assertIn("Get-Command g++.exe", workflow)
        self.assertIn("-print-file-name=libstdc++-6.dll", workflow)
        self.assertIn("$env:GITHUB_PATH", workflow)
        self.assertNotIn("continue-on-error", workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
