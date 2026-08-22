from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import anyio


ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = ROOT / "tools" / "mcp" / "company-context" / "server.py"
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
SECRET_SENTINEL = "do-not-leak-this-environment-value"


def _load_server():
    spec = importlib.util.spec_from_file_location("company_context_server", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load company context server")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


async def _tool_names(module):
    from mcp.client import Client

    async with Client(module.mcp) as client:
        result = await client.list_tools(cache_mode="refresh")
        return {tool.name for tool in result.tools}


class CompanyContextTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_server()

    def test_mcp_declares_exact_toolset(self):
        """Removing or adding a registered company-context tool breaks its MCP contract."""
        self.assertEqual(anyio.run(_tool_names, self.module), EXPECTED_TOOLS)

    def test_search_does_not_read_candidate_outside_approved_root(self):
        """Removing candidate root validation leaks a file returned by an unsafe traversal."""
        with tempfile.TemporaryDirectory() as approved, tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / "outside.txt"
            secret.write_text("OUTSIDE_SENTINEL", encoding="utf-8")
            with patch.dict(os.environ, {"COMPANY_LOCAL_ROOTS": approved}, clear=True):
                with patch.object(Path, "rglob", return_value=[secret]):
                    result = json.loads(self.module.search_local_docs("OUTSIDE_SENTINEL"))
        self.assertEqual(result["results"], [])

    def test_read_rejects_path_outside_approved_root(self):
        """Removing resolved root validation permits direct reads from outside configured roots."""
        with tempfile.TemporaryDirectory() as approved, tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / "outside.txt"
            secret.write_text("OUTSIDE_SENTINEL", encoding="utf-8")
            with patch.dict(os.environ, {"COMPANY_LOCAL_ROOTS": approved}, clear=True):
                result = json.loads(self.module.read_local_doc(str(secret)))
        self.assertEqual(result, {"error": "path is outside approved local roots"})

    def test_unconfigured_external_services_return_sanitized_json_errors(self):
        """Missing configuration must not trigger a request or expose configured secret values."""
        with patch.dict(
            os.environ,
            {
                "REDMINE_API_KEY": SECRET_SENTINEL,
                "RAGFLOW_API_KEY": SECRET_SENTINEL,
                "GITLAB_TOKEN": SECRET_SENTINEL,
            },
            clear=True,
        ):
            results = [
                self.module.get_redmine_issue(1),
                self.module.search_redmine("query"),
                self.module.ragflow_search("query"),
                self.module.get_gitlab_project(),
                self.module.search_gitlab_issues("query"),
            ]

        for result in results:
            parsed = json.loads(result)
            self.assertIn("error", parsed)
            self.assertNotIn(SECRET_SENTINEL, result)


if __name__ == "__main__":
    unittest.main()
