# TASK-V3-015 independent installer review

- Reviewer: `/root/v3_review_runtime`
- Role: independent reviewer; not the implementation or QA owner
- Scope: `install-to-D.ps1`, its TASK-V3-015 design/QA records, and focused installer tests
- Frozen implementation SHA-256: `D70F2B23D803A01C96959344D539D27DFC6996AF3505A958B8C6754B7E24F978`
- Traceability: `TASK-V3-015`, `BUG-INSTALL-001`, `NFR-V3-004`, `REQ-V3-010`
- Pre-review state: **IN REVIEW**; no PASS is recorded before independent unit/integration evidence and the actual Runtime review phase

## Review boundary

This review evaluates the local trusted-source transfer contract: fixed committed tree, exclusion of ignored/untracked host state and old Git metadata, source/destination path rejection, no overwrite/legacy Force behavior, bounded failure handling, and setup invocation. It does not claim a malicious-filesystem sandbox, general secret/DLP scanning, dependency availability, installation on every Windows configuration, release, deployment, human acceptance, or any G0-G11 decision.

## Source inspection

- The former recursive `Get-ChildItem -Force` / `Copy-Item -Recurse -Force` path is removed.
- Source `HEAD^{commit}` is captured once. The denylist inspection, depth-one fetch, and detached checkout all name that same object ID, so an ordinary concurrent source-HEAD advance cannot substitute an unchecked tree.
- A fresh destination repository is initialized and fetched from the source path without configuring it as a remote. The source `.git` directory, hooks/config, full history, ignored/untracked files, Runtime DB/output, virtual environment, worktrees, caches, local knowledge, and `.env` are therefore not recursively copied.
- `-Force`, a non-directory or non-empty destination, source equality/descendants, and pre-existing reparse points in source/destination path ancestry are rejected before delivery. The implementation never deletes or merges an existing destination.
- Initialization/fetch/checkout/setup errors do not reach the final `Installed at` message. A newly created target receives a plain `.install-failed` marker when the marker itself can be written.
- The source documents accurately limit static reparse checks: a malicious concurrent filesystem replacement after validation is outside this trusted-local helper's isolation contract.

## Pending independent evidence

The implementation owner reported a formal follow-up implementation Run and 8/8 developer tests, but those are not independent approval evidence. This review remains open until the assigned tester completes the frozen unit and integration suites and the reviewer independently repeats the relevant cases.

## Final independent review

- Verdict: **APPROVED** for the bounded TASK-V3-015 committed-source transfer contract; no P0-P2 finding remains in the frozen implementation.
- Independent tester evidence: unit `run-b43bd8f02ce84ea0b0aeaa86a3862b61` reported 8/8 PASS; integration `run-0217df99c2934123b437282174ce5aed` reported 6/6 top-level PASS, including five committed-path denylist subtests.
- Reviewer execution: `run-de25af2e50244082b82f52a839ce8197` ran both frozen suites together and reported 14/14 PASS, exit 0. Runtime task `task-7bec21bef03742fb950cac713497d128` then reported `DONE`, 4/4 quality checks.
- Additional reviewer probe: a synthetic committed fixture changed its setup script to throw `fixture setup failure`. The installer exited 1, wrote `.install-failed`, exposed the failure diagnostic, and did not print `Installed at`.
- The original BUG-INSTALL-001 history remains material: the superseded implementation copied Git state, Runtime data, worktrees, virtual environments, local knowledge/caches, and possible secrets. The new result does not rewrite that history.

The successful tests use harmless temporary setup doubles. A full dependency-installing setup in a fresh delivered checkout, hosted CI for this uncommitted change, general secret scanning, hostile concurrent filesystem mutation resistance, production installation, Gate decision, release, deployment, and human acceptance remain **NOT EXECUTED** or outside this review scope.

## Revision 2 reopening — BUG-INSTALL-002

- Current verdict: **FAIL / RE-REVIEW REQUIRED**. The revision-1 scoped PASS above is retained as history but is not valid for the new installation semantics.
- Severity: **P1** for TASK-V3-015 acceptance because the first real full installation of pushed commit `c3eb271089c0599b54775b2b4d3cb1c349a62bd0` exited 1 before transfer.
- Reproduction: the canonical committed source contains `knowledge/local/README.md`. Revision 1 rejected every committed path below `knowledge/local`, so the real repository always matched the denylist. The public policy stub is non-sensitive and has verified Git blob `f361c8f3bd3b7bb62af25fb46bb48c0965c2e263`.
- Required contract: any exception must be limited to the exact canonical path **and** exact approved blob/content identity. A changed canonical stub, any sibling/descendant under `knowledge/local`, case/path variants, and all other blocked local-state paths must still fail before delivery.
- The real failed install remains evidence and must not be replaced by the revision-1 fixture PASS. Revision 2 requires a new implementation, unit, integration, and review chain. GitHub Actions run `34032544002` was still running when the task was reopened and is not recorded here as PASS.

### Revision 2 pre-review finding

- **P2 — canonical Git path comparison was not exact.** The first revision-2 implementation used PowerShell `-eq`, which is case-insensitive. A same-blob path such as `KNOWLEDGE/local/README.md` could therefore enter the exception even though Git tree paths and the stated allow rule identify one exact case-sensitive path.
- Required correction: use case-sensitive path equality and retain the ordinary case-insensitive denylist for every non-exact variant. Add a negative case containing the approved blob at a case-variant path and require rejection before payload delivery.
- This finding caused revision 2 evidence to be invalidated and TASK-V3-015 to advance to revision 3. No revision-2 PASS is reused.

## Revision 3 pending review

The current candidate uses `-ceq` for the canonical path and includes a same-blob case-variant negative regression. It remains unapproved until a complete fresh revision-3 implementation, unit, integration, and independent review sequence finishes against one frozen source SHA.
