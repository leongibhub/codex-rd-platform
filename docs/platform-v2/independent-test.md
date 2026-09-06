# V2 Local Runtime Independent System Test Report

- Report ID: `EVD-V2-INDEPENDENT-TEST-001`
- Test owner: independent QA
- Date: 2026-09-06
- Scope: `DES-V2-001`; `REQ-V2-001` through `REQ-V2-009`
- Document State: `DRAFT`
- Evidence Status: `OBSERVED`
- Test conclusion: `PASS` for the eight executed independent system cases below. This is a module-quality result only; it is not a project Gate, deployment, release, or human-acceptance decision.

## Risk model and approach

The primary risks were loss or corruption of durable workflow facts under concurrency, a developer self-validating work, old evidence being reused after failure/change/pause, a local browser endpoint accepting untrusted writes, and a report turning absent or stale execution into a PASS. The test design derives from the requirement/interface contract, user workflow, and trust boundary--not from implementation claims.

All executed cases use a new temporary on-disk SQLite database. `TC-V2-906` also invokes the public CLI in a real Python subprocess, starts `python -m rd_platform ... serve --port 0` as a subprocess, sends loopback HTTP requests, and uses the trusted runner to collect actual child-process exit and output evidence before storing it in Runs. No external service, credential, or network dependency was used.

The identities in these tests are synthetic trusted-host identifiers (`dev-*`, `test-*`, `review-*`). They demonstrate state-machine role separation; they do not validate a real autonomous model, human identity, authentication, or resistance to a malicious local operator, all of which are outside the declared single-user trust boundary.

## Executed test cases and observable evidence

Command executed from `D:\codex-rd-platform`:

```powershell
& .venv\Scripts\python.exe -m unittest tests.runtime.test_system -v
```

Observed terminal result: exit code `0`; `Ran 8 tests in 1.863s`; `OK`.

```text
test_cli_http_runner_lifecycle_and_report_are_real ... ok
test_http_rejects_malicious_origin_host_and_json_without_writing ... ok
test_report_does_not_promote_unexecuted_or_stale_evidence_to_pass ... ok
test_concurrent_runtime_instances_allow_one_active_run ... ok
test_durable_identity_separation_and_final_review_gate ... ok
test_fail_retry_retest_closes_defect_only_after_fresh_review ... ok
test_modify_cascades_to_completed_dependents ... ok
test_pause_rejects_late_result_without_partial_write ... ok
```

| TC | Requirements | Test type / objective | Actual result / evidence | Status | Defect |
|---|---|---|---|---|---|
| `TC-V2-901` | `REQ-V2-001`, `REQ-V2-003` | Functional, persistence, identity boundary: only final independent review makes a task `DONE`. | New DB with developer/tester/reviewer records. Reopen through a new `Runtime(db_path)` retained `DONE`, 4 checks and ordered events; developer unit start was rejected. Command evidence above. | `PASS` | — |
| `TC-V2-902` | `REQ-V2-004` | Recovery: `FAIL → retry → complete retest → review` cannot reuse prior evidence. | Failed implementation opened a defect. After retry, checks were 0; defect stayed open through implementation/unit/integration and closed only after fresh review. Command evidence above. | `PASS` | — |
| `TC-V2-903` | `REQ-V2-005` | Reliability / late-result negative: paused work cannot write a late PASS. | Late `run.finish(PASS)` raised `ValueError`; persisted Run was `INVALIDATED` with no evidence and task stayed `PAUSED`. Command evidence above. | `PASS` | — |
| `TC-V2-904` | `REQ-V2-002`, `REQ-V2-005` | Dependency regression: upstream change invalidates completed dependent evidence. | Modified upstream revision became 2; dependent was no longer `DONE`, its revision advanced, checks were 0, and it could not start while upstream was not `DONE`. Command evidence above. | `PASS` | — |
| `TC-V2-905` | `REQ-V2-001`, `REQ-V2-002` | Concurrency / SQLite transaction boundary. | Eight threads used separate `Runtime` instances against one DB. Exactly one start succeeded, seven were rejected, and snapshot contained one active Run. This is bounded contention, not load certification. | `PASS` | — |
| `TC-V2-906` | `REQ-V2-001`, `REQ-V2-003`, `REQ-V2-006`, `REQ-V2-008`, `REQ-V2-009` | E2E / API contract: CLI + HTTP + runner + Runtime + report. | CLI created project; subprocess server created agents/task over HTTP; runner recorded observed output and zero exit for every lifecycle phase. Initial report was `NOT_EXECUTED`/`DO_NOT_RELEASE`; final module test status was `PASS`, while release remained `NO_RELEASE_EVIDENCE`. Command evidence above. | `PASS` | — |
| `TC-V2-907` | `REQ-V2-009` | Security HTTP negatives: malicious Origin/Host and malformed JSON fail closed without writes. | Real server returned controlled `403`/`400` for external Origin, attacker Host, invalid JSON, and a JSON array. SQLite post-check contained no projects or events. Command evidence above. | `PASS` | `BUG-V2-001` regression |
| `TC-V2-908` | `REQ-V2-004`, `REQ-V2-008` | Reporting boundary: stale or unexecuted evidence cannot become PASS. | Snapshot with an older-attempt PASS and an empty-evidence current PASS reported `NOT_EXECUTED`, zero passed tasks, and `DO_NOT_RELEASE`. Command evidence above. | `PASS` | — |

