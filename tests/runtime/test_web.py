"""HTTP boundary tests for TASK-V2-002.

These use a real temporary SQLite database and a real loopback HTTP server.
They intentionally do not mock Runtime.
"""

from __future__ import annotations

import http.client
import contextlib
import io
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from rd_platform.web import create_server


class WebServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.server = create_server(Path(self.temp_dir.name) / "state.db", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, method: str, path: str, body: object = Ellipsis, **headers: str):
        encoded = None if body is Ellipsis else json.dumps(body).encode("utf-8")
        request_headers = {"Host": f"127.0.0.1:{self.port}", **headers}
        if encoded is not None:
            request_headers.setdefault("Content-Type", "application/json")
            request_headers["Content-Length"] = str(len(encoded))
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(method, path, body=encoded, headers=request_headers)
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        return response.status, raw

    def test_empty_snapshot_contains_no_fake_tasks(self) -> None:
        status, raw = self.request("GET", "/api/snapshot")
        self.assertEqual(status, 200)
        snapshot = json.loads(raw)
        self.assertEqual(snapshot["projects"], [])
        self.assertEqual(snapshot["tasks"], [])
        self.assertEqual(snapshot["events"], [])

    def test_rejects_external_origin_and_unknown_host(self) -> None:
        status, _ = self.request(
            "POST", "/api/commands", {"command": "project.create", "data": {"name": "x", "idea": "y"}},
            Origin="https://attacker.example",
        )
        self.assertEqual(status, 403)

    def test_rejects_non_object_payloads_commands_and_simple_forms(self) -> None:
        for payload in ([], None, "not an object"):
            status, _ = self.request("POST", "/api/commands", payload)
            self.assertEqual(status, 400)
        for command in ([], {}):
            status, _ = self.request("POST", "/api/commands", {"command": command, "data": {}})
            self.assertEqual(status, 400)
        status, _ = self.request(
            "POST", "/api/commands", {"command": "project.create", "data": {"name": "x", "idea": "y"}},
            **{"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.assertEqual(status, 415)

    def test_origin_must_be_exact_loopback_origin(self) -> None:
        status, _ = self.request(
            "POST", "/api/commands", {"command": "project.create", "data": {"name": "x", "idea": "y"}},
            Origin=f"http://attacker@127.0.0.1:{self.port}",
        )
        self.assertEqual(status, 403)
        status, _ = self.request("GET", "/api/snapshot", Host="attacker.example")
        self.assertEqual(status, 400)
        status, _ = self.request(
            "POST", "/api/commands", {"command": "project.create", "data": {"name": "x", "idea": "y"}},
            Origin="http://127.0.0.1:not-a-port",
        )
        self.assertEqual(status, 403)

    def test_rejects_oversized_bodies_and_run_finish(self) -> None:
        huge = b"x" * (64 * 1024 + 1)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(
            "POST", "/api/commands", body=huge,
            headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "Content-Length": str(len(huge))},
        )
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        connection.close()
        status, _ = self.request("POST", "/api/commands", {"command": "run.finish", "data": {}})
        self.assertEqual(status, 403)

    def test_deep_json_is_controlled_bad_request_without_write(self) -> None:
        body = ("[" * 10000 + "0" + "]" * 10000).encode("ascii")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request("POST", "/api/commands", body=body, headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "Content-Length": str(len(body))})
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        response.read(); connection.close()
        status, raw = self.request("GET", "/api/snapshot")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["events"], [])

    def test_nonfinite_and_huge_integer_json_are_rejected_without_write(self) -> None:
        for body in (
            b'{"command":"project.create","data":{"name":"x","idea":NaN}}',
            b'{"command":"project.create","data":{"name":' + b"9" * 5000 + b',"idea":"x"}}',
        ):
            connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
            connection.request("POST", "/api/commands", body=body, headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "Content-Length": str(len(body))})
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            response.read(); connection.close()
        status, raw = self.request("GET", "/api/snapshot")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["projects"], [])

    def test_declared_but_unread_body_times_out_without_holding_thread(self) -> None:
        connection = socket.create_connection(("127.0.0.1", self.port), timeout=4)
        connection.sendall(
            f"POST /api/commands HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
            "Content-Type: application/json\r\nContent-Length: 1\r\n\r\n".encode("ascii")
        )
        response = connection.recv(4096)
        connection.close()
        self.assertIn(b" 408 ", response)

    def test_allowed_control_is_persisted_and_visible(self) -> None:
        status, raw = self.request(
            "POST", "/api/commands",
            {"command": "project.create", "data": {"name": "真实项目", "idea": "实际输入"}, "request_id": "web-project-1"},
        )
        self.assertEqual(status, 200)
        project = json.loads(raw)
        status, raw = self.request("GET", "/api/snapshot")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["projects"][0]["id"], project["id"])
        status, _ = self.request("POST", "/api/commands", {"command": "agent.register", "data": {"id": "board-agent", "role": "developer"}})
        self.assertEqual(status, 200)
        status, raw = self.request("GET", "/api/snapshot")
        self.assertEqual(json.loads(raw)["agents"][0]["id"], "board-agent")

    def test_dynamic_values_are_never_interpolated_into_html(self) -> None:
        status, raw = self.request(
            "POST", "/api/commands",
            {"command": "project.create", "data": {"name": "<img src=x>", "idea": "<script>alert(1)</script>"}},
        )
        self.assertEqual(status, 200)
        status, raw = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertNotIn(b"<img src=x>", raw)
        self.assertNotIn(b"<script>alert(1)</script>", raw)
        script = (Path(__file__).parents[2] / "rd_platform" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)
        self.assertIn("function renderAgents()", script)
        self.assertLess(script.index("const form = event.currentTarget"), script.index("await api(command"))
        page = (Path(__file__).parents[2] / "rd_platform" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="agents"', page)

    def test_cli_run_collects_real_evidence_and_finishes_run(self) -> None:
        from rd_platform.cli import main
        from rd_platform.runtime import Runtime

        runtime = Runtime(Path(self.temp_dir.name) / "cli.db")
        project = runtime.execute("project.create", {"name": "CLI", "idea": "test"})
        runtime.execute("agent.register", {"id": "developer-a", "role": "developer"})
        task = runtime.execute("task.create", {
            "project_id": project["id"], "title": "execute", "why": "verify CLI run", "role": "developer",
            "requirements": ["REQ-V2-009"], "dependencies": [], "inputs": {},
        })
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            exit_code = main([
                "--db", str(Path(self.temp_dir.name) / "cli.db"), "run", "--task-id", task["id"],
                "--agent-id", "developer-a", "--phase", "implementation", "--cwd", self.temp_dir.name,
                "--", sys.executable, "-c", "print('real-cli-evidence')",
            ])
        self.assertEqual(exit_code, 0)
        observed = runtime.snapshot(project["id"])
        self.assertEqual(observed["runs"][0]["status"], "PASS")
        self.assertIn("real-cli-evidence", observed["runs"][0]["evidence"]["stdout"])

    def test_cli_failed_command_finishes_run_and_returns_nonzero(self) -> None:
        from rd_platform.cli import main
        from rd_platform.runtime import Runtime

        runtime = Runtime(Path(self.temp_dir.name) / "failed-cli.db")
        project = runtime.execute("project.create", {"name": "CLI fail", "idea": "test"})
        runtime.execute("agent.register", {"id": "developer-b", "role": "developer"})
        task = runtime.execute("task.create", {
            "project_id": project["id"], "title": "fail", "why": "verify failure", "role": "developer",
            "requirements": ["REQ-V2-009"], "dependencies": [], "inputs": {},
        })
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main([
                "--db", str(Path(self.temp_dir.name) / "failed-cli.db"), "run", "--task-id", task["id"],
                "--agent-id", "developer-b", "--phase", "implementation", "--cwd", self.temp_dir.name,
                "--", sys.executable, "-c", "raise SystemExit(7)",
            ])
        self.assertEqual(exit_code, 1)
        observed = runtime.snapshot(project["id"])
        self.assertEqual(observed["runs"][0]["status"], "FAIL")
        self.assertEqual(observed["tasks"][0]["status"], "FAILED")
        self.assertFalse(any(run["status"] == "ACTIVE" for run in observed["runs"]))
