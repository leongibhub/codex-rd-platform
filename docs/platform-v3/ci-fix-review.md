# V3 Actual-CI Fix Independent Review

- Reviewer: `/root/v3_review_runtime`
- Date: 2026-09-06
- Scope: `TASK-V3-011` through `TASK-V3-014`, created from the four failures in actual GitHub Actions run `34029576291`
- State: **IN PROGRESS — TASK-V3-011/012/014 approved; TASK-V3-013 awaiting corrected independent QA evidence**
- Evidence boundary: this review does not rewrite the first CI run, claim a hosted rerun, close a Bug, decide a lifecycle Gate, or grant human/release acceptance.

## TASK-V3-011 / BUG-CI-001 — APPROVED

Affected contract: deterministic Store JSON admission and transaction atomicity across supported hosts. Reviewed source: `rd_platform/store.py`, `tests/runtime/test_json_limits.py`, and `tests/independent_v3/test_ci_json_limits_independent.py`.

The implementation walks JSON-compatible containers iteratively before encoding and after decoding. Root-container depth 64 is accepted; depth 65 and 5,000 are rejected independently of the encoder recursion threshold. Expanded value nodes include containers and repeated shared references: 100,000 nodes are accepted and 100,001 rejected. Only identities on the active ancestry path are treated as cycles, so shared acyclic DAGs remain legal while direct and indirect cycles fail. Non-finite values, object keys, decoder constants and exponent overflow fail closed. Runtime serializes the request before opening its write transaction; independent fixtures compared the complete SQLite `iterdump()` digest after deep, wide and cyclic rejections and found no mutation.

Independent executions:

| Host | Command | Result |
| --- | --- | --- |
| Windows Python | `.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_json_limits tests.independent_v3.test_ci_json_limits_independent tests.runtime.test_runtime -v` | 32/32 PASS |
| WSL Ubuntu-22.04 Python 3.10 | `python3 -m unittest tests.runtime.test_json_limits tests.independent_v3.test_ci_json_limits_independent tests.runtime.test_runtime -v` | 32/32 PASS |

Actual Runtime review run: `run-092ae7d4b1664f14b5a535255158dac6`; task `task-53affd29dde44db7bd0f82ca99673706` is DONE.

No P0–P3 finding remains in this scoped fix. `Store.loads` necessarily allocates parsed JSON before applying the structural walk; the existing HTTP 64 KiB ingress limit remains the transport guard. The implementation does not claim a general host-side string/memory sandbox. Actual Linux Python 3.13 CI verification remains pending a new hosted run.

## TASK-V3-012 / BUG-CI-002 — APPROVED

Reviewed source: `examples/multistack/java_booking/build.py`, its manifest, `tests/runtime/test_java_clean_build.py`, the existing stack-harness contracts, and independent TC1201–1203. The frozen `build.py` and manifest SHA-256 values were respectively `6a3648acbd398cd8a11b8d41e7d46ab1587eb2903f17fbb5aa28b7fb738c3856` and `b089e5fc28ad7b4047332cde400f3cd7715e9fecf0f8cd3a50eb89c06ed0257d`.

The manifest now invokes a Python argv-only driver which validates an absolute application child below the repository `.rd-platform/build` tree, rejects lexical traversal plus existing symlink/junction/reparse components, creates the previously missing `classes` directory, and calls the same six Java sources with `shell=False`. Compiler nonzero status is preserved and prevents downstream phases from running. A real JDK 8 clean workspace compiled from an absent classes directory, emitted class-file major version 52, passed unit/integration, left the copied Java source byte-identical, and placed no class file in that source tree.

Independent review reran the nine Java driver/real-build checks, thirteen stack-harness regressions, and independent TC1201–1203: 25/25 PASS. Relative, repository-external, source, parent-traversal, build-base and real junction targets were rejected before compilation; spaces and shell metacharacters remained single argv elements. Actual Runtime retry review: `run-03123e673058451caa7591e84254a41e`; task `task-9fe93a6e2e9e484a8db6c886854ce134` is DONE.

The initial unit failure `run-3bc7d50bf08f44ceb9578409b206da7d` remains a `TEST_SCRIPT` encoding failure: a hidden Windows process decoded localized `cmd /c mklink` output as UTF-8 before product assertions. The corrected fixture captures bytes and decodes diagnostics with replacement; it was not weakened to skip the real junction. No P0–P3 product finding remains. The build adapter explicitly does not claim to sandbox a concurrently malicious local process, and repaired hosted Ubuntu execution remains `NOT_EXECUTED`.

## TASK-V3-014 / BUG-CI-004 — APPROVED

Reviewed source: `scripts/write_local_config.py`, `.github/workflows/platform-validation.yml`, `tests/platform/test_config_rewrite.py`, `tests/platform/test_mcp_stdio.py`, `tests/platform/test_validator_contract.py`, and `tests/independent_v3/test_ci_bootstrap_independent.py`.

The native-path helper selects `.venv/Scripts/python.exe` on Windows and `.venv/bin/python` on POSIX. The Runtime CI job creates that repository-local environment with `venv --copies`, installs the declared MCP dependency set into it, rewrites the checked-out config from `GITHUB_WORKSPACE`, and then invokes all Runtime/platform test commands through the same interpreter. The rewriter changes only `company_context` command, args and cwd, reparses the result, and compares the complete parsed document against the intended three-field update before atomically replacing the original. Invalid input or a failed postcondition leaves the original bytes unchanged; CRLF, comments, multiline decoys, and unrelated MCP sections remain preserved.

The existing health resolver remains fail-closed: the resolved command must be an existing file under the canonical repository `.venv`, cwd must equal the repository root, the server argument must resolve to the exact in-root server, and required/enabled/timeouts/environment names retain their exact contracts.

Independent executions comprised 17 config/MCP checks, 27 validator checks, and two black-box rewrite/no-overwrite checks: 46/46 PASS. Actual Runtime retry review: `run-7e0e6e617c964d0aa34358e5f0465caf`; task `task-a6e58b30639347709ac8067ecb9a3fcb` is DONE. The initial integration `SyntaxError` remains recorded as a tester-owned `TEST_SCRIPT` failure and was not relabelled as product behavior.

No P0–P3 product finding remains in this scoped fix. The review host's WSL provides Python 3.10, below the platform's declared Python 3.11 minimum, so it was not used to fabricate POSIX success. A repaired hosted POSIX workflow and stdio health run remain `NOT_EXECUTED`.

## Pending increments

- `TASK-V3-013` / `BUG-CI-003`: Windows native GNU runtime and tool probing — production source is frozen, but review awaits a fresh integration run of the corrected current-OS test. The earlier tester run exercised a WSL-only fixture and cannot bind the subsequently changed test source.
