from __future__ import annotations

import os
from pathlib import Path
import tomllib
from typing import Any

import anyio
from mcp import Client, StdioServerParameters, stdio_client

from scripts.platform_validation import ValidationIssue


EXPECTED_TOOLS = {
    "get_gitlab_project",
    "get_project_context",
    "get_redmine_issue",
    "ragflow_search",
    "read_local_doc",
    "search_gitlab_issues",
    "search_local_docs",
    "search_redmine",
}
ENVIRONMENT_NAMES = {
    "COMPANY_LOCAL_ROOTS",
    "REDMINE_BASE_URL", "REDMINE_API_KEY", "REDMINE_PROJECT",
    "RAGFLOW_BASE_URL", "RAGFLOW_API_KEY", "RAGFLOW_DATASET_ID",
    "GITLAB_BASE_URL", "GITLAB_TOKEN", "GITLAB_PROJECT_ID",
}


class CompanyContextConfigError(Exception):
    def __init__(self, issue: ValidationIssue):
        super().__init__(issue.message)
        self.issue = issue


def _issue(code: str, message: str) -> CompanyContextConfigError:
    return CompanyContextConfigError(ValidationIssue(code, message))


def _resolve_under(root: Path, configured: str) -> Path:
    return (root / configured).resolve(strict=True)


def _is_under(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def resolve_company_context_config(root: Path) -> StdioServerParameters:
    """Resolve only the repository's trusted company-context stdio launch data."""
    root = root.resolve(strict=True)
    try:
        config = tomllib.loads((root / ".codex" / "config.toml").read_text(encoding="utf-8"))
        server: dict[str, Any] = config["mcp_servers"]["company_context"]
        command = server["command"]
        args = server["args"]
        cwd = server["cwd"]
        env_names = server["env_vars"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        raise _issue("MCP_CONFIG_INVALID", "company_context MCP configuration is invalid") from None

    if not isinstance(command, str) or not isinstance(cwd, str) or not isinstance(args, list):
        raise _issue("MCP_CONFIG_INVALID", "company_context MCP configuration is invalid")
    if server.get("required") is not True:
        raise _issue("MCP_REQUIRED_INVALID", "company_context MCP must be required")
    if server.get("enabled") is not True:
        raise _issue("MCP_ENABLED_INVALID", "company_context MCP must be enabled")
    if type(server.get("startup_timeout_sec")) is not int or server["startup_timeout_sec"] != 20:
        raise _issue("MCP_STARTUP_TIMEOUT_INVALID", "company_context MCP startup timeout must be 20 seconds")
    if type(server.get("tool_timeout_sec")) is not int or server["tool_timeout_sec"] != 60:
        raise _issue("MCP_TOOL_TIMEOUT_INVALID", "company_context MCP tool timeout must be 60 seconds")
    if len(args) != 1 or not isinstance(args[0], str):
        raise _issue("MCP_ARGS_INVALID", "company_context MCP arguments are invalid")
    if (
        not isinstance(env_names, list)
        or not all(isinstance(name, str) for name in env_names)
        or len(env_names) != len(ENVIRONMENT_NAMES)
        or len(set(env_names)) != len(env_names)
        or set(env_names) != ENVIRONMENT_NAMES
    ):
        raise _issue("MCP_ENV_VARS_INVALID", "company_context MCP environment names are invalid")

    try:
        command_path = _resolve_under(root, command)
        venv_root = _resolve_under(root, ".venv")
    except OSError:
        raise _issue("MCP_COMMAND_UNTRUSTED", "company_context command is outside repository .venv") from None
    if not command_path.is_file() or not _is_under(command_path, root) or not _is_under(venv_root, root) or not _is_under(command_path, venv_root):
        raise _issue("MCP_COMMAND_UNTRUSTED", "company_context command is outside repository .venv")
    try:
        cwd_path = _resolve_under(root, cwd)
    except OSError:
        raise _issue("MCP_CWD_UNTRUSTED", "company_context cwd is not repository root") from None
    if not cwd_path.is_dir() or cwd_path != root:
        raise _issue("MCP_CWD_UNTRUSTED", "company_context cwd is not repository root")
    try:
        server_path = _resolve_under(root, args[0])
        expected_server = _resolve_under(root, "tools/mcp/company-context/server.py")
    except OSError:
        raise _issue("MCP_SERVER_UNTRUSTED", "company_context server is not the trusted server.py") from None
    if not server_path.is_file() or not _is_under(server_path, root) or not _is_under(expected_server, root) or server_path != expected_server:
        raise _issue("MCP_SERVER_UNTRUSTED", "company_context server is not the trusted server.py")

    forwarded_environment = {
        name: os.environ[name]
        for name in env_names
        if name in os.environ
    }
    return StdioServerParameters(
        command=str(command_path),
        args=[str(server_path)],
        env=forwarded_environment,
        cwd=str(cwd_path),
    )


async def _list_tools(params: StdioServerParameters):
    transport = stdio_client(params)
    async with Client(transport, mode="auto", read_timeout_seconds=5) as client:
        return await client.list_tools(cache_mode="refresh")


def _validate_tools(tools: list[Any]) -> list[ValidationIssue]:
    names = [tool.name for tool in tools]
    if len(names) != len(set(names)) or set(names) != EXPECTED_TOOLS:
        return [ValidationIssue("MCP_TOOLSET_INVALID", "company_context tools do not match the required contract")]
    for tool in tools:
        if not tool.description or not tool.description.strip():
            return [ValidationIssue("MCP_TOOL_DESCRIPTION_INVALID", "company_context tool description is empty")]
        schema = getattr(tool, "input_schema", None)
        if not isinstance(schema, dict) or schema.get("type") != "object":
            return [ValidationIssue("MCP_TOOL_SCHEMA_INVALID", "company_context tool input schema is not an object")]
    return []


async def _check_stdio_parameters(
    params: StdioServerParameters, timeout_seconds: float
) -> list[ValidationIssue]:
    """Run the stdio-only health check for already trusted parameters."""
    try:
        with anyio.fail_after(timeout_seconds):
            result = await _list_tools(params)
            return _validate_tools(result.tools)
    except TimeoutError:
        return [ValidationIssue("MCP_STARTUP_TIMEOUT", "company_context stdio startup timed out")]
    except Exception:
        return [ValidationIssue("MCP_STDIO_FAILED", "company_context stdio health check failed")]


async def async_check_company_context(root: Path) -> list[ValidationIssue]:
    """Start the trusted configured server and verify only its MCP tools/list contract."""
    try:
        params = resolve_company_context_config(root)
    except CompanyContextConfigError as error:
        return [error.issue]

    return await _check_stdio_parameters(params, 15)


def check_company_context(root: Path) -> list[ValidationIssue]:
    """Synchronous entry point for the platform validator."""
    return anyio.run(async_check_company_context, root)
