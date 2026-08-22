from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from mcp.server import MCPServer

mcp = MCPServer(name="company-context", version="0.2.0")

TEXT_SUFFIXES = {
    ".md", ".txt", ".rst", ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".ps1", ".bat", ".sql", ".csv"
}
MAX_FILE_BYTES = 2_000_000
DEFAULT_TIMEOUT = 20


def _local_roots() -> list[Path]:
    raw = os.getenv("COMPANY_LOCAL_ROOTS", "")
    roots = [Path(p.strip()) for p in raw.split(";") if p.strip()]
    if not roots:
        roots = [Path.cwd() / "knowledge" / "local"]
    return roots


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_approved_path(path: Path, roots: list[Path]) -> Path | None:
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    for root in roots:
        try:
            approved_root = root.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if _is_relative_to(resolved, approved_root):
            return resolved
    return None


def _is_approved_path(path: Path, roots: list[Path]) -> bool:
    return _resolve_approved_path(path, roots) is not None


def _safe_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"File too large for direct text read: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def _headers(token_env: str, header: str) -> dict[str, str]:
    token = os.getenv(token_env, "").strip()
    return {header: token} if token else {}


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _request_error(service: str) -> str:
    return _error(f"{service} request failed")


@mcp.tool()
def search_local_docs(query: str, max_results: int = 20) -> str:
    """Search configured local text/code knowledge roots for a literal case-insensitive query."""
    q = query.strip()
    if not q:
        return json.dumps({"error": "query is empty"}, ensure_ascii=False)
    hits: list[dict[str, Any]] = []
    q_lower = q.lower()
    roots = _local_roots()

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if len(hits) >= max_results:
                break
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            resolved = _resolve_approved_path(path, roots)
            if resolved is None:
                continue
            try:
                text = _safe_text(resolved)
            except Exception:
                continue
            idx = text.lower().find(q_lower)
            if idx < 0:
                continue
            start = max(0, idx - 300)
            end = min(len(text), idx + len(q) + 500)
            hits.append({
                "path": str(resolved),
                "root": str(root),
                "snippet": text[start:end]
            })

    return json.dumps({"query": q, "results": hits}, ensure_ascii=False, indent=2)


