# Independent portable MCP bootstrap QA

Traceability: `TASK-V3-014`, `BUG-CI-004`, `NFR-V3-004`.  
Tester: `/root/v3_qa_platform`.

## Risk model and test cases

| Test | Risk / user-facing contract | Observable expected result | Status |
| --- | --- | --- | --- |
| TC-V3-IND-CI-801 | A checkout moved to the native host writes a command for a different OS, or rewrites unrelated config content. | Executing the rewriter on the current host writes the exact in-root native interpreter, server and CWD; unrelated section, CRLF, and target comment remain preserved. | PASS |
| TC-V3-IND-CI-802 | Invalid launch input causes a partial or destructive config write. | Process exits nonzero and the original config bytes are unchanged. | PASS |
| TC-CI-014-01 through 04 | Unit and public stdio/validator contracts. | Registered task quality commands pass on this host; actual stdio health and negative validator contracts are exercised. | PASS |

The independent test module is
`tests/independent_v3/test_ci_bootstrap_independent.py`. It creates only
temporary configuration roots. It does not create an environment, alter this
repository's `.codex/config.toml`, run a hosted workflow, or substitute a
Windows result for the required POSIX health check.

## Preflight and failure history

The first registered integration attempt is `run-db0d478ee2e44510bd341eaefe6d02cc`.
It failed at module import with a `SyntaxError` in this tester-owned file, before
any product assertion ran. This is recorded as a `TEST_SCRIPT` fixture defect,
not as product behavior or a closure of `BUG-CI-004`.

After correcting the fixture, preflight used
`.venv\\Scripts\\python.exe -B -X utf8 -m py_compile
tests\\independent_v3\\test_ci_bootstrap_independent.py` (exit 0) followed by
`.venv\\Scripts\\python.exe -B -X utf8 -m unittest
tests.independent_v3.test_ci_bootstrap_independent -q` (2/2 PASS in 0.326 s).
The qualified test file SHA-256 is
`73803D8B9F74557144CE4AA3987867FF47DA702B3F77E2372D4580E6846F65E9`.
This preflight did not replace the fresh Runtime unit/integration quality
chain.

## Attempt 2 independent quality evidence

Environment: Windows host, `D:\\codex-rd-platform`, repository virtual
environment, tester identity `/root/v3_qa_platform`. Frozen rewriter source
SHA-256: `1CE999C6D95FF7BD266D8AC467D348C151FCDB69147C2CAE73225A8672AABBE9`.

| Quality phase | Runtime run | Command payload | Observable result |
| --- | --- | --- | --- |
| Unit | `run-902667645b69434e9266a0743c545265` | `.venv\\Scripts\\python.exe -m unittest tests.platform.test_config_rewrite tests.platform.test_mcp_stdio -q` | Exit 0; 17 tests passed (`Ran 17 tests in 10.012s`; Runtime duration 11.250360 s). |
| Independent integration | `run-e66d28dd9bd6471f9647901e62002f78` | `.venv\\Scripts\\python.exe -m unittest tests.platform.test_validator_contract tests.independent_v3.test_ci_bootstrap_independent -q` | Exit 0; 29 tests passed (`Ran 29 tests in 33.346s`; Runtime duration 33.885056 s). |

The integration command includes actual native stdio health checking and
negative validator contracts, plus TC-V3-IND-CI-801 and TC-V3-IND-CI-802. The
task is ready for its separately authorized review phase. A hosted POSIX health
check/workflow run remains **NOT EXECUTED** in this tester record, and neither
these local tests nor the task state constitute a Gate or release conclusion.
