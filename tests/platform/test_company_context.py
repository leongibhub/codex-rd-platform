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
SECRET_SENTINEL = "[REDACTED_SECRET]"


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

    def test_search_reads_the_approved_canonical_candidate(self):
        """Reading the traversal path instead of its approved canonical path leaks stale content."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.txt"
            canonical = root / "canonical.txt"
            candidate.write_text("ORIGINAL_SENTINEL", encoding="utf-8")
            canonical.write_text("canonical content", encoding="utf-8")
            original_resolve = Path.resolve

            def resolve(path, strict=False):
                if path == candidate:
                    return original_resolve(canonical, strict=strict)
                return original_resolve(path, strict=strict)

            with patch.dict(os.environ, {"COMPANY_LOCAL_ROOTS": str(root)}, clear=True):
                with patch.object(Path, "rglob", return_value=[candidate]):
                    with patch.object(Path, "resolve", new=resolve):
                        result = json.loads(self.module.search_local_docs("canonical content"))

        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["snippet"], "canonical content")
        self.assertNotIn("ORIGINAL_SENTINEL", json.dumps(result))

    def test_read_returns_the_approved_canonical_path(self):
        """Returning the requested path instead of the approved path hides canonical resolution."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate.txt"
            canonical = root / "canonical.txt"
            candidate.write_text("ORIGINAL_SENTINEL", encoding="utf-8")
            canonical.write_text("canonical content", encoding="utf-8")
            original_resolve = Path.resolve
            expected_path = original_resolve(canonical, strict=True)

            def resolve(path, strict=False):
                if path == candidate:
                    return expected_path
                return original_resolve(path, strict=strict)

            with patch.dict(os.environ, {"COMPANY_LOCAL_ROOTS": str(root)}, clear=True):
                with patch.object(Path, "resolve", new=resolve):
                    result = json.loads(self.module.read_local_doc(str(candidate)))

        self.assertEqual(result["path"], str(expected_path))
        self.assertEqual(result["content"], [{"line": 1, "text": "canonical content"}])

    def test_search_requires_strict_candidate_and_root_resolution(self):
        """Non-strict resolution of either containment path must not satisfy the read contract."""
        with tempfile.TemporaryDirectory() as approved, tempfile.TemporaryDirectory() as outside:
            root = Path(approved)
            candidate = root / "candidate.txt"
            canonical = root / "canonical.txt"
            outside_path = Path(outside) / "outside.txt"
            candidate.write_text("ORIGINAL_SENTINEL", encoding="utf-8")
            canonical.write_text("canonical content", encoding="utf-8")
            outside_path.write_text("OUTSIDE_SENTINEL", encoding="utf-8")
            original_resolve = Path.resolve
            canonical_root = original_resolve(root, strict=True)
            canonical_path = original_resolve(canonical, strict=True)
            outside_root = original_resolve(Path(outside), strict=True)
            outside_file = original_resolve(outside_path, strict=True)

            def resolve(path, strict=False):
                if path == candidate:
                    return canonical_path if strict else outside_file
                if path == root:
                    return canonical_root if strict else outside_root
                return original_resolve(path, strict=strict)

            with patch.dict(os.environ, {"COMPANY_LOCAL_ROOTS": str(root)}, clear=True):
                with patch.object(Path, "rglob", return_value=[candidate]):
                    with patch.object(Path, "resolve", new=resolve):
                        result = json.loads(self.module.search_local_docs("canonical content"))

        self.assertEqual(result["results"], [{
            "path": str(canonical_path),
            "root": str(root),
            "snippet": "canonical content",
        }])

    def test_is_approved_path_reports_resolver_containment(self):
        """Removing the public containment helper breaks callers that need a boolean result."""
        with tempfile.TemporaryDirectory() as approved, tempfile.TemporaryDirectory() as outside:
            root = Path(approved)
            inside = root / "inside.txt"
            outside_path = Path(outside) / "outside.txt"
            inside.write_text("inside", encoding="utf-8")
            outside_path.write_text("outside", encoding="utf-8")
            self.assertTrue(self.module._is_approved_path(inside, [root]))
            self.assertFalse(self.module._is_approved_path(outside_path, [root]))

    def test_resolved_escape_candidate_is_not_read(self):
        """An approved-looking candidate that resolves outside the root must be skipped."""
        with tempfile.TemporaryDirectory() as approved, tempfile.TemporaryDirectory() as outside:
            root = Path(approved)
            candidate = root / "candidate.txt"
            secret = Path(outside) / "outside.txt"
            candidate.write_text("safe content", encoding="utf-8")
            secret.write_text("OUTSIDE_SENTINEL", encoding="utf-8")
            original_resolve = Path.resolve

            def resolve(path, strict=False):
                if path == candidate:
                    return secret
                return original_resolve(path, strict=strict)

            with patch.dict(os.environ, {"COMPANY_LOCAL_ROOTS": str(root)}, clear=True):
                with patch.object(Path, "rglob", return_value=[candidate]):
                    with patch.object(Path, "resolve", new=resolve):
                        result = json.loads(self.module.search_local_docs("OUTSIDE_SENTINEL"))

        self.assertEqual(result["results"], [])

    def test_unconfigured_external_services_return_sanitized_json_errors(self):
        """Missing configuration must not trigger a request or expose configured secret values."""
        def unexpected_http(*args, **kwargs):
            raise AssertionError("unconfigured service attempted an HTTP request")

        with patch.dict(
            os.environ,
            {
                "REDMINE_API_KEY": SECRET_SENTINEL,
                "RAGFLOW_API_KEY": SECRET_SENTINEL,
                "GITLAB_TOKEN": SECRET_SENTINEL,
            },
            clear=True,
        ):
            with patch.object(self.module.requests, "get", side_effect=unexpected_http):
                with patch.object(self.module.requests, "post", side_effect=unexpected_http):
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

    def test_configured_request_errors_are_sanitized_for_direct_and_context_tools(self):
        """Request parser failures must not expose configured URLs, IDs, or tokens."""
        environment = {
            "REDMINE_BASE_URL": SECRET_SENTINEL,
            "REDMINE_API_KEY": SECRET_SENTINEL,
            "RAGFLOW_BASE_URL": SECRET_SENTINEL,
            "RAGFLOW_API_KEY": SECRET_SENTINEL,
            "RAGFLOW_DATASET_ID": SECRET_SENTINEL,
            "GITLAB_BASE_URL": SECRET_SENTINEL,
            "GITLAB_TOKEN": SECRET_SENTINEL,
            "GITLAB_PROJECT_ID": SECRET_SENTINEL,
        }
        with patch.dict(os.environ, environment, clear=True):
            direct_results = [
                self.module.get_redmine_issue(1),
                self.module.search_redmine("query"),
                self.module.ragflow_search("query"),
                self.module.get_gitlab_project(),
                self.module.search_gitlab_issues("query"),
            ]
            context_result = self.module.get_project_context("query")

        for result in [*direct_results, context_result]:
            self.assertNotIn(SECRET_SENTINEL, result)
        for result in direct_results:
            self.assertIn("error", json.loads(result))
        context = json.loads(context_result)
        self.assertEqual(context["redmine"], {"error": "Redmine request failed"})
        self.assertEqual(context["gitlab"], {"error": "GitLab request failed"})


if __name__ == "__main__":
    unittest.main()
