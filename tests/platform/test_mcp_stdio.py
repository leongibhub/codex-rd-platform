from __future__ import annotations

import anyio
import inspect
import json
import os
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path

from mcp import StdioServerParameters
from scripts.mcp_health_check import _check_stdio_parameters, async_check_company_context, check_company_context


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_ENV_NAMES = {
    "COMPANY_LOCAL_ROOTS", "REDMINE_BASE_URL", "REDMINE_API_KEY", "REDMINE_PROJECT",
    "RAGFLOW_BASE_URL", "RAGFLOW_API_KEY", "RAGFLOW_DATASET_ID", "GITLAB_BASE_URL",
    "GITLAB_TOKEN", "GITLAB_PROJECT_ID",
}


class CompanyContextStdioTests(unittest.TestCase):
    def test_config_forwards_documented_env_and_is_required(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        server = config["mcp_servers"]["company_context"]
        root = ROOT.resolve()
        self.assertEqual(Path(server["cwd"]), root)
        self.assertEqual(Path(server["command"]), root / ".venv" / "Scripts" / "python.exe")
        self.assertEqual([Path(arg) for arg in server["args"]], [root / "tools" / "mcp" / "company-context" / "server.py"])
        self.assertIs(server["required"], True)
        self.assertEqual(len(server["env_vars"]), 10)
        self.assertEqual(set(server["env_vars"]), EXPECTED_ENV_NAMES)
        self.assertIs(server["enabled"], True)
        self.assertEqual(server["startup_timeout_sec"], 20)
        self.assertIs(type(server["startup_timeout_sec"]), int)
        self.assertEqual(server["tool_timeout_sec"], 60)
        self.assertIs(type(server["tool_timeout_sec"]), int)

    def test_public_health_check_entry_points_accept_only_root(self):
        self.assertEqual(list(inspect.signature(check_company_context).parameters), ["root"])
        self.assertEqual(list(inspect.signature(async_check_company_context).parameters), ["root"])
        with self.assertRaises(TypeError):
            check_company_context(ROOT, _test_command=[sys.executable])

    def test_stdio_health_check_lists_exact_tools(self):
        self.assertEqual(check_company_context(ROOT), [])

    def test_resolver_rejects_command_outside_repository_venv(self):
        with self._configured_root(command="../python.exe") as root:
            self.assertEqual(self._codes(check_company_context(root)), ["MCP_COMMAND_UNTRUSTED"])

    def test_resolver_rejects_cwd_outside_repository_root(self):
        with self._configured_root(cwd="tools") as root:
            self.assertEqual(self._codes(check_company_context(root)), ["MCP_CWD_UNTRUSTED"])

    def test_resolver_rejects_invalid_server_argument_shapes(self):
        cases = {
            "empty": ([], "MCP_ARGS_INVALID"),
            "leading-flag": (["--flag", "tools/mcp/company-context/server.py"], "MCP_ARGS_INVALID"),
            "trailing-flag": (["tools/mcp/company-context/server.py", "--flag"], "MCP_ARGS_INVALID"),
            "external": (["tools/other-server.py"], "MCP_SERVER_UNTRUSTED"),
            "reordered": (["tools/mcp/company-context/server.py", "tools/mcp/company-context/server.py"], "MCP_ARGS_INVALID"),
        }
        for name, (args, expected_code) in cases.items():
            with self.subTest(name=name), self._configured_root(args=args) as root:
                self.assertEqual(self._codes(check_company_context(root)), [expected_code])

    def test_resolver_rejects_required_false(self):
        with self._configured_root(required=False) as root:
            self.assertEqual(self._codes(check_company_context(root)), ["MCP_REQUIRED_INVALID"])

    def test_resolver_rejects_enabled_and_timeout_contract_violations(self):
        cases = (
            ({"enabled": False}, "MCP_ENABLED_INVALID"),
            ({"enabled": "true"}, "MCP_ENABLED_INVALID"),
            ({"startup_timeout_sec": True}, "MCP_STARTUP_TIMEOUT_INVALID"),
            ({"startup_timeout_sec": 20.0}, "MCP_STARTUP_TIMEOUT_INVALID"),
            ({"startup_timeout_sec": "20"}, "MCP_STARTUP_TIMEOUT_INVALID"),
            ({"startup_timeout_sec": 19}, "MCP_STARTUP_TIMEOUT_INVALID"),
            ({"tool_timeout_sec": False}, "MCP_TOOL_TIMEOUT_INVALID"),
            ({"tool_timeout_sec": 60.0}, "MCP_TOOL_TIMEOUT_INVALID"),
            ({"tool_timeout_sec": "60"}, "MCP_TOOL_TIMEOUT_INVALID"),
            ({"tool_timeout_sec": 61}, "MCP_TOOL_TIMEOUT_INVALID"),
        )
        for overrides, expected_code in cases:
            with self.subTest(overrides=overrides), self._configured_root(**overrides) as root:
                self.assertEqual(self._codes(check_company_context(root)), [expected_code])

    @unittest.skipUnless(os.name == "nt", "junction containment is a Windows contract")
    def test_resolver_rejects_junction_targets_outside_the_canonical_repository_root(self):
        with self._configured_root() as root, tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            python_target = outside / "python.exe"
            python_target.touch()
            venv_link = root / ".venv"
            (venv_link / "Scripts" / "python.exe").unlink()
            (venv_link / "Scripts").rmdir()
            venv_link.rmdir()
            self._make_junction(venv_link, outside)
            try:
                self.assertEqual(self._codes(check_company_context(root)), ["MCP_COMMAND_UNTRUSTED"])
            finally:
                self._remove_junction(venv_link)

        with self._configured_root() as root, tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            (outside / "server.py").touch()
            server_directory = root / "tools" / "mcp" / "company-context"
            (server_directory / "server.py").unlink()
            server_directory.rmdir()
            self._make_junction(server_directory, outside)
            try:
                self.assertEqual(self._codes(check_company_context(root)), ["MCP_SERVER_UNTRUSTED"])
            finally:
                self._remove_junction(server_directory)

    def test_resolver_rejects_invalid_environment_name_lists(self):
        cases = {
            "duplicate": [*sorted(EXPECTED_ENV_NAMES)[:-1], "COMPANY_LOCAL_ROOTS", "COMPANY_LOCAL_ROOTS"],
            "missing": sorted(EXPECTED_ENV_NAMES)[:-1],
            "extra": [*sorted(EXPECTED_ENV_NAMES), "EXTRA"],
        }
        for name, env_vars in cases.items():
            with self.subTest(name=name), self._configured_root(env_vars=env_vars) as root:
                self.assertEqual(self._codes(check_company_context(root)), ["MCP_ENV_VARS_INVALID"])

    def test_timeout_reaps_parent_and_child_processes_within_bound(self):
        with self._blocker() as blocker:
            started = time.monotonic()
            issues = anyio.run(_check_stdio_parameters, blocker.params, 2)
            elapsed = time.monotonic() - started
            self.assertEqual(self._codes(issues), ["MCP_STARTUP_TIMEOUT"])
            self.assertLess(elapsed, 8)
            parent, child = blocker.wait_for_processes()
            self.assertTrue(self._wait_for_exit(parent))
            self.assertTrue(self._wait_for_exit(child))

    def test_external_cancellation_reaps_parent_and_child_processes(self):
        with self._blocker() as blocker:
            anyio.run(self._cancel_running_check, blocker)
            parent, child = blocker.wait_for_processes()
            self.assertTrue(self._wait_for_exit(parent))
            self.assertTrue(self._wait_for_exit(child))

    @staticmethod
    async def _cancel_running_check(blocker: "_BlockingServer") -> None:
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(_check_stdio_parameters, blocker.params, 15)
            await blocker.wait_for_marker()
            task_group.cancel_scope.cancel()

    def _configured_root(self, **kwargs):
        return _ConfiguredRoot(**kwargs)

    @staticmethod
    def _codes(issues):
        return [issue.code for issue in issues]

    @staticmethod
    def _pid_exists(process_id: int) -> bool:
        if os.name == "nt":
            result = subprocess.run(["tasklist", "/FI", f"PID eq {process_id}", "/NH"], capture_output=True, text=True, check=False)
            return str(process_id) in result.stdout
        try:
            os.kill(process_id, 0)
        except ProcessLookupError:
            return False
        return True

    def _wait_for_exit(self, process_id: int, seconds: float = 6) -> bool:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if not self._pid_exists(process_id):
                return True
            time.sleep(0.05)
        return not self._pid_exists(process_id)

    def _blocker(self):
        return _BlockingServer(self)

    def _make_junction(self, link: Path, target: Path):
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], text=True, capture_output=True, check=False)
        if result.returncode != 0:
            self.skipTest(f"junction creation is unavailable: {result.stderr or result.stdout}")

    @staticmethod
    def _remove_junction(link: Path):
        if link.exists() or link.is_symlink():
            os.rmdir(link)


