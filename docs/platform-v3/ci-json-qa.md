# Independent CI JSON-admission QA plan

Traceability: `BUG-CI-001` / Store JSON-admission contract.  
Owner: `/root/v3_qa_platform` (independent tester).  
Status: **EXECUTED** — developer implementation was frozen and the Runtime
registered independent tester quality runs on 2026-09-06. Online CI re-run and
independent review remain **NOT EXECUTED** in this record.

## Risk model

The original CI failure on Linux Python 3.13 showed that relying on the
interpreter JSON encoder's recursion threshold is not a deterministic security
boundary. The independent suite therefore treats JSON admission as an explicit
contract at both `Store.dumps` and `Store.loads`, then verifies the public
Runtime does not mutate the SQLite database when admission rejects input.

| Test | Boundary / abuse case | Required observable result | Status |
| --- | --- | --- | --- |
| TC-V3-IND-CI-701 | Root-container depth 64 vs 65, including a root dictionary composition. | 64 accepted, 65 rejected before encoder invocation. | PASS |
| TC-V3-IND-CI-702 | 5,000-level iterative list on a permissive interpreter. | `ValueError` before encoder invocation; no recursion-dependent acceptance. | PASS |
| TC-V3-IND-CI-703 | Direct/indirect cycle and shared DAG. | Cycles rejected; shared acyclic references accepted. | PASS |
| TC-V3-IND-CI-704 | 100,000 vs 100,001 expanded values; shared DAG expansion. | Exact boundary accepts then rejects; sharing cannot evade expanded-node budget. | PASS |
| TC-V3-IND-CI-705 | `loads` depth/node limit plus `NaN`, infinities, and overflowing numeric literals; `dumps` non-finite values/keys. | Same admission rule after parse; all non-finite values rejected. | PASS |
| TC-V3-IND-CI-706 | `Runtime.execute('task.create')` with deep, wide, and cyclic inputs. | Public API raises; complete SQLite `iterdump()` SHA-256 is unchanged after every rejection. | PASS |

The suite is at
`tests/independent_v3/test_ci_json_limits_independent.py`. It creates only
temporary databases and does not exercise, restart, or infer a result from the
live eight-hour soak.

## Executed evidence

Environment: Windows host, repository working directory
`D:\\codex-rd-platform`, `.venv\\Scripts\\python.exe`; tester identity
`/root/v3_qa_platform`. The task controller is
`task-53affd29dde44db7bd0f82ca99673706` (attempt 1).

| Quality phase | Runtime run | Exact command payload | Observable result |
| --- | --- | --- | --- |
| Unit | `run-d32eb7c9762048be910b1b2ee9c6f4e9` | `.venv\\Scripts\\python.exe -m unittest tests.runtime.test_json_limits tests.runtime.test_runtime -q` | Exit 0; 26 tests passed (`Ran 26 tests in 1.633s`; Runtime duration 1.999275 s). |
| Independent integration | `run-61a302cf10e04397aa7e6240b056759f` | `.venv\\Scripts\\python.exe -m unittest tests.independent_v3.test_ci_json_limits_independent -q` | Exit 0; 6 tests passed (`Ran 6 tests in 0.143s`; Runtime duration 0.581877 s). |

The integration run covers TC-V3-IND-CI-701 through TC-V3-IND-CI-706 and is
the observable basis for the PASS statuses above. The public-API rejection
test computes a full SQLite `iterdump()` SHA-256 before and after each rejected
payload; those digests matched in the executed test.

## Boundaries not concluded here

The historical Linux Python 3.13 CI failure for `BUG-CI-001` remains preserved
as a failure history. A hosted CI re-run is **NOT EXECUTED** by this tester and
is not inferred from the local runs. Independent review is also **NOT
EXECUTED** here; the Runtime task is ready for the separately authorized review
phase, not a Gate or release decision.
