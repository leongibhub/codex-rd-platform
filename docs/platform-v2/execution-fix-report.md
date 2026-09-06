# Execution adapter and config rewrite review fixes

- Document State: DRAFT
- Evidence Status: OBSERVED
- Scope: TASK-V2-004 / TASK-V2-005; REQ-V2-008 / REQ-V2-010; DES-V2-001.
- Implementer: `/root/v2_execution_fixes`. Independent re-test/re-review: PENDING.
- Branch: `codex/platform-v2-runtime`; Windows, Python 3.13.5.
- Governance remains template mode; these local results do not establish a project Gate PASS, human acceptance, or release approval.

## Reproduced failures

Command: `python -m unittest tests.runtime.test_runner tests.platform.test_config_rewrite`.

Initial RED: 15 tests, 7 failure records, exit 1, 3.011 seconds. Observations:

- Parent exited with 0 and adapter returned PASS in 0.146132 seconds; descendant created its marker after the requested 0.2 second deadline.
- Invalid UTF-8 expanded a requested 31 byte result budget into 93 UTF-8 bytes.
- Patching temporary disk spool creation to reject writes raised an assertion: the adapter relied on disk spooling.
- Output at the secret boundary disclosed `secret-b`; three-character environment secrets and credential argv values also remained visible.
- A multiline fake section made a genuine unindented header fail; an indented real header produced success while its actual command remained `old`.

Fixtures use synthetic, non-production credential values and temporary directories only.

## Changes

Windows execution now creates a ctypes Job Object with KILL_ON_JOB_CLOSE. The `-I -S` Python helper blocks on a private stdin permission before executing the target. Only successful Job assignment grants permission. All descendants inherit containment; Job active-process count controls completion even after the target/helper exits or descendants close output handles. Timeout/output overflow terminate the Job; final cleanup closes it. Job creation and assignment failure regressions verify that the target never starts. POSIX uses a dedicated session/process group, checks group liveness after leader exit, and sends group SIGKILL on cleanup.

The runner drains a PIPE on a dedicated reader, retains only bounded evidence plus undecidable secret-prefix overlap, and has no disk spool. Raw-byte overflow triggers tree termination and FAIL. Sensitive environment names contribute every nonempty value regardless of length; `--token`, `--password`, `--api-key` / `--api_key` values, including equals syntax, also redact metadata and output. Optional `explicit_secret_values` adds caller-known values without changing existing arguments or result fields. Redaction spans read boundaries; incomplete secret prefixes at the cutoff are suppressed. The final replacement-decoded UTF-8 result is capped again in bytes.

Config rewriting walks TOML statements, including ordinary/triple-quoted strings, quoted keys and comments, to identify actual table/key spans. It preserves unrelated text, comments, CRLF and whitespace. After replacing the three spans, tomllib must reproduce exactly the original document with only the intended command/args/cwd values changed. A deliberately faulty span locator regression verifies failed postconditions exit 2 and preserve the original file byte for byte.

## Verification

The focused command was run five times: RED 15 tests / exit 1; GREEN 15 / exit 0; GREEN 21 / exit 0; GREEN 22 / exit 0; final GREEN 22 / exit 0. The final run after the wall-clock completion check completed 22 tests in 5.496 seconds. The postcondition negative test intentionally printed a parser error while its test passed.

`git diff --check -- rd_platform/runner.py rd_platform/_process_tree.py scripts/write_local_config.py tests/runtime/test_runner.py tests/platform/test_config_rewrite.py`: exit 0; only repository CRLF conversion warnings. Qualification: `_process_tree.py` was untracked, so this Git command did not inspect that file. The helper was exercised by the focused tests; a separate trailing-whitespace check is recorded in the residual-fix section below.

Coverage includes real Windows child/grandchild termination, normal descendant completion, overflow with descendants holding no capture handles, failed Job creation/assignment, 5 MB output, invalid UTF-8, all split positions of a secret, capped retained storage, explicit credentials, multiline fake keys/headers, indented/commented headers, CRLF preservation, and zero-write failure postconditions.

## Remaining verification boundaries

- This implementer ran only the assigned focused suites. Independent reviewer/tester results are PENDING; full platform regression belongs to the orchestrator.
- POSIX implementation is present but execution on a POSIX host is NOT_EXECUTED in this Windows session. Process groups are not a security sandbox against a target intentionally calling setsid or launching untracked remote work.
- No production rollout, human acceptance, Git commit, or push was performed by this agent.
- Truncated evidence may end within the fixed redaction label; it never implies successful execution. Environment/explicit secret matching covers literal values, not transformations such as base64.

## Residual re-review fixes

Source: `execution-rereview.md`, RF-EXEC-RR-001 (P1) and RF-EXEC-RR-002 (P2). This section records implementation, not independent closure of those findings.

The exact flag allowlist was replaced by sensitive-name matching `TOKEN|SECRET|PASSWORD|API[_-]?KEY` for option names beginning with `-`. Both assignment and following-value syntax are covered. Added a real subprocess regression for client-secret, access-token, database-password and service-api_key.

Execution and cleanup now capture OS and subprocess failures separately using fixed context and exception types; raw exception text is never evidence. A failed liveness query is treated as active. Termination, Job close, wait, reader join and pipe close are attempted independently. Failed Job close triggers termination/close retries; the low-level close checks its Windows return value. Any primary or cleanup error forces a structured FAIL even if a later retry succeeds. Launch-constructor cleanup also attempts each operation without allowing a secondary cleanup failure to suppress remaining operations.

Residual-cycle RED command: `python -m unittest tests.runtime.test_runner tests.platform.test_config_rewrite`; 26 tests, 1 failure (sensitive variants) and 4 errors (query, termination, wait, close), exit 1, 5.964 seconds. The failing baseline also emitted resource warnings from skipped cleanup. First GREEN: same command, 26 tests, exit 0, 5.981 seconds, with no resource warnings. The parser message remains expected output from the config zero-write negative test.

The implementer requests another independent narrow review. No independent PASS is claimed here.

Final residual-cycle focused verification after applying redaction to structured error labels: 26 tests, exit 0, 6.361 seconds. This residual cycle ran the focused command three times (RED, GREEN, final GREEN). Tracked-file `git diff --check` returned 0. A separate PowerShell `Get-Content` / `[ \t]+$` check over the untracked helper returned `Helper trailing-whitespace check PASS`, exit 0.
