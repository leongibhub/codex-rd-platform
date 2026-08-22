# 2026-08-22 平台维护测试证据

- Record Type: PLATFORM_MAINTENANCE
- Evidence ID: EVD-T8-TEST-20260822
- Linked Test Cases: [TC-001](TC-001-platform-automated-validation.md), [TC-002](TC-002-codex-restart-validation.md)
- Linked BUG / Task: [BUG-001](BUG-001-platform-self-check-false-positive.md) / [TASK-001](TASK-001-platform-readiness-repair.md)
- Scope: 独立 tester 在 `2d3ae0a` 的初始验证，及独立 retester 在 `ce9ca0e` 的修复后验证。

## Evidence Summary

| Evidence ID | Target / command | Start–end (Asia/Shanghai) | Exit / count | Status | Raw log |
|---|---|---|---|---|---|
| EVD-T8-01 | `unittest discover -s tests -v` | 21:55:19–21:56:20 | 0; 94 tests, 0 failures | PASS | [01](evidence/2026-08-22/01-full-unittest.txt) |
| EVD-T8-02 | `pip check` | 21:56:35–21:56:35 | 0 | PASS | [02](evidence/2026-08-22/02-pip-check.txt) |
| EVD-T8-03 | full `validate_platform.py` | 21:56:35–21:56:37 | 0 | PASS; template mode, runtime executed, evaluated gates none | [03](evidence/2026-08-22/03-platform-validator.txt) |
| EVD-T8-04 | stdio contract ×3 | recorded in log | 0; 3 × 10 tests | PASS; exact eight-tool contract and cleanup | [04](evidence/2026-08-22/04-mcp-stdio-repeat.txt) |
| EVD-T8-05 | two-run setup retry clone | 22:01:07–22:01:44 | 0; freeze 35/35 and equal | PASS | [05](evidence/2026-08-22/05-setup-twice.txt) |
| EVD-T8-06 | 55 negative/boundary tests | 22:02:22–22:06:45 | 0; 55 tests, 0 failures | PASS | [06](evidence/2026-08-22/06-boundary-negative.txt) |
| EVD-T8-06A | public approved-root path escape | 22:07:04–22:07:05 | 0; 1 probe, 0 failures | PASS; result `REJECTED` | [06a](evidence/2026-08-22/06a-public-path-escape.txt) |
| EVD-T8-07 | secret-pattern scan | 22:04:11–22:04:12 | wrapper 0; raw grep 1 no-match | PASS | [07](evidence/2026-08-22/07-security-scan.txt) |
| EVD-T8-08 | Git integrity and scope | 22:04:25–22:04:26 | 0 | PASS | [08](evidence/2026-08-22/08-git-integrity.txt) |
| EVD-T8-R1-01 | `unittest discover -s tests -v` | 22:47:52–22:48:58 | 0; 100 tests, 0 failures | PASS | [10](evidence/2026-08-22/10-full-unittest-retest.txt) |
| EVD-T8-R1-02 | `pip check` | 22:47:52–22:47:53 | 0 | PASS | [11](evidence/2026-08-22/11-pip-check-retest.txt) |
| EVD-T8-R1-03 | five P2 directed contracts | 22:51:48–22:52:28 | 0; 5 tests, 0 failures | PASS | [15](evidence/2026-08-22/15-five-p2-directed-contracts-final.txt) |
| EVD-T8-R1-04 | correct-layout junction probe | 22:49:54–22:49:55 | 0; 1 probe | PASS; `MCP_COMMAND_UNTRUSTED` | [13](evidence/2026-08-22/13-correct-layout-junction-probe.txt) |
| EVD-T8-R1-05 | full and static validators | 22:53:21–22:53:24 | 0; 2 commands | PASS | [16](evidence/2026-08-22/16-validator-full-static-retest.txt) |
| EVD-T8-R1-06 | real stdio health ×3 | 22:53:41–22:53:45 | 0; 3 runs, 0 issues | PASS; exact eight tools and 0 Python processes after run | [17](evidence/2026-08-22/17-stdio-health-three-runs.txt) |
| EVD-T8-R1-07 | same-process clone setup / negative path | 22:58:03–23:00:28 | see recorded subcommands | PASS for stated success, skip, validator-failure, cwd, freeze, user-variable and cleanup assertions | [19](evidence/2026-08-22/19-same-process-clone-setup-final.txt) |

## Historical and Command-Execution Records Excluded from PASS Counts

| Record | Classification | Fact and disposition | Raw log |
|---|---|---|---|
| TC-T8-05A initial clone cleanup | HISTORICAL_BLOCKED | The first functional setup attempt retained its clone cwd; later-process deletion was not attempted by tester. This historical test-execution record remains `BLOCKED`. | [05 attempt 1](evidence/2026-08-22/05-setup-twice-attempt1-cleanup-blocked.txt) |
| Controller artifact cleanup | OBSERVED | Exact temp direct-child target was moved to Windows Recycle Bin; exit 0 and `Exists after: False`. Artifact risk is resolved and recoverable until the Recycle Bin is emptied; this does not rewrite the historical `BLOCKED` test record. | [05b](evidence/2026-08-22/05b-controller-cleanup.txt) |
| Initial boundary capture | COMMAND_ERROR | Capture was incomplete and is retained; it is not included in the 55-test PASS count. | [06 attempt 1](evidence/2026-08-22/06-boundary-negative-attempt1-output-capture-incomplete.txt) |
| Initial Git scope assertion | COMMAND_ERROR | Scope rule initially saw one non-evidence path; corrected integrity record is the PASS evidence. | [08 attempt 1](evidence/2026-08-22/08-git-integrity-attempt1-scope-rule-failed.txt) |
| First P2 direct command | COMMAND_ERROR | Invalid module entrypoints collided with the standard-library `platform` module; 5 errors, exit 1. Not a product failure and not a PASS count. | [12](evidence/2026-08-22/12-five-p2-directed-contracts.txt) |
| Second P2 direct command | COMMAND_ERROR | Four direct test-file invocations lacked `PYTHONPATH=.`; exit 1. The corrected run is EVD-T8-R1-03. | [14](evidence/2026-08-22/14-five-p2-directed-contracts-corrected.txt) |
| First same-process setup retest capture | COMMAND_ERROR | Harness treated an expected terminating validator-failure as an exception; a separate negative capture recorded the expected failure. It is not a PASS count. | [18](evidence/2026-08-22/18-same-process-clone-setup-retest.txt) |

## Independent Tester Conclusions

- At `2d3ae0a`, independent testing recorded 94/94 full-suite tests, dependency check, full validator, stdio contract ×3, retry-clone setup, 55 negative/boundary tests, public path escape, secret scan and Git integrity as PASS.
- At `ce9ca0e`, independent retesting recorded 100/100 tests, pip check, five P2 contracts, correct-layout junction rejection, full/static validator, three real stdio runs with exact eight tools and no residual Python processes, same-process setup behavior, secret scan and Git integrity as PASS.
- Codex restart/current-session MCP visibility is `NOT_EXECUTED`; [TC-002](TC-002-codex-restart-validation.md) is deliberately not pre-filled with a result.
- Redmine, RAGFlow and GitLab external calls are `NOT_EXECUTED`.
