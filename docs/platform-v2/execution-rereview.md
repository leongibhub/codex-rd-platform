# TASK-V2-004 / TASK-V2-005 Independent Execution Re-review

- Evidence ID: `EVD-V2-EXEC-REREVIEW-20260906`
- Evidence Status: `VERIFIED`
- Source role: independent reviewer
- Reviewer identity: `/root/v2_review_execution`
- Review target: dirty working tree on `codex/platform-v2-runtime` at HEAD `a2c766c`; `rd_platform/_process_tree.py` was untracked and was read and exercised explicitly.
- Scope: `rd_platform/runner.py`, `rd_platform/_process_tree.py`, `scripts/write_local_config.py`, their focused tests, and `docs/platform-v2/execution-fix-report.md`.
- Boundary: this is a task-scoped code re-review. It is not a project Gate, human acceptance, release approval, deployment result, or full-suite regression conclusion.

## Verdict

- Specification conformance: `FAIL` pending the unresolved P1 and P2 below.
- Code-quality decision: `CHANGES_REQUIRED`; do not approve TASK-V2-005 while the P1 remains unresolved.
- Finding count: P0=0, P1=1, P2=1, P3=0.

The prior descendant-process, truncated-secret, strict output-byte-cap, disk-spool, and TOML false-success findings are materially fixed on the reviewed Windows path. The focused suite passed, but two failure/security boundaries remain.

## Verification performed

Command:

```text
.venv\Scripts\python.exe -m unittest tests.runtime.test_runner tests.platform.test_config_rewrite -v
```

Observed result: exit 0; 22 tests passed in 6.213 seconds. No full suite, package installation, or network operation was executed.

Confirmed fixed behavior:

- Windows helper does not receive target argv until successful Job assignment; Job creation and assignment failure tests demonstrate that target code does not start.
- Job active-process accounting waits for normal descendants and terminates descendants on timeout or output overflow.
- Output is drained through a pipe with bounded retained memory; invalid UTF-8 remains within the final encoded byte cap and no temporary disk spool is used.
- Environment secrets of any nonempty length, explicit secrets, split secrets, and the implemented `--token`, `--password`, `--api-key`, and `--api_key` forms are redacted.
- The TOML scanner ignores fake keys/headers in multiline strings, accepts indented/commented headers, preserves CRLF and unrelated MCP text, and verifies exact parsed postconditions before atomic replacement.

## Unresolved findings

### RF-EXEC-RR-001 — P1 critical — Sensitive argv flag matching is not fail-closed

- Requirement/task: TASK-V2-005; evidence-secret protection.
- Evidence: `rd_platform/runner.py:14-26` recognizes only four exact flag names. The CLI caller does not supply `explicit_secret_values`.
- Narrow reproduction: execute a synthetic command with `--client-secret review-client-secret-fixture`. The runner returned `PASS`, and the complete synthetic secret was present in the returned result.
- Failure mode: obvious variants such as `--secret`, `--client-secret`, `--access-token`, and prefixed credential options are returned in both argv metadata and captured stdout unless the direct Python caller separately supplies the optional explicit list.
- Impact: credentials can be persisted as execution evidence despite the repository's no-secret-in-evidence policy.
- Required remediation: normalize option names and treat any option whose name contains controlled sensitive terms such as `token`, `secret`, `password`, or `api-key` as sensitive for both `--name value` and `--name=value`; alternatively require structured argv sensitivity metadata and make all production callers provide it. Add direct runner and CLI integration tests for non-exact sensitive flag variants and failure fallbacks.

### RF-EXEC-RR-002 — P2 major — Termination/query failures escape instead of producing structured FAIL evidence

- Requirement/task: TASK-V2-005; REQ-V2-008 failure handling.
- Evidence: `rd_platform/runner.py:105-130` catches an `OSError` from the main loop, but the `finally` block calls `tree.active()` and `tree.stop()` again without converting their failures. `rd_platform/_process_tree.py:52-63,112-120` can raise from Job query, termination, or process wait.
- Narrow reproduction: patch `ProcessTree.stop` to raise a synthetic `OSError` while a real sleeping process reaches timeout. `run_command` raised `OSError` instead of returning its documented result dictionary.
- Impact: execution evidence and stable FAIL status are lost on precisely the containment-failure path. Current CLI fallback also reconstructs argv outside the runner's redaction path, increasing the confidentiality impact.
- Required remediation: make cleanup best-effort but non-lossy: capture primary and cleanup errors, always attempt Job-handle closure/pipe closure/thread join, return a sanitized `FAIL` result, and never let a secondary cleanup exception replace the primary execution outcome. Add Job query, terminate, wait, and close-failure tests.

## Evidence qualification

