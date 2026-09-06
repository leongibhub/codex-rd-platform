"""REQ-MATRIX-JAVA: clean Java 8 build plus bounded-output driver contracts."""
import hashlib
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from rd_platform.stack_harness import probe_tools, run_matrix


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "examples/multistack/java_booking"


class JavaCleanBuildTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / ".rd-platform"
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="java clean build ", dir=base)
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def driver(self):
        return importlib.import_module("examples.multistack.java_booking.build")

    def link_directory(self, linked, target):
        try:
            linked.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            # Windows junction creation does not need a symlink privilege.
            # cmd's code page can differ in a hidden Runtime process from the
            # caller's Python -X utf8 mode. Capture bytes so diagnostic decoding
            # cannot fail in subprocess reader threads before checking exit.
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(linked), str(target)],
                                    capture_output=True, check=False)
            diagnostic = (result.stdout + result.stderr).decode("mbcs", errors="replace")
            self.assertEqual(result.returncode, 0, diagnostic)

    @unittest.skipUnless(os.name == "nt", "Windows junction permission-fallback contract")
    def test_permission_denied_symlink_falls_back_to_actual_junction(self):
        outside = self.root / "真实 junction target"
        outside.mkdir()
        linked = self.root / "真实 junction link"
        # Only the missing privilege is simulated. mklink itself and the
        # filesystem junction are real, before any compiler/subprocess mock.
        with patch.object(Path, "symlink_to", side_effect=PermissionError(1314, "Synthetic missing symlink privilege")):
            self.link_directory(linked, outside)
        self.assertTrue(linked.is_dir())
        self.assertTrue(getattr(linked.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)
        self.assertEqual(linked.resolve(), outside.resolve())

    def test_real_java8_manifest_build_from_absent_classes_then_unit_and_integration(self):
        tools = probe_tools()
        if any(tools[tool]["status"] != "AVAILABLE" for tool in ("javac", "java")):
            self.skipTest("NOT_AVAILABLE: real Java 8 compiler/runtime required")
        versions = {tool: subprocess.run([tools[tool]["path"], "-version"], capture_output=True, text=True, check=False)
                    for tool in ("javac", "java")}
        for tool, completed in versions.items():
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertRegex(completed.stdout + completed.stderr, r"(?:javac |version \"?)1\.8\.",
                             "This regression must run against a real Java 8 JDK/runtime")
        copied = self.root / "examples/multistack/java_booking"
        shutil.copytree(APP, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.class"))
        sources = {p.relative_to(copied): hashlib.sha256(p.read_bytes()).hexdigest() for p in copied.rglob("*") if p.is_file()}
        classes = self.root / ".rd-platform/build/java_booking/classes"
        self.assertFalse(classes.exists())
        result = run_matrix(copied / "manifest.json", root=self.root,
                            tools={tool: info["path"] for tool, info in tools.items()})
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual([result["phases"][phase]["status"] for phase in ("build", "unit", "integration")], ["PASS", "PASS", "PASS"], result)
        for phase in ("unit", "integration"):
            self.assertRegex(result["phases"][phase]["stdout"], r"[1-9][0-9]* assertions passed")
        self.assertTrue((classes / "booking/BookingCli.class").is_file())
        self.assertEqual(int.from_bytes((classes / "booking/BookingCli.class").read_bytes()[6:8], "big"), 52)
        self.assertTrue((classes / "booking/BookingStoreTest.class").is_file())
        self.assertFalse(list(copied.rglob("*.class")))
        self.assertEqual(sources, {p.relative_to(copied): hashlib.sha256(p.read_bytes()).hexdigest() for p in copied.rglob("*") if p.is_file()})

    def test_real_compiler_failure_does_not_run_or_pass_downstream_phases(self):
        tools = probe_tools()
        if tools["javac"]["status"] != "AVAILABLE":
            self.skipTest("NOT_AVAILABLE: real compiler required for failing-build integration")
        copied = self.root / "examples/multistack/java_booking"
        shutil.copytree(APP, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.class"))
        (copied / "src/booking/Booking.java").write_text("deliberately invalid Java fixture\n", encoding="utf-8")
        result = run_matrix(copied / "manifest.json", root=self.root,
                            tools={tool: info["path"] for tool, info in tools.items()})
        self.assertEqual(result["status"], "FAIL", result)
        self.assertNotEqual(result["phases"]["build"]["exit_code"], 0)
        self.assertEqual(set(result["phases"]), {"build"})
        self.assertFalse(list(copied.rglob("*.class")))

    def test_public_driver_rejects_escaping_target_without_creating_it(self):
        target = self.root / "source-output-forbidden"
        result = subprocess.run([sys.executable, "-B", str(APP / "build.py"), "--javac", sys.executable,
                                 "--build", str(target)], capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("build path", result.stderr)
        self.assertFalse(target.exists())

    def test_driver_rejects_source_outside_relative_and_parent_traversal_targets(self):
        driver = self.driver()
        base = self.root / ".rd-platform/build"
        forbidden = [self.root, self.root / "examples/source", self.root.parent / "escape",
                     base, Path("relative-output"), base / "safe/../escaped"]
        with patch.object(driver, "ROOT", self.root), patch.object(driver.subprocess, "run") as process:
            for target in forbidden:
                with self.subTest(target=target):
                    with self.assertRaisesRegex(ValueError, "build"):
                        driver.compile_application(sys.executable, target)
            process.assert_not_called()
        self.assertFalse(base.exists())

    def test_driver_keeps_space_and_shell_metacharacters_in_single_argv_arguments(self):
        driver = self.driver()
        target = self.root / ".rd-platform/build/java space & literal"
        with patch.object(driver, "ROOT", self.root), patch.object(driver.subprocess, "run") as process:
            process.return_value.returncode = 0
            self.assertEqual(driver.compile_application(sys.executable, target), 0)
            args, kwargs = process.call_args
            argv = args[0]
            self.assertEqual(argv[:5], [sys.executable, "-encoding", "UTF-8", "-d", str(target / "classes")])
            self.assertEqual(len(argv), 11)
            self.assertFalse(kwargs["shell"])
            self.assertTrue((target / "classes").is_dir())

    def test_driver_propagates_nonzero_compiler_result(self):
        driver = self.driver()
        with patch.object(driver, "ROOT", self.root), patch.object(driver.subprocess, "run") as process:
            process.return_value.returncode = 7
            self.assertEqual(driver.compile_application(sys.executable, self.root / ".rd-platform/build/failure"), 7)

    def test_driver_rejects_linked_output_ancestor(self):
        driver = self.driver()
        base = self.root / ".rd-platform/build"
        base.mkdir(parents=True)
        outside = self.root / "outside"
        outside.mkdir()
        linked = base / "linked"
        self.link_directory(linked, outside)
        with patch.object(driver, "ROOT", self.root), patch.object(driver.subprocess, "run") as process:
            with self.assertRaisesRegex(ValueError, "symlink|junction|reparse"):
                driver.compile_application(sys.executable, linked / "nested")
            process.assert_not_called()
        self.assertFalse((outside / "nested").exists())

    def test_driver_rejects_link_inside_existing_classes_directory(self):
        driver = self.driver()
        target = self.root / ".rd-platform/build/java"
        classes = target / "classes"
        classes.mkdir(parents=True)
        outside = self.root / "source-directory"
        outside.mkdir()
        self.link_directory(classes / "booking", outside)
        with patch.object(driver, "ROOT", self.root), patch.object(driver.subprocess, "run") as process:
            with self.assertRaisesRegex(ValueError, "symlink|junction|reparse"):
                driver.compile_application(sys.executable, target)
            process.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
