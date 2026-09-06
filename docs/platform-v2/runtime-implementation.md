# TASK-V2-001 Durable runtime implementation record

- Task: `TASK-V2-001`
- Design: `DES-V2-001` (`docs/superpowers/specs/2026-09-06-platform-v2-runtime-design.md`)
- Requirements: `REQ-V2-001` through `REQ-V2-005`
- Document State: `DRAFT`
- Evidence Status: `OBSERVED`

## Scope delivered

`rd_platform.runtime.Runtime` implements the frozen `execute` and `snapshot`
interfaces over a local SQLite database. Each operation opens its own SQLite
connection and uses `BEGIN IMMEDIATE`; the state mutation, event append, and
optional idempotency response are committed together or rolled back together.

The durable records are projects, agents, tasks, runs, events, defects, and
request-id results. Events retain insertion `sequence` in snapshots and UTC
timestamps preserve microseconds. `snapshot` returns the six frozen list keys and includes
task/run `revision` and integer `attempt`. An initial task/run uses attempt 1;
a retry after a failure increments it. Task completion checks only count PASS
runs from the task's current revision and attempt, so historical retry evidence
cannot establish a current PASS.

The state machine enforces same-project existing dependencies, DONE-only start
dependencies, one active Run per task (including a partial unique SQLite index),
phase order, role separation, non-empty evidence, terminal review completion,
failure defects, bounded retry, control events, version invalidation, and
request-id payload binding. `PASS` evidence carrying a non-zero `exit_code` is
rejected. The runtime trusts the CLI/host-provided identity; it is not a
multi-user authentication mechanism. HTTP authorization and the prohibition on
`run.*` HTTP commands are outside this task's owned adapter files.

## TDD and local verification

RED was observed before implementation:

```text
ModuleNotFoundError: No module named 'rd_platform'
```

GREEN command, executed with the repository interpreter:

```powershell
& .venv\Scripts\python.exe -m unittest tests.runtime.test_runtime -v
```

Result: superseded by the follow-up review verification below.

The tests use temporary SQLite databases and cover persistence/idempotency,
dependency constraints, developer self-validation rejection, complete
failure/retry/review closure, task/project pause/modify stale-run rejection,
transitive downstream version invalidation, task/Agent active-Run concurrency,
assignee enforcement, related event snapshots, and strict input validation.
This is implementation-unit evidence
only. Independent testing, independent review, product acceptance, release,
and any Gate decision remain `NOT_EXECUTED`/outside this task.

## Follow-up review corrections

Independent review findings were reproduced by new RED tests and corrected.
Assignment is scoped to the task's `next_phase`: a passing Run clears its
assignment, and retry/modify/invalidation clear it too. `skip` and `reject`
version the cancelled task and recursively invalidate dependent task evidence;
`run.finish` rechecks that all dependencies are still `DONE` before any write.

For `PASS`, host evidence such as `{ "review": "pass" }` remains valid, while
explicit command evidence must not contradict success: `exit_code` must be the
integer `0` (not `bool`), and timeout, truncation, start-error, or a non-PASS
explicit evidence status is rejected. Snapshot transactions now use deferred
SQLite `BEGIN`; mutation operations retain `BEGIN IMMEDIATE`.

Exact re-verification command:

```powershell
& .venv\Scripts\python.exe -m unittest tests.runtime.test_runtime -q
```

Result: `Ran 16 tests in 1.352s`, `OK`, exit code `0`. The added cases are
`test_reassignment_is_scoped_to_next_phase_and_clears_after_pass`,
`test_skip_invalidates_downstream_active_run_and_finish_rechecks_dependencies`,
and `test_pass_rejects_explicit_failed_command_evidence`.

## Files

- `rd_platform/__init__.py`
- `rd_platform/store.py`
- `rd_platform/runtime.py`
- `tests/runtime/__init__.py`
- `tests/runtime/test_runtime.py`

No commit was made by this implementation agent; the parent review process owns
integration, independent validation, and commit decisions.
