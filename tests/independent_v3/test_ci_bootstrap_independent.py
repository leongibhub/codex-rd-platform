"""Independent black-box checks for TASK-V3-014 local MCP bootstrap."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "write_local_config.py"


class IndependentPortableMcpBootstrapTests(unittest.TestCase):
    """Requirement-derived native-host rewrite and no-write failure coverage."""

    def test_tc_v3_ind_ci_801_native_rewrite_has_exact_in_root_launch(self) -> None:
        original = (
            '# preamble preserved\r\n'
            '[mcp_servers.unrelated]\r\n'
            'command = "external-tool"\r\n'
            'args = ["--serve"]\r\n'
            'cwd = "C:/unrelated"\r\n\r\n'
            '[mcp_servers.company_context]\r\n'
            'command = "old" # retained comment\r\n'
            'args = ["old.py"]\r\n'
            'cwd = "old"\r\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = root / ".codex" / "config.toml"
            config.parent.mkdir()
            config.write_bytes(original.encode("utf-8"))

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            rewritten = config.read_bytes()
            parsed = tomllib.loads(rewritten.decode("utf-8"))
            launch = parsed["mcp_servers"]["company_context"]
            expected_python = root / ".venv" / ("Scripts" if os.name == "nt" else "bin") / (
                "python.exe" if os.name == "nt" else "python"
            )
            self.assertEqual(launch["command"], str(expected_python))
            self.assertEqual(launch["args"], [str(root / "tools" / "mcp" / "company-context" / "server.py")])
            self.assertEqual(launch["cwd"], str(root))
            self.assertEqual(rewritten.split(b"[mcp_servers.company_context]", 1)[0],
                             original.encode("utf-8").split(b"[mcp_servers.company_context]", 1)[0])
            self.assertIn(b"# retained comment\r\n", rewritten)
            self.assertNotIn(b"\n", rewritten.replace(b"\r\n", b""))

    def test_tc_v3_ind_ci_802_invalid_target_fails_without_overwrite(self) -> None:
        original = (
            '[mcp_servers.company_context]\n'
            'command = 7\nargs = ["server.py"]\ncwd = "."\n'
        ).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = root / ".codex" / "config.toml"
            config.parent.mkdir()
            config.write_bytes(original)

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(config.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
