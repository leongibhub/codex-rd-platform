# Task-board exercise independent black-box test record

- Record ID: `EVD-EXAMPLE-BLACKBOX-001`
- Scope: `DES-EXAMPLE-001`, `REQ-EXAMPLE-001` through `REQ-EXAMPLE-003`
- Test owner: `/root/v2_independent_qa` (role `tester`)
- Document State: `DRAFT`
- Evidence Status: `OBSERVED`
- Overall result: `PASS` for the eight current-attempt HTTP black-box cases. This is an exercise-level module result, not a release, production deployment, or human acceptance decision.

## Independent scope

The test suite is derived only from `examples/task_board/SPEC.md`. It does not inspect `app.py` or developer unit tests. Each case starts a real loopback HTTP server with a temporary SQLite DB, sends user-facing HTTP requests, and observes only responses plus subsequent API-visible state.

The `X-Role` header is tested only as the specified trusted role-boundary demonstration. It is not authentication evidence.

## Executed cases and observable evidence

The tester was registered in the actual runtime database `.rd-platform/state.db`
as `/root/v2_independent_qa`, role `tester`, with idempotent request ID
`v2-independent-qa-register-001`. The actual platform task was
`task-5b6e402c2c43480b801036fe0e06d02f`.

After its recorded implementation PASS, the tester started and finished the
`unit` Run `run-3ea423153b41449bb13afe74e835a010` with the independently
observed result below. The developer-specified command was executed unchanged
through the trusted bounded runner:

```text
argv: python -m unittest examples.task_board.test_unit -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 5.236975
observed summary: Ran 8 tests in 4.927s / OK
```

Historical attempt 1 integration Run `run-51ba1ed64b5a430eac5f0c61a52b6e63`
passed its six then-current black-box cases. A subsequent sample defect required
task retry, so that run does not establish current-attempt evidence.

For current attempt 2, the tester started and finished unit Run
`run-37caaf7399a149298b981624ca394ed8` by independently re-running the
developer unit command:

```text
argv: python -m unittest examples.task_board.test_unit -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 5.732932
observed summary: Ran 9 tests in 5.338s / OK
```

The tester then started and finished current-attempt integration Run
`run-b4d4b26025e349c38d4ae8ca1f9b91ab` with the extended SPEC-derived HTTP
suite:

```text
argv: python -m unittest examples.task_board.test_blackbox -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 5.235075
observed summary: Ran 7 tests in 4.769s / OK
```

The prior attempt-2 evidence was followed by a second sample remediation.
Current attempt 3 unit Run `run-901998433b394b6ba333f890d4096220` independently
executed the unchanged developer command:

```text
argv: python -m unittest examples.task_board.test_unit -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 6.929560
observed summary: Ran 11 tests in 6.442s / OK
```

Current attempt 3 integration Run `run-f184d7e959d640ce84b995026a5741b0` executed
the expanded black-box suite:

```text
argv: python -m unittest examples.task_board.test_blackbox -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 5.415662
observed summary: Ran 8 tests in 4.994s / OK
```

The runtime task subsequently observed `status: READY`, `next_phase: review`,
`attempt: 3`, and `checks_passed: 3` of `checks_total: 4`. No reviewer result
has been created by this tester.

| TC | Requirements | Objective and observed result | Status | Evidence | Defect |
|---|---|---|---|---|---|
| `TC-EXAMPLE-901` | `REQ-EXAMPLE-001` | Health returned `200 {"status":"ok"}`; editor CRUD produced 201/200/204; viewer listed the resulting state. | `PASS` | Integration runner output above; named test `test_health_and_crud_for_viewer_and_editor`. | — |
| `TC-EXAMPLE-902` | `REQ-EXAMPLE-001` | Missing, viewer, malformed, and unknown roles returned `403` for all mutations; subsequent list was unchanged. | `PASS` | Integration runner output above; `test_write_operations_require_editor_role`. | — |
| `TC-EXAMPLE-903` | `REQ-EXAMPLE-002` | Trimmed length-120 title succeeded; missing/null/non-string/empty/121-char/non-object/malformed JSON returned `400`; >16 KiB returned `413`; list was unchanged by rejects. | `PASS` | Integration runner output above; `test_title_validation_and_request_body_limits_are_non_mutating`. | — |
| `TC-EXAMPLE-904` | `REQ-EXAMPLE-002` | Only JSON bool was accepted; 0/1/string/null/container returned `400`; unknown IDs and paths returned `404`. | `PASS` | Integration runner output above; `test_done_is_boolean_and_unknown_resources_are_not_successful`. | — |
| `TC-EXAMPLE-905` | `REQ-EXAMPLE-003` | Updating first task and deleting second left only the updated first task visible. | `PASS` | Integration runner output above; `test_modify_and_delete_affect_only_target_task`. | — |
| `TC-EXAMPLE-906` | `REQ-EXAMPLE-003` | Stop and restart over the same temporary SQLite DB retained the committed task. | `PASS` | Integration runner output above; `test_restart_preserves_committed_tasks`. | — |
| `TC-EXAMPLE-907` | `REQ-EXAMPLE-002` | A 5,000-level JSON structure below the 16 KiB cap returned controlled `400`; the pre-existing task list stayed unchanged. | `PASS` | Current integration runner output above; `test_deep_json_is_rejected_without_creating_a_task`. | — |
| `TC-EXAMPLE-908` | `REQ-EXAMPLE-002` | A valid JSON body below 16 KiB whose title is a 5,000-digit number returned controlled `400` and preserved prior tasks. | `PASS` | Current attempt-3 integration runner output above; `test_oversized_numeric_title_is_rejected_without_disconnect`. | — |

## Defects

No black-box defect was observed in the current attempt-3 execution. No
`BUG-EXAMPLE-xxx` was created. This statement is limited to the eight executed
current cases (`TC-EXAMPLE-901` through `TC-EXAMPLE-908`) and does not assert
absence of defects outside their scope. The six-case attempt-1 result remains
historical evidence only, as labeled above.

## Boundaries

Performance/load limits, 72-hour reliability, external deployment, real login, multi-tenancy, security certification, production recovery, and human acceptance are `NOT_EXECUTED` because they are excluded from the exercise specification.
