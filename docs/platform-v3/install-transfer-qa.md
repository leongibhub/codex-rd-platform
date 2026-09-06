# Independent secure-install-transfer QA plan

Traceability: `TASK-V3-015`, `BUG-INSTALL-001`, `NFR-V3-004`, `REQ-V3-010`.  
Tester: `/root/v3_qa_platform`.

Revision 1 evidence below is historical only. The actual full-setup preflight
against commit `c3eb271` failed because its broad denylist rejected the
canonical public `knowledge/local/README.md`; this is `BUG-INSTALL-002` and
invalidated revision 1's installer conclusion. Revision 2's unit result is
historical; its integration `run-ab766bf5940941028bd8bc2f923f02a1` was
invalidated before evidence could be recorded. Revision 3 implementation is in
retry review after the initial fixture failure; its fresh unit/integration
evidence appears below.

The revision-2 fixture fixes its canonical input from the Git object
`HEAD:knowledge/local/README.md` / blob
`f361c8f3bd3b7bb62af25fb46bb48c0965c2e263`, using `git cat-file` bytes rather
than working-tree text. This deliberately avoids Windows CRLF checkout
conversion becoming the input that is both tested and accepted.

Revision 3's first integration attempt, `run-d3fab938a32c4f778104df548b7aaba2`,
is recorded by Runtime as a failed tester run. Its two failures compared a
Windows CRLF worktree checkout to LF Git-object bytes, rather than comparing
the delivered `HEAD:path` object identity. This was a QA fixture assertion
defect, not product evidence of a broadened allowlist; it remains historical
and does not supply revision-3 PASS evidence.

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
| TC-V3-IND-INSTALL-901 | Committed delivery accidentally includes ignored/untracked state or old Git metadata/history. | Current committed payload and a new current shallow Git checkout are present; setup observes the real HEAD; `.env`, `.venv`, `.rd-platform`, `.worktrees`, local knowledge, cache, untracked state, source hook/config marker and prior history are absent. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-902 | A stale destination is merged or overwritten. | Installer exits nonzero and a complete pre/post tree SHA-256 digest, including the sentinel bytes, is unchanged. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-903 | Source itself or a source descendant is accepted as destination. | Installer exits nonzero; source non-Git tree digest is unchanged; no child destination is created. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-904 | Legacy `-Force` requests a merge/overwrite behavior. | Installer exits nonzero and does not create the destination. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-905 | Source or destination junction/reparse point redirects operation. | Both calls exit nonzero; linked target sentinel remains unchanged and no delivery directory is created. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-906 | A forbidden local-state path is maliciously committed instead of ignored. | Each `.env`, `.worktrees`, `.pytest_cache`, `__pycache__`, and `cache` fixture rejects before delivery; no approved payload appears at destination. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-907 | Exact published `knowledge/local/README.md` needs to survive delivery for setup. | The independently fixed content and Git blob identity `f361c8f3bd3b7bb62af25fb46bb48c0965c2e263` are delivered; ignored private sibling remains absent. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-908 | A same-path README is changed after the published identity is fixed. | Delivery rejects before payload copy. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-909 | A neighbouring new `knowledge/local` file attempts to broaden the exception. | Delivery rejects before payload copy. | PASS (revision 3 attempt 2) |
| TC-V3-IND-INSTALL-910 | A Git tree records the exact published blob under a case-variant path only. | Delivery rejects before payload copy; Windows case folding must not broaden the path exception. | PASS (revision 3 attempt 2) |

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

## Revision 3 attempt 2 evidence

Frozen installer SHA-256:
`F99EFF0AC23E15D8386ABF7E428C0EB0FA150CBCEC5F92172053F52C20DEEB3C`.

| Quality phase | Runtime run | Command payload | Observable result |
| --- | --- | --- | --- |
| Unit | `run-3a171d0744de43b7b72d15ed6b08135c` | `.venv\\Scripts\\python.exe -B -X utf8 -m unittest tests.platform.test_install_transfer -q` | Exit 0; 12 tests passed (`Ran 12 tests in 14.946s`; Runtime duration 15.260210 s). |
| Independent integration | `run-7bd040f6d7614590a6958aa8bc9cc9b6` | `.venv\\Scripts\\python.exe -B -X utf8 -m unittest tests.independent_v3.test_install_transfer_independent -q` | Exit 0; 10 top-level tests passed (`Ran 10 tests in 20.933s`; Runtime duration 21.250697 s), including five forbidden-path subtests and TC-V3-IND-INSTALL-910's separately recorded Git case-variant tree. |

The successful canonical-stub checks compare the delivered Git
`HEAD:knowledge/local/README.md` object to blob `f361c8f3bd3b7bb62af25fb46bb48c0965c2e263`;
they intentionally do not compare Windows worktree CRLF bytes to Git-object LF
bytes. The task is ready for separate review. This independent result still
does not execute real dependency installation, production delivery, hosted CI,
release or a Gate decision.
