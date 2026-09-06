# Independent secure-install-transfer QA plan

Traceability: `TASK-V3-015`, `BUG-INSTALL-001`, `NFR-V3-004`, `REQ-V3-010`.  
Tester: `/root/v3_qa_platform`.

## Risk model

The previous installer recursively copied the daily working directory with
`-Force`. That could disclose credentials, Git internals, worktrees, virtual
environment state, Runtime databases, local knowledge and caches, while also
merging into an existing destination. The independent fixture therefore creates
an isolated two-commit Git source, then adds ignored and untracked local-state
sentinels *after* commit. Its mock setup only writes a marker after confirming a
real delivered Git `HEAD`; it neither installs dependencies nor contacts an
external service.

| Test | Risk / boundary | Required observable result | Status |
| --- | --- | --- | --- |
| TC-V3-IND-INSTALL-901 | Committed delivery accidentally includes ignored/untracked state or old Git metadata/history. | Current committed payload and a new current shallow Git checkout are present; setup observes the real HEAD; `.env`, `.venv`, `.rd-platform`, `.worktrees`, local knowledge, cache, untracked state, source hook/config marker and prior history are absent. | PASS |
| TC-V3-IND-INSTALL-902 | A stale destination is merged or overwritten. | Installer exits nonzero and a complete pre/post tree SHA-256 digest, including the sentinel bytes, is unchanged. | PASS |
| TC-V3-IND-INSTALL-903 | Source itself or a source descendant is accepted as destination. | Installer exits nonzero; source non-Git tree digest is unchanged; no child destination is created. | PASS |
| TC-V3-IND-INSTALL-904 | Legacy `-Force` requests a merge/overwrite behavior. | Installer exits nonzero and does not create the destination. | PASS |
| TC-V3-IND-INSTALL-905 | Source or destination junction/reparse point redirects operation. | Both calls exit nonzero; linked target sentinel remains unchanged and no delivery directory is created. | PASS |
| TC-V3-IND-INSTALL-906 | A forbidden local-state path is maliciously committed instead of ignored. | Each `.env`, `.worktrees`, `.pytest_cache`, `__pycache__`, and `cache` fixture rejects before delivery; no approved payload appears at destination. | PASS |

The executable suite is
`tests/independent_v3/test_install_transfer_independent.py`. It has not been
run against the old recursive installer. It operates exclusively under a new
temporary directory. No installer test here establishes a release, deployment,
human acceptance, or Gate decision.

## Executed independent evidence

Environment: Windows host `D:\\codex-rd-platform`, repository virtual
environment, Git and PowerShell 7.6.5; tester `/root/v3_qa_platform`. The
frozen installer SHA-256 was
`D70F2B23D803A01C96959344D539D27DFC6996AF3505A958B8C6754B7E24F978`.

| Quality phase | Runtime run | Command payload | Observable result |
| --- | --- | --- | --- |
| Unit | `run-b43bd8f02ce84ea0b0aeaa86a3862b61` | `.venv\\Scripts\\python.exe -B -X utf8 -m unittest tests.platform.test_install_transfer -q` | Exit 0; 8 tests passed (`Ran 8 tests in 9.000s`; Runtime duration 9.295934 s). |
| Independent integration | `run-0217df99c2934123b437282174ce5aed` | `.venv\\Scripts\\python.exe -B -X utf8 -m unittest tests.independent_v3.test_install_transfer_independent -q` | Exit 0; 6 top-level tests passed (`Ran 6 tests in 12.111s`; Runtime duration 12.413015 s), including the five prohibited-path subtests in TC-V3-IND-INSTALL-906. |

The executed integration fixture used a two-commit isolated source repository,
then created ignored/untracked sentinel files. Its marker-only delivered
`setup.ps1` verifies a real delivered Git `HEAD` and writes one marker; it does
not exercise dependency installation or any external service. The completed
task is ready for separately authorized review. A real dependency-installing
setup, production installation, hosted CI, release and Gate decision are
**NOT EXECUTED** in this tester record.
