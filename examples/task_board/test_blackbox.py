"""Independent HTTP black-box tests for the task-board exercise.

This suite is derived solely from SPEC.md.  It uses the public server factory
and real loopback HTTP requests; it does not inspect application internals.
"""

from __future__ import annotations

import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from examples.task_board.app import create_server


class TaskBoardBlackBoxTests(unittest.TestCase):
    """TC-EXAMPLE-901..906 / DES-EXAMPLE-001."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="task-board-blackbox-")
        self.db_path = Path(self.temp_dir.name) / "tasks.db"
        self.server = None
        self.thread = None
        self.start_server()

    def tearDown(self) -> None:
        self.stop_server()
        self.temp_dir.cleanup()

    def start_server(self) -> None:
        self.server = create_server(self.db_path, port=0)
        self.assertEqual("127.0.0.1", self.server.server_address[0])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop_server(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=3)
        self.server = None
        self.thread = None

    @property
    def port(self) -> int:
        self.assertIsNotNone(self.server)
        return self.server.server_address[1]

    def request(
        self,
        method: str,
        path: str,
        body: object | bytes | None = None,
        *,
        role: str | None = None,
    ) -> tuple[int, dict | None, bytes]:
        encoded = body if isinstance(body, bytes) else (None if body is None else json.dumps(body).encode("utf-8"))
        headers: dict[str, str] = {}
        if role is not None:
            headers["X-Role"] = role
        if encoded is not None:
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(encoded))
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read()
        finally:
            connection.close()
        decoded = json.loads(raw) if raw else None
        return response.status, decoded, raw

    def create(self, title: str) -> dict:
        status, task, _ = self.request("POST", "/tasks", {"title": title}, role="editor")
        self.assertEqual(201, status)
        self.assertIsInstance(task, dict)
        return task

    def list_tasks(self) -> list[dict]:
        status, payload, _ = self.request("GET", "/tasks", role="viewer")
        self.assertEqual(200, status)
        self.assertIsInstance(payload, dict)
        self.assertIsInstance(payload.get("tasks"), list)
        return payload["tasks"]

    def test_health_and_crud_for_viewer_and_editor(self) -> None:
        """TC-EXAMPLE-901 / REQ-EXAMPLE-001 normal HTTP workflow."""
        status, payload, _ = self.request("GET", "/health")
        self.assertEqual(200, status)
        self.assertEqual({"status": "ok"}, payload)
        self.assertEqual([], self.list_tasks())

        created = self.create("  prepare acceptance  ")
        self.assertIsInstance(created.get("id"), int)
        self.assertEqual("prepare acceptance", created.get("title"))
        self.assertIs(created.get("done"), False)
        self.assertEqual([created], self.list_tasks())

        status, updated, _ = self.request("PATCH", f"/tasks/{created['id']}", {"done": True}, role="editor")
        self.assertEqual(200, status)
        self.assertEqual(created["id"], updated["id"])
        self.assertIs(updated["done"], True)
        status, _, raw = self.request("DELETE", f"/tasks/{created['id']}", role="editor")
        self.assertEqual(204, status)
        self.assertEqual(b"", raw)
        self.assertEqual([], self.list_tasks())

    def test_write_operations_require_editor_role(self) -> None:
        """TC-EXAMPLE-902 / REQ-EXAMPLE-001 role boundary for every mutation."""
        task = self.create("protected")
        for method, path, body in (
            ("POST", "/tasks", {"title": "blocked"}),
            ("PATCH", f"/tasks/{task['id']}", {"done": True}),
            ("DELETE", f"/tasks/{task['id']}", None),
        ):
            for role in (None, "viewer", "editor ", "unknown"):
                with self.subTest(method=method, role=role):
                    status, _, _ = self.request(method, path, body, role=role)
                    self.assertEqual(403, status)
        self.assertEqual([task], self.list_tasks())

    def test_title_validation_and_request_body_limits_are_non_mutating(self) -> None:
        """TC-EXAMPLE-903 / REQ-EXAMPLE-002 title equivalence/boundary/negative cases."""
        valid = self.create("x" * 120)
        self.assertEqual(120, len(valid["title"]))
        invalid_bodies = (
            {},
            {"title": None},
            {"title": 3},
            {"title": "   "},
            {"title": "x" * 121},
            [],
        )
        for body in invalid_bodies:
            with self.subTest(body=body):
                status, _, _ = self.request("POST", "/tasks", body, role="editor")
                self.assertEqual(400, status)
        status, _, _ = self.request("POST", "/tasks", b'{"title":', role="editor")
        self.assertEqual(400, status)
        status, _, _ = self.request("POST", "/tasks", b"x" * (16 * 1024 + 1), role="editor")
        self.assertEqual(413, status)
        self.assertEqual([valid], self.list_tasks())

    def test_deep_json_is_rejected_without_creating_a_task(self) -> None:
        """TC-EXAMPLE-907 / REQ-EXAMPLE-002 bounded JSON parser failure path."""
        existing = self.create("before deep json")
        # 5,000 nested arrays are intentionally below the 16 KiB body limit:
        # rejection must be a controlled 400 rather than a disconnect/500 or
        # a partially persisted task.
        deeply_nested = b'{"title":"must-not-persist","extra":' + b"[" * 5000 + b"0" + b"]" * 5000 + b"}"
        self.assertLessEqual(len(deeply_nested), 16 * 1024)
        status, _, _ = self.request("POST", "/tasks", deeply_nested, role="editor")
        self.assertEqual(400, status)
        self.assertEqual([existing], self.list_tasks())

    def test_oversized_numeric_title_is_rejected_without_disconnect(self) -> None:
        """TC-EXAMPLE-908 / REQ-EXAMPLE-002 large numeric JSON parsing path."""
        existing = self.create("before numeric title")
        # The body is valid JSON and below 16 KiB, but title is a 5,000-digit
        # number rather than the required string. It must produce a controlled
        # validation response even where Python limits integer conversion.
        oversized_number = b'{"title":' + b"9" * 5000 + b"}"
        self.assertLessEqual(len(oversized_number), 16 * 1024)
        status, _, _ = self.request("POST", "/tasks", oversized_number, role="editor")
        self.assertEqual(400, status)
        self.assertEqual([existing], self.list_tasks())

    def test_done_is_boolean_and_unknown_resources_are_not_successful(self) -> None:
        """TC-EXAMPLE-904 / REQ-EXAMPLE-002 boolean and resource negative cases."""
        task = self.create("state")
        for value in (0, 1, "true", None, [], {}):
            with self.subTest(value=value):
                status, _, _ = self.request("PATCH", f"/tasks/{task['id']}", {"done": value}, role="editor")
                self.assertEqual(400, status)
        for method, path, body in (
            ("PATCH", "/tasks/999999", {"done": True}),
            ("DELETE", "/tasks/999999", None),
            ("GET", "/tasks/999999", None),
            ("GET", "/not-a-route", None),
        ):
            with self.subTest(method=method, path=path):
                status, _, _ = self.request(method, path, body, role="editor")
                self.assertEqual(404, status)
        self.assertEqual([task], self.list_tasks())

    def test_modify_and_delete_affect_only_target_task(self) -> None:
        """TC-EXAMPLE-905 / REQ-EXAMPLE-003 target isolation."""
        first = self.create("first")
        second = self.create("second")
        status, updated, _ = self.request("PATCH", f"/tasks/{first['id']}", {"done": True}, role="editor")
        self.assertEqual(200, status)
        self.assertIs(updated["done"], True)
        status, _, _ = self.request("DELETE", f"/tasks/{second['id']}", role="editor")
        self.assertEqual(204, status)
        self.assertEqual([{**first, "done": True}], self.list_tasks())

    def test_restart_preserves_committed_tasks(self) -> None:
        """TC-EXAMPLE-906 / REQ-EXAMPLE-003 SQLite recovery after server restart."""
        created = self.create("survives restart")
        self.stop_server()
        self.start_server()
        self.assertEqual([created], self.list_tasks())


if __name__ == "__main__":
    unittest.main()