class _ConfiguredRoot:
    def __init__(self, command=None, cwd=None, args=None, required=True, env_vars=None, enabled=True, startup_timeout_sec=20, tool_timeout_sec=60):
        self._directory = tempfile.TemporaryDirectory()
        self.root, self.command, self.cwd, self.args = Path(self._directory.name), command, cwd, args
        self.required, self.env_vars = required, env_vars
        self.enabled, self.startup_timeout_sec, self.tool_timeout_sec = enabled, startup_timeout_sec, tool_timeout_sec

    def __enter__(self) -> Path:
        (self.root / ".codex").mkdir()
        (self.root / ".venv" / "Scripts").mkdir(parents=True)
        (self.root / "tools" / "mcp" / "company-context").mkdir(parents=True)
        (self.root / ".venv" / "Scripts" / "python.exe").touch()
        (self.root / "tools" / "mcp" / "company-context" / "server.py").touch()
        command = self.command if self.command is not None else ".venv/Scripts/python.exe"
        args = self.args if self.args is not None else ["tools/mcp/company-context/server.py"]
        cwd = self.cwd if self.cwd is not None else "."
        env_vars = self.env_vars if self.env_vars is not None else sorted(EXPECTED_ENV_NAMES)
        entries = [
            "[mcp_servers.company_context]", f'command = "{command}"',
            "args = [" + ", ".join(f'"{arg}"' for arg in args) + "]",
            f'cwd = "{cwd}"', f"required = {json.dumps(self.required)}", f"enabled = {json.dumps(self.enabled)}",
            f"startup_timeout_sec = {json.dumps(self.startup_timeout_sec)}", f"tool_timeout_sec = {json.dumps(self.tool_timeout_sec)}",
            "env_vars = [" + ", ".join(f'"{name}"' for name in env_vars) + "]",
        ]
        (self.root / ".codex" / "config.toml").write_text("\n".join(entries), encoding="utf-8")
        return self.root

    def __exit__(self, *unused):
        self._directory.cleanup()


class _BlockingServer:
    def __init__(self, case: CompanyContextStdioTests):
        self.case, self._directory = case, tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        self.marker, self.blocker = self.root / "processes.json", self.root / "blocker.py"
        self.params = StdioServerParameters(command=sys.executable, args=[str(self.blocker)], env={"MCP_TEST_PID_MARKER": str(self.marker)}, cwd=str(self.root))

    def __enter__(self):
        self.blocker.write_text(
            "from pathlib import Path\nimport json, os, subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            "Path(os.environ['MCP_TEST_PID_MARKER']).write_text(json.dumps({'parent': os.getpid(), 'child': child.pid}))\n"
            "time.sleep(60)\n", encoding="utf-8")
        return self

    def __exit__(self, *unused):
        self._directory.cleanup()

    async def wait_for_marker(self) -> None:
        with anyio.fail_after(5):
            while not self.marker.exists():
                await anyio.sleep(0.05)

    def wait_for_processes(self) -> tuple[int, int]:
        deadline = time.monotonic() + 5
        while not self.marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.case.assertTrue(self.marker.exists())
        processes = json.loads(self.marker.read_text(encoding="utf-8"))
        return processes["parent"], processes["child"]


if __name__ == "__main__":
    unittest.main()
