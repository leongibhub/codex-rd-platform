"""TASK-V3-013 / BUG-CI-003 native compiler and JDK probe contracts."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from rd_platform import stack_harness


class NativeToolProbeTests(unittest.TestCase):
    def test_windows_native_gpp_is_reported_as_cxx(self):
        with tempfile.TemporaryDirectory(prefix="rd-native-tool-") as directory:
            compiler = Path(directory) / "g++.exe"
            compiler.touch()
            windows = SimpleNamespace(name="nt", environ={})
            with patch.object(stack_harness, "os", windows), patch.object(
                stack_harness.shutil, "which", side_effect=lambda name: str(compiler) if name == "g++" else None
            ):
                tools = stack_harness.probe_tools()
        self.assertEqual(tools["cxx"]["status"], "AVAILABLE")
        self.assertEqual(tools["cxx"]["path"], str(compiler.resolve()))

    def test_linux_java_home_uses_unextended_binary_name(self):
        with tempfile.TemporaryDirectory(prefix="rd-native-tool-") as directory:
            home = Path(directory) / "jdk"
            executable = home / "bin" / "java"
            executable.parent.mkdir(parents=True)
            executable.touch()
            linux = SimpleNamespace(name="posix", environ={"JAVA_HOME": str(home)})
            with patch.object(stack_harness, "os", linux), patch.object(stack_harness.shutil, "which", return_value=None):
                resolved = stack_harness._java_tool("java")
        self.assertEqual(resolved, executable)


if __name__ == "__main__":
    unittest.main()
