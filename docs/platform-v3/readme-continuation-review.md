# TASK-V3-009 README continuation review

- Reviewer: `/root/v3_review_runtime`
- Role: independent reviewer; not the README author or tester
- Scope: `README.md` and `README.en.md` usage instructions at Git commit `62c153e8a14425ce4aa3146519129521ded25af5`, with read-only comparison to CLI help, `scripts/setup.ps1`, `scripts/write_local_config.py`, `install-to-D.ps1`, `.agents/skills/platform-orchestration/SKILL.md`, and the referenced command adapters
- Excluded: re-review of frozen Runtime implementation, Python lifecycle Gate evidence, hosted CI outcome, product acceptance, release, and any G0-G11 decision
- Initial verdict: **FAIL**; one P1 and two P2 findings require correction and a new complete quality attempt

## Evidence actually checked

- `python -X utf8 -m rd_platform --help` and the help for `snapshot`, `lifecycle`, `lifecycle-collection`, `lifecycle-report`, `project-export`, `test-run`, `run`, `stack-probe`, `stack-run`, and `stack-package` all executed successfully from the repository virtual environment.
- `python -X utf8 -m unittest tests.platform.test_readme_contract -v` executed 4 tests and reported 4 PASS. These tests did not cover the failures below.
- A synthetic temporary Git fixture was used only to reproduce checkout behavior. It contained an empty fixture commit and no project approval or production evidence. In a `--single-branch --branch main` clone, the documented `git fetch origin codex/platform-v3-lifecycle` returned 0 and populated only `FETCH_HEAD`; the next documented command returned 128 with `fatal: invalid reference: origin/codex/platform-v3-lifecycle`.
- A read-only expansion of the selection expression at `install-to-D.ps1:23-26` showed that the current checkout would copy `.git`, `.venv`, `.rd-platform`, `.worktrees`, `.pytest_cache`, and the whole `knowledge` directory. `.env` would also be selected when present because the script excludes only its own filename.

## Findings

### P1 — The recommended Windows copy installer transfers host-local state and possible secrets

- Location: `README.md:69`, `README.en.md:69`; implementation evidence `install-to-D.ps1:23-32`.
- Failure mode: the README recommends `install-to-D.ps1`, while the script recursively copies every source-root child except `install-to-D.ps1` itself. Git ignore rules are not consulted.
- Impact: the target can receive the source repository's `.git`, worktree metadata, non-portable `.venv`, Runtime database and raw execution evidence under `.rd-platform`, caches, local knowledge, and a possible `.env`. `-Force` additionally merges this state into an existing destination. This creates credential/privacy exposure, stale or corrupt Git/worktree state, and an installation that may reuse machine-specific executables.
- Required remediation: disable this README entry until implementation uses a reviewed tracked-file allowlist or equivalent clean delivery source. Explicitly exclude Git metadata, virtual environments, Runtime/output directories, worktrees, caches, local knowledge, env files, and other secret-bearing host state. Test using real ignored marker files and require failure not to leave a destination presented as successfully installed.

### P2 — The existing-clone commands fail for a legitimate single-branch clone and an existing local branch

- Location: `README.md:43-48`, `README.en.md:43-48`.
- Failure mode: fetching a source ref without a destination can leave it only in `FETCH_HEAD`; a single-branch clone has no `origin/codex/platform-v3-lifecycle`, so the subsequent tracked switch fails. If the local feature branch already exists, unconditional `git switch --track` also fails rather than continuing it.
- Impact: a documented primary continuation path cannot reach the required V3 source in common existing-clone states.
- Required remediation: add the feature branch to `remote.origin.fetch` (for example with `git remote set-branches --add`) and fetch it, then conditionally create a tracked local branch or switch and fast-forward an existing local branch. Exercise both states in temporary independent repositories, including a remote commit newer than the existing local branch.

### P2 — `test-run` overstates the executor identity guarantee

