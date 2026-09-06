"""Loopback-only HTTP surface for the local runtime board.

The browser is deliberately a restricted control plane.  Run lifecycle
commands and command execution remain CLI/host responsibilities.
"""

from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit


MAX_BODY_BYTES = 64 * 1024
REQUEST_READ_TIMEOUT_SECONDS = 2.0
HTTP_COMMANDS = frozenset({
    "project.create", "agent.register", "task.create", "task.control", "project.control",
    "lifecycle.control", "work.control",
})
STATIC_ROOT = Path(__file__).with_name("static")


def _reject_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not allowed: {value}")


def create_server(db_path: str | Path, *, host: str = "127.0.0.1", port: int = 8020) -> ThreadingHTTPServer:
    """Create a local-only server backed by a real Runtime instance."""
    if host != "127.0.0.1":
        raise ValueError("HTTP server must bind exactly to 127.0.0.1")
    # Delayed import lets CLI help and static inspection work before all task
    # modules have been installed, without providing a substitute core.
    from .runtime import Runtime

    server = ThreadingHTTPServer((host, port), _handler_type())
    server.runtime = Runtime(db_path)  # type: ignore[attr-defined]
    return server


def _handler_type() -> type[BaseHTTPRequestHandler]:
    class BoardHandler(BaseHTTPRequestHandler):
        server_version = "RDPlatform/2"

        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            if not self._valid_host():
                self._error(HTTPStatus.BAD_REQUEST, "Host must be this loopback server")
                return
            request = urlsplit(self.path)
            if request.path == "/api/lifecycle/collection":
                query = parse_qs(request.query, keep_blank_values=True)
                try:
                    if set(query) - {"project_id", "collection", "after_cursor", "limit"} or any(len(value) != 1 for value in query.values()):
                        raise ValueError("query fields may appear once")
                    project_id = query.get("project_id", [""])[0]
                    collection = query.get("collection", [""])[0]
                    if not project_id or not collection:
                        raise ValueError("project_id and collection are required")
                    limit_text = query.get("limit", ["200"])[0]
                    if re.fullmatch(r"[1-9][0-9]*", limit_text) is None:
                        raise ValueError("invalid lifecycle pagination")
                    result = self.server.runtime.lifecycle_collection(project_id, collection, limit=int(limit_text), after_cursor=query.get("after_cursor", [None])[0])
                    self._json(HTTPStatus.OK, result)
                except (KeyError, ValueError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if request.path == "/api/lifecycle":
                query = parse_qs(request.query, keep_blank_values=True)
                try:
                    if set(query) - {"project_id", "after_sequence", "limit"} or any(len(v) != 1 for v in query.values()):
                        raise ValueError("query fields may appear once")
                    project_id = query.get("project_id", [""])[0]
                    if not project_id:
                        raise ValueError("project_id is required")
                    after = int(query.get("after_sequence", ["0"])[0])
                    limit = int(query.get("limit", ["200"])[0])
                    if after < 0 or not 1 <= limit <= 500:
                        raise ValueError("invalid lifecycle pagination")
                    result = self.server.runtime.lifecycle_snapshot(project_id, after_sequence=after, limit=limit)
                    self._json(HTTPStatus.OK, result)
                except (KeyError, ValueError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            if request.path == "/api/snapshot":
                query = parse_qs(request.query, keep_blank_values=True)
                project_ids = query.get("project_id", [])
                if len(project_ids) > 1:
                    self._error(HTTPStatus.BAD_REQUEST, "project_id may appear once")
                    return
                try:
                    self._json(HTTPStatus.OK, self.server.runtime.snapshot(project_ids[0] if project_ids else None))  # type: ignore[attr-defined]
                except (KeyError, ValueError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            static_path = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}.get(request.path)
            if static_path is None:
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            content = (STATIC_ROOT / static_path).read_bytes()
            content_type, _ = mimetypes.guess_type(static_path)
            self.send_response(HTTPStatus.OK)
            self._security_headers()
            self.send_header("Content-Type", content_type or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
            if not self._valid_host():
                self._error(HTTPStatus.BAD_REQUEST, "Host must be this loopback server")
                return
            if not self._valid_origin():
                self._error(HTTPStatus.FORBIDDEN, "External Origin is not allowed")
                return
            if self.path != "/api/commands":
                self._error(HTTPStatus.NOT_FOUND, "Not found")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type must be application/json")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._error(HTTPStatus.BAD_REQUEST, "Content-Length is required")
                return
            if length < 0 or length > MAX_BODY_BYTES:
                # Drain only a one-byte-over-limit payload so a compliant
                # client can receive the 413 cleanly.  Never try to drain an
                # arbitrarily announced body; close that connection instead.
                if length <= MAX_BODY_BYTES + 1:
                    try:
                        self.connection.settimeout(REQUEST_READ_TIMEOUT_SECONDS)
                        self.rfile.read(length)
                    except OSError:
                        pass
                else:
                    self.close_connection = True
                self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body is too large")
                return
            try:
                self.connection.settimeout(REQUEST_READ_TIMEOUT_SECONDS)
                payload = json.loads(self.rfile.read(length).decode("utf-8"), parse_constant=_reject_nonfinite_json)
                if not isinstance(payload, dict):
                    raise ValueError("request payload must be an object")
                command = payload["command"]
                data = payload["data"]
                request_id = payload.get("request_id")
                if not isinstance(command, str):
                    raise ValueError("command must be a string")
                if command not in HTTP_COMMANDS:
                    self._error(HTTPStatus.FORBIDDEN, "Command is not available over HTTP")
                    return
                if not isinstance(data, dict) or request_id is not None and not isinstance(request_id, str):
                    raise ValueError("data must be an object and request_id must be a string")
                if command == 'lifecycle.control' and data.get('action') not in {'pause', 'resume'}:
                    raise ValueError('HTTP lifecycle control supports pause/resume only')
                if command == 'work.control' and data.get('action') not in {'retry', 'reject', 'skip', 'reassign', 'modify'}:
                    raise ValueError('HTTP work control does not execute rollback')
                result = self.server.runtime.execute(command, data, request_id=request_id)  # type: ignore[attr-defined]
            except (OSError, TimeoutError, RecursionError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
                self._error(HTTPStatus.REQUEST_TIMEOUT if isinstance(exc, TimeoutError) else HTTPStatus.BAD_REQUEST, str(exc))
                return
            self._json(HTTPStatus.OK, result)

        def _valid_host(self) -> bool:
            host = self.headers.get("Host", "")
            port = str(self.server.server_port)
            # Deliberately accept an IP literal only: a hostname can be
            # rebound by DNS, whereas the listener and browser origin are
            # both pinned to the loopback address specified by the contract.
            return host == f"127.0.0.1:{port}"

        def _valid_origin(self) -> bool:
            origin = self.headers.get("Origin")
            if origin is None:
                return True
            return origin == f"http://127.0.0.1:{self.server.server_port}"

        def _json(self, status: HTTPStatus, value: Any) -> None:
            body = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self._security_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._json(status, {"error": message})

        def _security_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'; frame-ancestors 'none'")

        def log_message(self, format: str, *args: object) -> None:
            # Avoid mirroring user supplied content to an uncontrolled console.
            return

    return BoardHandler