## Defect record

| BUG | Severity | Main owner | Requirement / test | Reproduction and observed result | Current disposition |
|---|---|---|---|---|---|
| `BUG-V2-001` | High | `rd_platform.web` | `REQ-V2-009`; `TC-V2-907` | First independent execution sent JSON `[]` to `POST /api/commands` and observed `http.client.RemoteDisconnected: Remote end closed connection without response`, not a controlled client error. | `RESOLVED` in the current worktree: payload-object validation returns `400`; independent regression confirms no SQLite write. Not closed: commit/review/release disposition is outside this report. |
| `BUG-V2-015` | Medium | Independent QA test asset (`tests/runtime/test_system.py`) | `REQ-V2-009`; `TC-V2-906`, `TC-V2-907` | The fresh execution-fix integration Run `run-bca18012c85849b79a1332f0f59efff6` ran `python -m unittest tests.runtime.test_system -v` and exited 1. Its subprocess server launcher used the Windows default text codec (GBK) to read a UTF-8 Chinese CLI startup line, producing `UnicodeDecodeError` before either HTTP assertion. | `RESOLVED` in the test asset: server stdout/stderr explicitly decode UTF-8 with replacement. Fresh current-attempt integration Run `run-80e52f99ec82402f8f02eac5fbd398ab` passed all eight cases. This was a test-harness portability defect, not a demonstrated product HTTP failure; it is not marked closed pending review/commit disposition. |

## Fresh execution-fix evidence

The focused independent unit command was executed through the runner for
platform Run `run-b0f7467d0ba141d78c211c9df7a58ccb`:

```text
argv: python -m unittest tests.runtime.test_runner tests.platform.test_config_rewrite -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 5.714278
observed summary: Ran 22 tests in 5.291s / OK
```

The current integration Run `run-bca18012c85849b79a1332f0f59efff6` was
finished `FAIL` with actual evidence: `exit_code: 1`, `duration_seconds:
1.678821`, and two `UnicodeDecodeError` errors while `test_system` attempted to
decode the CLI startup output. No PASS is claimed for this integration attempt.

Following implementation/retry, fresh execution-fix attempt-2 unit Run
`run-f7b4d04dde9c4727a8447fd67ff42276` executed:

```text
argv: python -m unittest tests.runtime.test_runner tests.platform.test_config_rewrite -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 6.587356
observed summary: Ran 26 tests in 6.142s / OK
```

Fresh attempt-2 integration Run `run-80e52f99ec82402f8f02eac5fbd398ab` executed
the normal-interpreter CLI/system path:

```text
argv: python -m unittest tests.runtime.test_system -v
exit_code: 0
timed_out: false
output_truncated: false
duration_seconds: 2.853396
observed summary: Ran 8 tests in 2.441s / OK
```

This task subsequently observed `status: READY`, `next_phase: review`,
`attempt: 2`, and `checks_passed: 3` of `checks_total: 4`. The result is not a
release, acceptance, or Gate decision.

## Coverage and limits

| Area | Status | Boundary |
|---|---|---|
| Functional, persistence, recovery, API integration, E2E, regression, bounded concurrency and security behavior | `PASS` | `TC-V2-901`–`TC-V2-908`; observable command evidence above. |
| Full repository suite / legacy platform regression | `NOT_EXECUTED` | Reserved for the main reviewer to avoid repeated slow-suite runs during parallel implementation. |
| Long-duration reliability, maximum stress/load, performance baselines | `NOT_EXECUTED` | No 72-hour, peak-load, latency, or capacity claim is supported by the eight-thread check. |
| Production deployment, backup/restore drill, browser human acceptance, cross-platform compatibility | `NOT_EXECUTED` | No production target, human acceptance evidence, or OS/browser matrix was exercised. |
| Actual model autonomy / human identity assurance | `NOT_EXECUTED` | Synthetic host identities validate only runtime role-state logic. |

## Release and Gate boundary

The E2E run demonstrates that all recorded module test phases can pass, but `report_scope` is `MODULE_QUALITY`. Its final recommendation is correctly `NO_RELEASE_EVIDENCE`, since deployment and human acceptance were not executed. This report supplies no basis for a project Gate `PASS`, a release, or closure of `BUG-V2-001`.
