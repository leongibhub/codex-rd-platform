from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

from scripts.mcp_health_check import (
    EXPECTED_TOOLS,
    async_check_company_context,
    check_company_context,
    resolve_company_context_config,
)


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ENV_NAMES = {
    "COMPANY_LOCAL_ROOTS",
    "REDMINE_BASE_URL", "REDMINE_API_KEY", "REDMINE_PROJECT",
    "RAGFLOW_BASE_URL", "RAGFLOW_API_KEY", "RAGFLOW_DATASET_ID",
    "GITLAB_BASE_URL", "GITLAB_TOKEN", "GITLAB_PROJECT_ID",
}


class CompanyContextStdioTests(unittest.TestCase):
    def test_config_forwards_documented_env_and_is_required(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        server = config["mcp_servers"]["company_context"]
        self.assertEqual(server["cwd"], ".")
        self.assertTrue(server["required"])
        self.assertEqual(set(server["env_vars"]), EXPECTED_ENV_NAMES)

    def test_stdio_health_check_lists_exact_tools(self):
        self.assertEqual(check_company_context(ROOT), [])

    def test_resolver_rejects_command_outside_repository_venv(self):
        with self._configured_root(command="../python.exe") as root:
            self.assertEqual(self._codes(check_company_context(root)), ["MCP_COMMAND_UNTRUSTED"])

    def test_resolver_rejects_cwd_outside_repository_root(self):
        with self._configured_root(cwd="tools") as root:
            self.assertEqual(self._codes(check_company_context(root)), ["MCP_CWD_UNTRUSTED"])

    def test_resolver_rejects_server_other_than_company_context_server(self):
        with self._configured_root(args=["tools/mcp/company-context/other-server.py"]) as root:
            self.assertEqual(self._codes(check_company_context(root)), ["MCP_SERVER_UNTRUSTED"])

    def test_timeout_returns_stable_code_and_reaps_test_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blocker = root / "blocker.py"
            marker = root / "child.pid"
            blocker.write_text(
                "from pathlib import Path\nimport os, time\n"
                "Path(os.environ['MCP_TEST_PID_MARKER']).write_text(str(os.getpid()))\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            old_marker = os.environ.get("MCP_TEST_PID_MARKER")
            os.environ["MCP_TEST_PID_MARKER"] = str(marker)
            try:
                issues = check_company_context(
                    ROOT,
                    _test_command=[sys.executable, str(blocker)],
                    _test_timeout_seconds=0.25,
                )
            finally:
                if old_marker is None:
                    os.environ.pop("MCP_TEST_PID_MARKER", None)
                else:
                    os.environ["MCP_TEST_PID_MARKER"] = old_marker

            self.assertEqual(self._codes(issues), ["MCP_STARTUP_TIMEOUT"])
            deadline = time.monotonic() + 2
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            process_id = int(marker.read_text(encoding="utf-8"))
            self.assertFalse(self._pid_exists(process_id))

    def _configured_root(self, *, command: str | None = None, cwd: str | None = None,
                         args: list[str] | None = None):
        return _ConfiguredRoot(command=command, cwd=cwd, args=args)

    @staticmethod
    def _codes(issues):
        return [issue.code for issue in issues]

    @staticmethod
    def _pid_exists(process_id: int) -> bool:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {process_id}", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(process_id) in result.stdout
        try:
            os.kill(process_id, 0)
        except ProcessLookupError:
            return False
        return True


class _ConfiguredRoot:
    def __init__(self, *, command: str | None, cwd: str | None, args: list[str] | None):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.command = command
        self.cwd = cwd
        self.args = args

    def __enter__(self) -> Path:
        (self.root / ".codex").mkdir()
        (self.root / ".venv" / "Scripts").mkdir(parents=True)
        (self.root / "tools" / "mcp" / "company-context").mkdir(parents=True)
        (self.root / ".venv" / "Scripts" / "python.exe").touch()
        (self.root / "tools" / "mcp" / "company-context" / "server.py").touch()
        config = {
            "command": self.command or ".venv/Scripts/python.exe",
            "args": self.args or ["tools/mcp/company-context/server.py"],
            "cwd": self.cwd or ".",
            "required": True,
            "env_vars": sorted(EXPECTED_ENV_NAMES),
        }
        entries = [
            "[mcp_servers.company_context]",
            f'command = "{config["command"]}"',
            "args = [" + ", ".join(f'"{arg}"' for arg in config["args"]) + "]",
            f'cwd = "{config["cwd"]}"',
            "required = true",
            "env_vars = [" + ", ".join(f'"{name}"' for name in config["env_vars"]) + "]",
        ]
        (self.root / ".codex" / "config.toml").write_text("\n".join(entries), encoding="utf-8")
        return self.root

    def __exit__(self, exc_type, exc_value, traceback):
        self._directory.cleanup()


if __name__ == "__main__":
    unittest.main()
