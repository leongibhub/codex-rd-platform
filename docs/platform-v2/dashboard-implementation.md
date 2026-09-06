# TASK-V2-002 Dashboard and CLI implementation record

- Task: `TASK-V2-002`
- Requirements: `REQ-V2-006`, `REQ-V2-009`
- Design / interface: `DES-V2-001`, sections “公共接口” and “模块边界”
- Scope owner: `rd_platform/web.py`, `cli.py`, `__main__.py`, `static/`, and `tests/runtime/test_web.py`.
- Implementation state: implemented locally; independent test/review and any project Gate decision remain `NOT_EXECUTED` / outside this task.

## Delivered behavior

- `python -m rd_platform serve` binds only `127.0.0.1:8020` by default and serves a board backed by the real SQLite `Runtime` snapshot.
- `GET /api/snapshot` is read-only. `POST /api/commands` accepts only `project.create`, `agent.register`, `task.create`, `task.control`, and `project.control`; lifecycle run commands and shell/argv execution are not exposed to HTTP.
- The HTTP adapter accepts only an exact IP-literal loopback Host and Origin, requires JSON (rejecting simple form requests), caps bodies at 64 KiB, times out incomplete bodies, returns controlled JSON errors, and uses static routes only. Board JavaScript creates all dynamic DOM text with `textContent`.
- The Chinese console renders actual empty state, projects, tasks, inputs, roles, project runtime status, task current quality phase, check counts, run handoff, expandable run summary/evidence/output, events, and a snapshot-driven Agent table. It refreshes every three seconds only while the page is visible, prevents overlapping refreshes, and reports its last successful refresh or a disconnected state. The Agent table maps `task_id` to its title and truthfully labels absent heartbeats as `未报告`; only a BUSY Agent whose heartbeat is older than five minutes is marked `可能失联`, not as a claim that an untracked remote process was killed. It declares that a model is not automatically connected.
- CLI commands are `serve`, `command`, `snapshot`, `discover`, `freeze`, `report`, and trusted-only `run`; they share the default database `.rd-platform/state.db` and exchange JSON. `run` starts a Runtime run, calls the existing shell-free runner with argv after `--`, writes collected evidence through `run.finish`, and returns nonzero for a failed execution.

## Verification evidence

| Step | Command | Result | Evidence status |
| --- | --- | --- | --- |
| RED | `python -m unittest tests.runtime.test_web -v` | Expected pre-integration failure: `ModuleNotFoundError: No module named 'rd_platform'`, after the test was written and before TASK-V2-001 created the runtime package. | OBSERVED |
| HTTP/CLI GREEN | `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m unittest tests.runtime.test_web -v` | Exit 0; 12 tests passed. Covers empty snapshot/no fake task, malformed/deeply nested/nonfinite/oversized-integer payload handling without writes, simple-form rejection, exact Origin and foreign Host rejection, incomplete-body timeout, oversize body rejection, denied `run.finish`, persisted permitted command, static dynamic-content handling, and real trusted CLI successful/failed run evidence. | OBSERVED |
| CLI | `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m rd_platform --help` | Exit 0; shows all six commands and default database option. | OBSERVED |
| Real CLI persistence | `.\.venv\Scripts\python.exe -m rd_platform --db <temporary-db> command project.create '{"name":"CLI项目","idea":"真实命令"}' --request-id cli-project-1`; then `... snapshot` | Exit 0; returned created project and later snapshot with that project plus one `project.created` event. Temporary database removed after observation. | OBSERVED |
| Static check | `.\.venv\Scripts\python.exe -m compileall -q rd_platform` | Exit 0. | OBSERVED |
| Adjacent runtime regression | `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m unittest tests.runtime.test_runtime tests.runtime.test_runner tests.runtime.test_discovery tests.runtime.test_reporting -v` | Exit 0; 30 tests passed. This is a local regression observation, not independent validation. | OBSERVED |

## Traceability and limitations

`REQ-V2-006` is covered by the snapshot-driven board and empty-state regression. `REQ-V2-009` is covered by the loopback/Host/Origin/content-type/body/allowlist regressions and CLI adapters. This task does not execute arbitrary commands through HTTP and does not claim an autonomous model connection, independent verification, human acceptance, release readiness, or a Gate `PASS`.
