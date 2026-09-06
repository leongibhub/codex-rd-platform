# V3 Actual-CI Fix Independent Review

- Reviewer: `/root/v3_review_runtime`
- Date: 2026-09-06
- Scope: `TASK-V3-011` through `TASK-V3-014`, created from the four failures in actual GitHub Actions run `34029576291`
- State: **COMPLETE — TASK-V3-011/012/013/014 implementation fixes approved; repaired hosted CI rerun remains pending**
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

## TASK-V3-013 / BUG-CI-003 — REVISION 3 APPROVED; ONLINE RETEST PENDING

Reviewed source: `.github/workflows/platform-validation.yml`, `rd_platform/stack_harness.py`, the existing C++ adapter, `tests/runtime/test_native_tool_probe.py`, `tests/platform/test_ci_contract.py`, the stack-harness regressions, and independent TC1204/1205.

Windows tool probing now recognizes an existing `g++`/`g++.exe` as `cxx` while the application adapter retains its prior WSL fallback when native GNU C++ is absent. Java resolution appends `.exe` only on Windows, so each matrix OS tests its native `JAVA_HOME/bin` spelling. Both workflow jobs declare Java 8 and Node 22. Before the Windows manifests run, PowerShell locates the exact `g++.exe`, asks that compiler for `libstdc++-6.dll`, requires the reported DLL to exist, and writes both compiler and runtime directories to `GITHUB_PATH`. GitHub's documented workflow-command contract prepends such directories to `PATH` for subsequent steps, where the real C++ build/unit/integration executes: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-system-path>.

Independent revision-2 review reran the two native-tool checks, three workflow contracts, thirteen stack-harness regressions, and corrected current-OS TC1204/1205: 20/20 PASS. Actual Runtime review `run-bc28f89da2314e889d1249338c50bfd0` approved only that scoped implementation. Revision-1 integration `run-377e593ecc8c4653b98f956d772c530b` remains historical/superseded because its fixture incorrectly required WSL on Windows; it was not reused as revision-2 evidence.

The second actual workflow, GitHub Actions run `34030786796` at commit `ba17e3524c41c75b17219b4a7c71a6d2b4e35631`, again built native Windows C++ successfully but the unit executable returned `0xC0000139`. That result is authoritative evidence that revision 2's PATH-only implementation did not recover the Bug; the old review PASS was not online validation and is not reused as closure.

Revision 3 adds `-static-libstdc++` and `-static-libgcc` to both native-Windows link commands only. POSIX and Windows-WSL compilation retain their prior flags. Independent review reran the frozen 20 unit/contracts (20/20 PASS), then forced `os=nt` plus the WSL branch and inspected both application/unit link argv: neither contained the Windows static flags. A separate actual public `stack-run` used the host's WSL fallback because native `cxx` was `NOT_AVAILABLE`; build PASS, unit reported five tests, and integration reported three checks. This proves WSL regression safety, not native Windows recovery.

Actual revision-3 Runtime review: `run-f61445255fd3489f9c8c4cb7419c1ea7`; task `task-ef5124d4909940758962ca113a8854b4` revision 3 is DONE. No P0–P3 implementation finding remains. Acceptance of the new static flags by the hosted Windows GNU compiler and recovery from `0xC0000139` remain `NOT_EXECUTED` until the third hosted workflow.

## Remaining external verification

All four scoped implementation tasks are DONE. A third GitHub Actions run must still execute the repaired commit on Linux and Windows before the actual CI recovery can be concluded. A successful local review is not that hosted result and alters neither the first four-job FAILURE record nor the second Windows `0xC0000139` failure.