@mcp.tool()
def read_local_doc(path: str, start_line: int = 1, max_lines: int = 400) -> str:
    """Read a text/code file only when it is located under an approved COMPANY_LOCAL_ROOTS directory."""
    target = Path(path)
    roots = _local_roots()
    resolved = _resolve_approved_path(target, roots)
    if resolved is None:
        return _error("path is outside approved local roots")

    try:
        text = _safe_text(resolved)
    except (OSError, ValueError):
        return _error("local document read failed")

    lines = text.splitlines()
    start = max(1, start_line)
    end = min(len(lines), start - 1 + max(1, min(max_lines, 2000)))
    selected = [{"line": i + 1, "text": lines[i]} for i in range(start - 1, end)]
    return json.dumps({
        "path": str(resolved),
        "start_line": start,
        "end_line": end,
        "total_lines": len(lines),
        "content": selected
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def get_redmine_issue(issue_id: int) -> str:
    """Fetch one Redmine issue using REDMINE_BASE_URL and REDMINE_API_KEY."""
    base = os.getenv("REDMINE_BASE_URL", "").rstrip("/")
    key = os.getenv("REDMINE_API_KEY", "")
    if not base or not key:
        return json.dumps({"error": "Redmine is not configured"}, ensure_ascii=False)

    try:
        r = requests.get(
            f"{base}/issues/{issue_id}.json",
            headers={"X-Redmine-API-Key": key},
            params={"include": "journals,relations,attachments,watchers"},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        return json.dumps(r.json(), ensure_ascii=False, indent=2)
    except (requests.RequestException, ValueError):
        return _request_error("Redmine")


@mcp.tool()
def search_redmine(query: str, limit: int = 50) -> str:
    """Search Redmine issues by subject/description using the issues API."""
    base = os.getenv("REDMINE_BASE_URL", "").rstrip("/")
    key = os.getenv("REDMINE_API_KEY", "")
    project = os.getenv("REDMINE_PROJECT", "").strip()
    if not base or not key:
        return json.dumps({"error": "Redmine is not configured"}, ensure_ascii=False)

    params: dict[str, Any] = {
        "status_id": "*",
        "limit": max(1, min(limit, 100)),
        "set_filter": 1,
        "f[]": "subject",
        "op[subject]": "~",
        "v[subject][]": query,
    }
    if project:
        params["project_id"] = project

    try:
        r = requests.get(
            f"{base}/issues.json",
            headers={"X-Redmine-API-Key": key},
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        return json.dumps(r.json(), ensure_ascii=False, indent=2)
    except (requests.RequestException, ValueError):
        return _request_error("Redmine")


@mcp.tool()
def ragflow_search(query: str, top_k: int = 8) -> str:
    """
    Retrieve RAGFlow chunks for configured RAGFLOW_DATASET_ID.

    Note: RAGFlow deployments can differ by version/API contract.
    This uses the common /api/v1/retrieval endpoint shape; validate it
    against your deployed RAGFlow API before production use.
    """
    base = os.getenv("RAGFLOW_BASE_URL", "").rstrip("/")
    key = os.getenv("RAGFLOW_API_KEY", "")
    dataset_id = os.getenv("RAGFLOW_DATASET_ID", "")
    if not base or not key or not dataset_id:
        return json.dumps({"error": "RAGFlow is not configured"}, ensure_ascii=False)

    payload = {
        "question": query,
        "dataset_ids": [dataset_id],
        "page": 1,
        "page_size": max(1, min(top_k, 50)),
    }
    try:
        r = requests.post(
            f"{base}/api/v1/retrieval",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        return json.dumps(r.json(), ensure_ascii=False, indent=2)
    except (requests.RequestException, ValueError):
        return _request_error("RAGFlow")


@mcp.tool()
def get_gitlab_project() -> str:
    """Fetch configured GitLab project metadata."""
    base = os.getenv("GITLAB_BASE_URL", "").rstrip("/")
    token = os.getenv("GITLAB_TOKEN", "")
    project_id = os.getenv("GITLAB_PROJECT_ID", "")
    if not base or not token or not project_id:
        return json.dumps({"error": "GitLab is not configured"}, ensure_ascii=False)

    try:
        r = requests.get(
            f"{base}/api/v4/projects/{requests.utils.quote(project_id, safe='')}",
            headers={"PRIVATE-TOKEN": token},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        return json.dumps(r.json(), ensure_ascii=False, indent=2)
    except (requests.RequestException, ValueError):
        return _request_error("GitLab")


@mcp.tool()
def search_gitlab_issues(query: str, limit: int = 50) -> str:
    """Search issues in the configured GitLab project."""
    base = os.getenv("GITLAB_BASE_URL", "").rstrip("/")
    token = os.getenv("GITLAB_TOKEN", "")
    project_id = os.getenv("GITLAB_PROJECT_ID", "")
    if not base or not token or not project_id:
        return json.dumps({"error": "GitLab is not configured"}, ensure_ascii=False)

    try:
        pid = requests.utils.quote(project_id, safe="")
        r = requests.get(
            f"{base}/api/v4/projects/{pid}/issues",
            headers={"PRIVATE-TOKEN": token},
            params={"search": query, "per_page": max(1, min(limit, 100)), "scope": "all"},
            timeout=DEFAULT_TIMEOUT,
        )
        r.raise_for_status()
        return json.dumps(r.json(), ensure_ascii=False, indent=2)
    except (requests.RequestException, ValueError):
        return _request_error("GitLab")


@mcp.tool()
def get_project_context(topic: str) -> str:
    """
    Return a compact cross-source context bundle.
    It searches local docs and, when configured, Redmine/GitLab.
    RAGFlow retrieval is exposed separately because its API contract may need deployment-specific validation.
    """
    bundle: dict[str, Any] = {"topic": topic}

    try:
        bundle["local"] = json.loads(search_local_docs(topic, 10))
    except Exception:
        bundle["local_error"] = "local search failed"

    try:
        if os.getenv("REDMINE_BASE_URL") and os.getenv("REDMINE_API_KEY"):
            bundle["redmine"] = json.loads(search_redmine(topic, 20))
    except Exception:
        bundle["redmine_error"] = "Redmine context failed"

    try:
        if os.getenv("GITLAB_BASE_URL") and os.getenv("GITLAB_TOKEN") and os.getenv("GITLAB_PROJECT_ID"):
            bundle["gitlab"] = json.loads(search_gitlab_issues(topic, 20))
    except Exception:
        bundle["gitlab_error"] = "GitLab context failed"

    return json.dumps(bundle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
