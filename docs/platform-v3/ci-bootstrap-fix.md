# Cross-platform local MCP bootstrap fix

Traceability: `TASK-V3-014`, `BUG-CI-004`, `NFR-V3-004`.

## Scope and minimal design

The local config rewriter derives the MCP interpreter from the repository root
and the host platform only: Windows uses `.venv/Scripts/python.exe`; non-Windows
uses `.venv/bin/python`. The rewrite postcondition uses the same helper as the
replacement, so it cannot validate a different path than it writes.

Only the three `company_context` TOML launch values may change. Existing
comments, line endings, multiline strings, other MCP sections, containment
validation and health-check behavior remain unchanged. The rewriter does not
create a virtual environment; CI bootstrap owns creation. On Linux bootstrap
must use `venv --copies` so the configured interpreter is a real in-root file
for the existing strict containment contract.

## Acceptance tests

| ID | Target | Expected observable result |
| --- | --- | --- |
| TC-CI-014-01 | Windows rewrite | Exact `.venv/Scripts/python.exe` command and matching postcondition. |
| TC-CI-014-02 | POSIX rewrite | Exact `.venv/bin/python` command and matching postcondition. |
| TC-CI-014-03 | Rewrite preservation | Comments/CRLF and non-target sections remain byte-identical. |
| TC-CI-014-04 | MCP stdio expectation | Test expectation follows the current native platform path without weakening containment. |

Developer verification and independent CI/QA evidence remain separate. This
change does not alter the running 8-hour benchmark or claim a workflow run has
passed.

## Developer verification

Executed on Windows with the repository virtual environment:

```text
.venv\Scripts\python.exe -X utf8 -m unittest tests.platform.test_config_rewrite tests.platform.test_mcp_stdio -v
```

Result: 17/17 tests passed. The run includes both synthetic Windows/POSIX path
branches, comment/CRLF preservation, the native current-platform config
expectation, current MCP stdio health checking, and existing rejection tests
for outside commands/cwd and junction containment. `compileall` and
`git diff --check` also exited successfully. Linux CI execution and independent
QA/review remain separate evidence.

## Independent integration attempt classification

The first independent integration attempt was `FAIL` before test execution
because a QA-owned fixture raised `SyntaxError`. This is `TEST_SCRIPT`
evidence, not a failure of this frozen production implementation. The frozen
`scripts/write_local_config.py` SHA-256 is
`1CE999C6D95FF7BD266D8AC467D348C151FCDB69147C2CAE73225A8672AABBE9`; its
developer focused baseline was re-run with 17/17 passing. QA fixture repair
and independent unit/integration re-execution remain pending.