`docs/platform-v2/execution-fix-report.md` states that `git diff --check` included `rd_platform/_process_tree.py`; because that file is currently untracked, Git did not inspect it through that command. This re-review inspected and executed the helper directly, but the cited diff-check line should not be treated as evidence for the untracked file until it is staged or checked separately.

## Reviewer signature

Signed-by: `/root/v2_review_execution`

Role: independent reviewer

Date: 2026-09-06 (Asia/Shanghai)
Decision: `CHANGES_REQUIRED`

## Final residual re-review — 2026-09-06

This section appends the independent closure decision and intentionally preserves the earlier `FAIL` / `CHANGES_REQUIRED` record above as review history.

### Scope and execution

Reviewed only the directed residual changes for:

- `RF-EXEC-RR-001`: generalized sensitive argv option matching in `rd_platform/runner.py:15-26`;
- `RF-EXEC-RR-002`: sanitized, best-effort execution and cleanup failure handling in `rd_platform/runner.py:92-156` and checked Windows Job close behavior in `rd_platform/_process_tree.py:65-69`.

Independent directed command:

```text
.venv\Scripts\python.exe -m unittest -v \
  tests.runtime.test_runner.CommandRunnerTests.test_sensitive_flag_variants_redact_assignment_and_next_value \
  tests.runtime.test_runner.CommandRunnerTests.test_query_and_termination_errors_return_fail_and_close_job \
  tests.runtime.test_runner.CommandRunnerTests.test_wait_failure_returns_fail_with_sanitized_error \
  tests.runtime.test_runner.CommandRunnerTests.test_close_failure_is_fail_and_retried
```

Observed result: exit 0; 4 tests passed in 0.949 seconds.

Independent former-failure probes also observed:

- `--client-secret final-review-client-secret-fixture`: command result remained `PASS`, the synthetic secret was absent from the complete returned result, and `[REDACTED]` was present.
- injected `ProcessTree.stop` `OSError` on timeout: `run_command` returned a structured `FAIL`; `launch_error` was present and the synthetic raw exception text was absent.

### Finding disposition

- `RF-EXEC-RR-001` P1: `RESOLVED`. Assignment and following-value forms are covered by sensitive-name matching and independent subprocess evidence.
- `RF-EXEC-RR-002` P2: `RESOLVED`. Query, termination, wait, and close failures now produce sanitized structured failure evidence while cleanup attempts continue independently.
- New actionable findings in this directed re-review: P0=0, P1=0, P2=0, P3=0.

### Final scoped verdict

- Specification conformance for the reviewed TASK-V2-004 compatibility fix and TASK-V2-005 runner scope: `PASS`.
- Code-quality decision for this reviewed scope: `APPROVED`.
- Boundary: this approval covers only the reviewed working-tree implementation and independent focused evidence. It is not a project Gate PASS, full regression result, POSIX execution result, human acceptance, release approval, commit, push, or deployment evidence.

Signed-by: `/root/v2_review_execution`

Role: independent reviewer

Date: 2026-09-06 (Asia/Shanghai)
Decision: `APPROVED` for the stated scope

## Final sign-off checkpoint — independent QA handoff

The reviewer performed a read-only identity check after the independent-QA handoff. The approved product files all predate the signed final residual review at 2026-09-06 16:32:31 +08:00 and remain the same content reviewed for the PASS above:

| File | Last write (+08:00) | SHA-256 |
|---|---|---|
| `rd_platform/runner.py` | 2026-09-06 16:31:25 | `34C6BFC40DB829F2187B5028C3698A0CF851F2EEE8B23E51073445A000D17194` |
| `rd_platform/_process_tree.py` | 2026-09-06 16:30:14 | `38D1AA55CF7D5B1C516DBC2FFAFF43723CBD88B0AABA4702EEE64312816A03E2` |
| `scripts/write_local_config.py` | 2026-09-06 16:18:23 | `38220A1B7B83772049583A1871B7FE6613048DE0DF9B975F9540F7C9E2071495` |

The QA-only adjustment in `tests/runtime/test_system.py:216-223` explicitly decodes the spawned local server's text pipes as UTF-8 with replacement on malformed bytes. It changes only the test harness interpretation of the application's declared UTF-8 output, does not modify product execution behavior, and does not invalidate this review.

No new actionable finding was identified. The final scoped verdict remains `PASS` / `APPROVED`. The orchestrator reported review Run `run-15569ccf32c14ac598a3c922da4b1370` as `ACTIVE`; this reviewer did not mutate runtime state or claim its completion. This checkpoint is evidence supporting the orchestrator's subsequent actual `run.finish` decision, not a substitute for that recorded transition.

Signed-by: `/root/v2_review_execution`

Role: independent reviewer

Date: 2026-09-06 (Asia/Shanghai)
Decision: final scoped sign-off confirmed
