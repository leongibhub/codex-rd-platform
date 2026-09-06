"""Loopback unit tests for the task-board HTTP contract.

These tests use the public server interface, so their assertions cover actual
HTTP parsing and SQLite persistence rather than handler internals.
"""

from __future__ import annotations

import http.client
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from examples.task_board.app import create_server


class TaskBoardApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "tasks.db"
        self.server = create_server(self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tempdir.cleanup()

    def request(self, method: str, path: str, payload=None, headers=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request_headers = dict(headers or {})
        if body is not None:
            request_headers["Content-Type"] = "application/json"
            request_headers["Content-Length"] = str(len(body))
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        return response.status, json.loads(raw) if raw else None

    def create(self, title: str = "write tests") -> dict:
        status, task = self.request("POST", "/tasks", {"title": title}, {"X-Role": "editor"})
        self.assertEqual(201, status)
        return task

    def test_health_and_empty_listing(self) -> None:
        self.assertEqual((200, {"status": "ok"}), self.request("GET", "/health"))
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_editor_crud_and_viewer_read(self) -> None:
        task = self.create("  write real HTTP tests  ")
        self.assertEqual({"id": task["id"], "title": "write real HTTP tests", "done": False}, task)
        self.assertEqual((200, {"tasks": [task]}), self.request("GET", "/tasks", headers={"X-Role": "viewer"}))
        self.assertEqual((200, {"id": task["id"], "title": task["title"], "done": True}), self.request(
            "PATCH", f"/tasks/{task['id']}", {"done": True}, {"X-Role": "editor"}
        ))
        self.assertEqual((204, None), self.request("DELETE", f"/tasks/{task['id']}", headers={"X-Role": "editor"}))
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_write_requires_trusted_editor_header(self) -> None:
        self.assertEqual((403, {"error": "editor role required"}), self.request("POST", "/tasks", {"title": "x"}))
        self.assertEqual((403, {"error": "editor role required"}), self.request("POST", "/tasks", {"title": "x"}, {"X-Role": "viewer"}))
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_invalid_payloads_do_not_create_tasks(self) -> None:
        bad_titles = [{}, {"title": None}, {"title": 3}, {"title": " \t "}, {"title": "x" * 121}]
        for payload in bad_titles:
            self.assertEqual(400, self.request("POST", "/tasks", payload, {"X-Role": "editor"})[0])
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_patch_rejects_non_boolean_and_unknown_resource(self) -> None:
        task = self.create()
        for value in (1, 0, "true", None):
            self.assertEqual(400, self.request("PATCH", f"/tasks/{task['id']}", {"done": value}, {"X-Role": "editor"})[0])
        self.assertEqual(404, self.request("PATCH", "/tasks/99999", {"done": True}, {"X-Role": "editor"})[0])
        self.assertEqual(404, self.request("DELETE", "/tasks/99999", headers={"X-Role": "editor"})[0])
        self.assertEqual((404, {"error": "not found"}), self.request("GET", "/other"))

    def test_malformed_non_object_and_oversized_json_are_rejected(self) -> None:
        for payload in ([], "text", 3):
            self.assertEqual(400, self.request("POST", "/tasks", payload, {"X-Role": "editor"})[0])
        oversized = json.dumps({"title": "x" * 17000}).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("POST", "/tasks", body=oversized, headers={"X-Role": "editor", "Content-Length": str(len(oversized))})
        response = connection.getresponse()
        self.assertEqual(413, response.status)
        response.read()
        connection.close()
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_deeply_nested_json_is_a_controlled_non_mutating_client_error(self) -> None:
        # This remains below 16 KiB but exceeds the standard decoder recursion
        # limit; the server must return 400 instead of disconnecting the client.
        nested = b'{"title":' + (b"[" * 5000) + (b"]" * 5000) + b"}"
        self.assertLessEqual(len(nested), 16 * 1024)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("POST", "/tasks", body=nested, headers={"X-Role": "editor", "Content-Length": str(len(nested))})
        response = connection.getresponse()
        self.assertEqual(400, response.status)
        self.assertEqual({"error": "invalid JSON body"}, json.loads(response.read()))
        connection.close()
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_excessively_long_json_integer_is_a_controlled_non_mutating_client_error(self) -> None:
        # Python's JSON decoder may reject integers beyond its digit safety
        # limit with ValueError; this must not disconnect the HTTP client.
        payload = b'{"title":' + (b"9" * 5000) + b"}"
        self.assertLessEqual(len(payload), 16 * 1024)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("POST", "/tasks", body=payload, headers={"X-Role": "editor", "Content-Length": str(len(payload))})
        response = connection.getresponse()
        self.assertEqual(400, response.status)
        self.assertEqual({"error": "invalid JSON body"}, json.loads(response.read()))
        connection.close()
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_nonfinite_json_constant_is_a_controlled_non_mutating_client_error(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("POST", "/tasks", body=b'{"title":NaN}', headers={"X-Role": "editor", "Content-Length": "13"})
        response = connection.getresponse()
        self.assertEqual(400, response.status)
        self.assertEqual({"error": "invalid JSON body"}, json.loads(response.read()))
        connection.close()
        self.assertEqual((200, {"tasks": []}), self.request("GET", "/tasks"))

    def test_reopening_server_preserves_tasks(self) -> None:
        task = self.create("persist me")
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.server = create_server(self.db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        self.assertEqual((200, {"tasks": [task]}), self.request("GET", "/tasks"))

    def test_module_cli_starts_loopback_server(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        db_path = Path(self.tempdir.name) / "cli.db"
        process = subprocess.Popen(
            [sys.executable, "-m", "examples.task_board.app", "--port", str(port), "--db", str(db_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            for _ in range(20):
                try:
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=0.2)
                    connection.request("GET", "/health")
                    response = connection.getresponse()
                    body = json.loads(response.read())
                    connection.close()
                    if response.status == 200:
                        break
                except (ConnectionRefusedError, TimeoutError):
                    time.sleep(0.05)
            else:
                self.fail("CLI server did not become available")
            self.assertEqual({"status": "ok"}, body)
        finally:
            process.terminate()
            process.wait(timeout=3)
            stderr = process.stderr.read()
            process.stderr.close()
            self.assertEqual("", stderr)


if __name__ == "__main__":
    unittest.main()
