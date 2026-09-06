"""A deliberately small, loopback-only SQLite task API exercise.

``X-Role`` is a trusted demonstration header for the exercise's role boundary;
it is not identity authentication.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator


MAX_BODY_BYTES = 16 * 1024


def _connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def _database(db_path: str) -> Iterator[sqlite3.Connection]:
    """Open, commit or roll back, and always close one request connection."""
    connection = _connect(db_path)
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _initialize(db_path: str) -> None:
    with _database(db_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY, title TEXT NOT NULL, done INTEGER NOT NULL CHECK(done IN (0, 1))"
            ")"
        )


def _task(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def _reject_nonfinite_json(_: str) -> None:
    raise ValueError("non-finite JSON constant")


def create_server(db_path: str | Path, port: int = 0) -> ThreadingHTTPServer:
    """Create a loopback HTTP server backed by *db_path*."""
    path = str(db_path)
    _initialize(path)

    class TaskBoardHandler(BaseHTTPRequestHandler):
        server_version = "TaskBoard/1.0"

        @property
        def db_path(self) -> str:
            return self.server.db_path  # type: ignore[attr-defined]

        def log_message(self, format: str, *args: object) -> None:
            """Keep exercise test output focused on assertions."""

        def _send(self, status: int, payload: dict[str, Any] | None = None) -> None:
            body = b"" if payload is None else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            if payload is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _error(self, status: int, message: str) -> None:
            self._send(status, {"error": message})

        def _editor_required(self) -> bool:
            if self.headers.get("X-Role") != "editor":
                self._error(403, "editor role required")
                return False
            return True

        def _json_object(self) -> dict[str, Any] | None:
            length_text = self.headers.get("Content-Length")
            try:
                length = int(length_text) if length_text is not None else -1
            except ValueError:
                length = -1
            if length < 0:
                self._error(400, "invalid JSON body")
                return None
            if length > MAX_BODY_BYTES:
                self._error(413, "request body too large")
                return None
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"), parse_constant=_reject_nonfinite_json)
            except (UnicodeDecodeError, ValueError, RecursionError):
                self._error(400, "invalid JSON body")
                return None
            if not isinstance(value, dict):
                self._error(400, "JSON body must be an object")
                return None
            return value

        @staticmethod
        def _task_id(path: str) -> int | None:
            prefix = "/tasks/"
            if not path.startswith(prefix):
                return None
            text = path[len(prefix):]
            return int(text) if text.isdecimal() else None

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send(200, {"status": "ok"})
                return
            if self.path == "/tasks":
                with _database(self.db_path) as connection:
                    tasks = [_task(row) for row in connection.execute("SELECT id, title, done FROM tasks ORDER BY id")]
                self._send(200, {"tasks": tasks})
                return
            self._error(404, "not found")

        def do_POST(self) -> None:
            if self.path != "/tasks":
                self._error(404, "not found")
                return
            if not self._editor_required():
                return
            payload = self._json_object()
            if payload is None:
                return
            title = payload.get("title")
            if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
                self._error(400, "title must be 1 to 120 characters")
                return
            with _database(self.db_path) as connection:
                cursor = connection.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (title.strip(), False))
                row = connection.execute("SELECT id, title, done FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
            self._send(201, _task(row))

        def do_PATCH(self) -> None:
            task_id = self._task_id(self.path)
            if task_id is None:
                self._error(404, "not found")
                return
            if not self._editor_required():
                return
            payload = self._json_object()
            if payload is None:
                return
            done = payload.get("done")
            if type(done) is not bool:
                self._error(400, "done must be a boolean")
                return
            with _database(self.db_path) as connection:
                cursor = connection.execute("UPDATE tasks SET done = ? WHERE id = ?", (done, task_id))
                if cursor.rowcount != 1:
                    self._error(404, "not found")
                    return
                row = connection.execute("SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
            self._send(200, _task(row))

        def do_DELETE(self) -> None:
            task_id = self._task_id(self.path)
            if task_id is None:
                self._error(404, "not found")
                return
            if not self._editor_required():
                return
            with _database(self.db_path) as connection:
                if connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount != 1:
                    self._error(404, "not found")
                    return
            self._send(204)

    server = ThreadingHTTPServer(("127.0.0.1", port), TaskBoardHandler)
    server.db_path = path  # type: ignore[attr-defined]
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local task-board exercise API.")
    parser.add_argument("--port", type=int, default=8030)
    parser.add_argument("--db", required=True, help="SQLite database path")
    args = parser.parse_args()
    server = create_server(args.db, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