- Location: `README.md:151`, `README.en.md:151`; implementation evidence `rd_platform/lifecycle_runner.py:27-32`.
- Failure mode: the documentation says the command launches “under a real tester identity”. The adapter verifies only that the supplied `--executor-id` names a Runtime agent with the tester role and records it as metadata. It neither authenticates that identity nor changes the operating-system process identity.
- Impact: readers can mistake a trusted-host assertion for authenticated independent execution evidence.
- Required remediation: describe it as a registered tester ID declared by the trusted host, explicitly state that it is not authentication or OS impersonation, and require actual host-assignment evidence for independence.

### P3 — The clone verification comment names a stale observed commit

- Location: `README.md:39`, `README.en.md:39`.
- Failure mode: a fresh branch clone now resolves to `62c153e`, while the inline expected observation still says `2d77904`.
- Impact: a correct checkout appears inconsistent with the guide. This does not by itself execute the wrong code because the branch is explicit.
- Required remediation: either update the observation to the reviewed commit or remove the volatile expected SHA and direct readers to the commit-specific delivery record.

## Items found conformant in this bounded pass

- Documented CLI command names and option positions match current parser help, including global `--db` before `test-run`.
- The report versus lifecycle-report denominator warning, pagination/cursor boundary, export non-approval boundary, generic NFR-runner rejection, no-shell trusted argv boundary, pause versus external-process cancellation, and V2 quality phases versus V3 Case/Gate distinctions match the inspected contracts.
- The `platform-orchestration` prompt names an available repository Skill and correctly states that it constrains host work rather than launching a background service.
- The Linux manual setup commands match the native `.venv/bin/python` configuration rewrite path and do not claim one-step delivery or hosted PASS.

No Gate, human approval, deployment, release, or hosted CI result is approved by this review.

## Revision 2 pre-review observation

An intermediate documentation edit attempted to fetch directly into `refs/remotes/origin/codex/platform-v3-lifecycle`. The same single-branch fixture proved that insufficient: fetch returned 0 and the ref existed, but Git still returned 128 from `git switch --track -c ... origin/codex/platform-v3-lifecycle` with `starting point ... is not a branch` because the remote's configured fetch mapping still covered only `main`. Its existing-local-branch path also switched without fast-forwarding to the fetched revision. This intermediate text is not an accepted fix; the complete revised commands and their tests remain pending.

## Revision 2 final review

- Final scoped verdict: **APPROVED** for the revised `README.md` / `README.en.md`; no unresolved P0-P2 README finding remains.
- Independent QA evidence read: unit `run-7c00698431da4be59069aba0fe6ff4d6` (5/5 PASS) and targeted integration `run-140e4f0d35af4e38acec792367e2d84c` (2/2 PASS).
- Independent reviewer execution: `run-cf53be71a6e64fc7a3ed61c58c667d25`, 5/5 PASS, exit 0. Runtime task `task-9046486dcff54b89b6cec5c3c2e1e387` then reported revision 2 `DONE`, 4/4 quality checks.
- The reviewer also repeated the missing-local-branch flow and then advanced the synthetic remote by one commit; the existing local branch fast-forwarded and its final `HEAD` equalled the remote tip.
- The revised guide no longer recommends the unsafe copy installer. It names the transferred host-local categories and directs users to a clean branch clone. This mitigates the README execution risk but does **not** close or approve `BUG-INSTALL-001` / TASK-V3-015; the installer implementation remains independently reviewable work.
- The tester identity wording now matches the trusted-host boundary: registered role metadata is not identity authentication or OS impersonation, and actual independence still needs host-assignment evidence.
- The current report/export/query/test-run/phase/Gate wording remains within the inspected implementation contract. The public GitHub run link displayed commit `62c153e`, status `Success`, two completed jobs in each of its two matrices, and four artifacts; logs and subsequent uncommitted README/installer changes were not treated as covered CI evidence.

This approval is limited to the two revised usage guides and their revision-2 tests. It is not approval of `install-to-D.ps1`, setup on every machine, Python project Gates, hosted execution of uncommitted changes, release, deployment, or human acceptance.
