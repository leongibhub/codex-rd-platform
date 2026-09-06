# Task-board exercise implementation record

- Task: `task-5b6e402c2c43480b801036fe0e06d02f`
- Implementation run: `run-808b20af7e854ac9aa3e8a7e03ce3f9f`
- Implementation agent: `/root/v2_example_app`
- Requirements: `REQ-EXAMPLE-001`, `REQ-EXAMPLE-002`, `REQ-EXAMPLE-003`
- Design / acceptance source: [`examples/task_board/SPEC.md`](../../examples/task_board/SPEC.md)
- Scope: platform self-test exercise only; this is not customer-product acceptance.

## Implementation summary

`examples.task_board.app` provides a loopback-only `ThreadingHTTPServer` and
the requested module CLI:

```text
python -m examples.task_board.app --port 8030 --db PATH_TO_SQLITE_DB
```

It stores tasks in SQLite using parameterized statements. Each HTTP request
opens a fresh connection, commits or rolls back its own transaction, and closes
the connection. `X-Role: editor` is a trusted exercise header that demonstrates
the write-role boundary; it is explicitly **not** real identity authentication.

## Traceability

| Requirement | Delivered behavior | Developer test coverage |
| --- | --- | --- |
| `REQ-EXAMPLE-001` | `/health`, task listing and editor CRUD, loopback server and CLI | health/list, CRUD, CLI subprocess tests |
| `REQ-EXAMPLE-002` | strict title/done validation, role denial, 404, JSON-object and 16 KiB limits | invalid input, role, resource, oversized-body, deep-JSON and long-number tests |
| `REQ-EXAMPLE-003` | per-request SQLite transaction/connection, parameterized target-only updates/deletes, restart persistence | CRUD and reopen-server persistence tests |

## Developer verification

| Command | Actual result |
| --- | --- |
| `python -m unittest examples.task_board.test_unit -v` | `Ran 11 tests in 6.529s; OK` |
| `python -m compileall -q examples\\task_board` | exit 0, no output |
| `git diff --check` | exit 0, no whitespace errors |

The test suite uses a real loopback HTTP server and temporary on-disk SQLite
databases. Its CLI test starts `python -m examples.task_board.app` in a Python
subprocess and observes `GET /health`; it does not mock HTTP behavior.

## Review-finding remediation

An independent review identified that a syntactically valid, deeply nested JSON
array below the 16 KiB body cap could raise `RecursionError` in the standard
library decoder and disconnect the client. `TaskBoardHandler._json_object`
now treats that parser failure as invalid JSON and returns a controlled `400`.
Developer regression `test_deeply_nested_json_is_a_controlled_non_mutating_client_error`
uses 5,000 nested arrays, asserts `400`, and confirms that no task is stored.
The RED reproduction ended with `RemoteDisconnected`; the post-fix focused test
and the full developer suite pass. A fresh independently executed test/review
is still required; this note does not close the review finding.

The second review pass found a different decoder failure: a 5,000-digit JSON
number below the body cap raised an ordinary `ValueError` under Python's
integer-digit safety limit. The parser boundary now catches `ValueError`
(which also subsumes `JSONDecodeError`) and explicitly rejects non-finite JSON
constants through `parse_constant`. Developer HTTP regressions assert a
controlled `400` and no write for both the long integer and `NaN`. The RED
long-integer case ended with `RemoteDisconnected`; the focused regressions and
the 11-test developer suite pass. Independent re-test and re-review remain
separate required activities.

## Boundaries and next steps

This record reports only developer implementation and local unit verification.
Independent black-box HTTP testing and source review are `PENDING` and must be
performed by separately registered tester/reviewer agents. No project Gate,
release, deployment, human acceptance, or final system acceptance is asserted.
