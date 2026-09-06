"""TASK-V3-013 / BUG-CI-003 Windows-native C++ runtime-linking contract."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


VERIFY = Path(__file__).resolve().parents[2] / "examples" / "multistack" / "cpp_inventory" / "verify.py"


def load_verify_module():
    spec = importlib.util.spec_from_file_location("cpp_inventory_windows_linking", VERIFY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WindowsCppLinkingTests(unittest.TestCase):
    def test_static_gnu_runtime_flags_cover_both_native_windows_outputs(self):
        verify = load_verify_module()
        with tempfile.TemporaryDirectory(prefix="rd-cpp-link-") as directory, patch.object(verify, "BUILD", Path(directory)), patch.object(
            verify.os, "name", "nt"
        ), patch.object(verify, "use_wsl", return_value=False), patch.object(verify, "invoke") as invoke:
            verify.compile_application()
            verify.compile_unit_tests()
        self.assertEqual(invoke.call_count, 2)
        for command in (call.args[0] for call in invoke.call_args_list):
            self.assertIn("-static-libstdc++", command)
            self.assertIn("-static-libgcc", command)

    def test_linux_or_wsl_commands_do_not_gain_windows_runtime_flags(self):
        verify = load_verify_module()
        with tempfile.TemporaryDirectory(prefix="rd-cpp-link-") as directory, patch.object(verify, "BUILD", Path(directory)), patch.object(
            verify.os, "name", "posix"
        ), patch.object(verify, "use_wsl", return_value=False), patch.object(verify, "invoke") as invoke:
            verify.compile_application()
            verify.compile_unit_tests()
        for command in (call.args[0] for call in invoke.call_args_list):
            self.assertNotIn("-static-libstdc++", command)
            self.assertNotIn("-static-libgcc", command)


if __name__ == "__main__":
    unittest.main()
