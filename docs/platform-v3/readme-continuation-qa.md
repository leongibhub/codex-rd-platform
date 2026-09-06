# TASK-V3-009 README continuation independent QA

Execution owner: `/root/v3_qa_apps` (independent Tester)  
Date: 2026-09-06  
Status: revision-2 independent unit and targeted integration PASS; Task is READY for independent review. This is not a Gate, release, hosted-CI, or human-acceptance decision.

## Test model and environment

The active tests derive from the README’s clone/continuation and `test-run` safety claims. They use disposable local Git repositories only; they do not inspect this checkout’s `origin`, mutate a real remote, create a global Git configuration, or run setup against the real workspace.

| Case | Risk and objective | Data / steps | Expected result | Initial actual result | Status |
| --- | --- | --- | --- | --- | --- |
| TC-V3-README-005 | `BUG-DOC-001`, `REQ-V3-010` / a single-branch `main` clone cannot continue safely to the V3 branch | Create a disposable local remote with `main` and `codex/platform-v3-lifecycle`; exercise a new feature clone, a shallow main-only clone, the old fetch/switch flow, the documented remote-mapping flow, and an already-local branch after the remote tip advances. | Old flow must RED. The documented flow must create an actual `origin/` tracking ref, create a missing local branch, and fast-forward (not merely switch) an existing local branch to the current remote tip. | Historical RED retained: old `git fetch origin BRANCH` returned 0 but only wrote `FETCH_HEAD`; switch then failed. The earlier one-off refspec created a ref but `switch --track -c` exited 128 because the branch was not in `remote.origin.fetch`. Revision 2 PASS: `remote set-branches --add` + `fetch origin` created the ref; new clone, main-only clone and existing-local-branch paths passed; `HEAD` equalled the deliberately advanced remote tip after `merge --ff-only`. | PASS (regression fixed; historical defect evidence retained) |
| TC-V3-README-004 extension | `NFR-V3-004`, `REQ-V3-010` / `--executor-id` is misread as authentication or OS impersonation | Read both README test-run sections. | Both describe only a trusted-host-declared, Runtime-registered tester ID; explicitly deny authentication and OS-user impersonation. | PASS: both guides contain all three boundaries; the targeted integration execution independently rechecked them. | PASS |
| TC-V3-README-006 (historical) | `BUG-INSTALL-001` / recursive installer leaks secrets, database, worktrees, caches or local knowledge | Copy the actual installer to a temporary fixture source with marker files under `.git`, `.venv`, `.rd-platform`, `.worktrees`, `.env`, `knowledge/local` and `cache`; use a harmless temporary setup stub; run installer to a temporary destination. | Destination must contain only approved delivery content; none of the host-local markers/directories may exist. | All seven forbidden entries were copied into the destination: `.git`, `.venv`, `.rd-platform`, `.worktrees`, `.env`, `knowledge/local`, `cache`. The temporary target is removed automatically after the assertion. | FAIL / transferred to TASK015 installer QA |

## Observable command evidence

Initial command: `.venv\Scripts\python.exe -X utf8 -m unittest tests.platform.test_readme_contract -v`.

It initially ran six cases: TC-001–004 passed; TC-005 and TC-006 failed as stated above. TC-006 is now historical Task015 evidence; the active Task009 suite contains TC-001–005. This is an actual local RED, not a Gate, release, online CI, fresh-network-clone, installer usability, or human-acceptance conclusion.

## Revision-2 execution evidence

The frozen README continuation text registers the feature branch in `origin`'s fetch mapping before `fetch origin`. It then tracks a missing local branch or fast-forwards an existing local branch only. The integration fixture exercised the actual Git commands against disposable file remotes, including a remote feature commit made after the local branch existed.

| Runtime phase | Execution ID | Command | Observable result |
| --- | --- | --- | --- |
| Unit | `run-7c00698431da4be59069aba0fe6ff4d6` | `.venv\\Scripts\\python.exe -X utf8 -m unittest tests.platform.test_readme_contract -q` | PASS, 5 tests in 5.193 s, exit 0. |
| Targeted independent integration | `run-140e4f0d35af4e38acec792367e2d84c` | `.venv\\Scripts\\python.exe -X utf8 -m unittest tests.platform.test_readme_contract.ReadmeContractTests.test_tc_v3_readme_005_feature_branch_continuation_uses_remote_mapping_and_handles_local_branch tests.platform.test_readme_contract.ReadmeContractTests.test_tc_v3_readme_004_local_host_and_native_boundaries_are_explicit -q` | PASS, 2 tests in 4.059 s, exit 0. |

This does not erase BUG-DOC-001's initial actual RED. The installer requires an allowlist-based delivery design (or continued explicit rejection); its historical failure is owned by TASK015 and remains separate from this Task009 conclusion.

## Limits

No actual GitHub remote, GitHub Actions, network clone, Venv install, MCP configuration, native WeChat, browser flow, production database, Gate decision, release, or human approval was run. The historical installer fixture used a disposable setup stub solely to stop installation after testing the actual installer’s copy boundary; it does not validate setup behavior.
