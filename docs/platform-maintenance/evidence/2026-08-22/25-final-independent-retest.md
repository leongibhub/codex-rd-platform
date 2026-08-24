# 最终独立复验受控转录

- Record Type: PLATFORM_MAINTENANCE_EVIDENCE
- Evidence ID: EVD-T8-FINAL-RETEST-20260822
- Recorder role: documentation manager
- Source role: independent tester
- Test target SHA: `5b422d0`
- Branch: `codex/fix-BUG-001-platform-readiness`
- Source basis: final independent-tester response retained by the Task 8 test loop; this is a documentation-manager controlled transcription, not a signature, Gate decision, release decision or acceptance.

## Exact Retained Invocation

| Exact command | Result | Runner duration |
|---|---|---|
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` | 103 tests; 0 failures; 0 errors; 0 skipped; exit 0 | 83.216 s |

## Observed Summary

Other final checks were reported by the independent tester, but their literal shell invocations were not retained in the final response. They are therefore recorded as `OBSERVED` summaries rather than invented commands or additional command-ledger `PASS` rows.

| Check area | Observed result | Literal invocation |
|---|---|---|
| Governance manifest path matrix | 9/9 fail-closed across three path categories and absolute, `..`, and junction variants. | NOT_AVAILABLE |
| Strict template validators | Full validation reported runtime `EXECUTED`; static validation reported runtime `NOT_EXECUTED`. | NOT_AVAILABLE |
| stdio health | 3/3 runs passed. | NOT_AVAILABLE |
| Environment and integrity checks | `pip check`, PowerShell parse, `compileall`, diff check, status and secret scan all reported PASS. | NOT_AVAILABLE |

## Boundary

[TC-002](../../TC-002-codex-restart-validation.md) and Redmine/RAGFlow/GitLab external calls were not executed and remain `NOT_EXECUTED`. The result above is independent automated/platform evidence only; it does not establish a project Gate, release, deployment or acceptance.
