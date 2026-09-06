# V3 Lifecycle / Runtime Independent Review

- Review role: independent reviewer / read-only gatekeeper
- Review scope: `rd_platform/lifecycle*.py`, `runtime.py`, `store.py`, `stack_harness.py`, and the V3 CLI/HTTP/board/report adapters
- Design baseline: `docs/superpowers/specs/2026-09-06-platform-v3-design.md` (`DES-V3-001`)
- Code baseline: working tree derived from `9655f33`; this report does not assert that uncommitted files are a release artifact
- Review evidence: code inspection plus isolated temporary-database synthetic fixtures; no fixture approval, deployment, test result, or defect closure in this review is project evidence
- Initial decision: **FAIL** — the review/remediation cycle reproduced four P1 and six P2 findings before retry.
- Final scoped review decision: **APPROVED** — all reproduced P1/P2 findings below were remediated and independently re-reviewed. This is a code-review conclusion, not a project Gate, human acceptance, release, or deployment decision.

## Findings

### P1 — Unauthenticated public method can mint `VERIFIED` human approval — RESOLVED / VERIFIED

- Affected requirements: `REQ-V3-004`, `REQ-V3-007`, `NFR-V3-005`; ADR-V3-003.
- Evidence: `Runtime.register_human_approval()` (`rd_platform/runtime.py`) explicitly trusts every local caller and forwards an arbitrary `operator` string. `LifecycleService.human_approval()` (`rd_platform/lifecycle.py`) only proves that the string is not an ID in `agents`; it then assigns `source.kind=human` and `recorded_role=human` itself.
- Failure mode: a model/plugin or ordinary Python caller in the same process calls the public method with `operator="arbitrary-unregistered-string"`. No trusted UI interaction, authenticated identity, approval-provider attestation, or complete project/Gate/subject binding is required.
- Reproduction: an isolated temporary DB accepted an explicitly synthetic statement saying no human acted and returned `status=VERIFIED`, `recorded_role=human`, `recorded_by=arbitrary-unregistered-string`.
- Impact: G9–G11 and deployment readiness can consume platform-minted approval as if it were an external human fact. Merely omitting the method from `execute`, CLI, and HTTP is channel separation, not an authorization boundary.
- Required remediation: default-deny unless an injected trusted approval verifier authenticates the operator interaction and validates the exact project, Gate, decision, statement, and locked subject versions. Persist verifier provenance/attestation ID; make synthetic unit providers unmistakably fixture-only and unavailable in production defaults.
- Retry evidence: the default runtime now rejects approval registration when no provider is configured. An injected provider must return authenticated identity plus the exact digest of the platform-computed project/Gate/decision/statement/current-subject/policy binding. Focused tests and independent code review confirmed the prior bare-operator reproduction no longer succeeds.

### P1 — A critical defect can close with no completed fix task — RESOLVED / VERIFIED

- Affected requirements: `REQ-V3-006`; design section 7 defect lifecycle.
- Evidence: `defect_fix()` in `rd_platform/lifecycle_testing.py` validates only that `fix_task_id` resolves to a current `TASK` artifact. It does not require the task artifact to be baselined/approved, connect it to a V2 task/work order, or prove the implementation/unit/integration/review loop reached `DONE`.
- Failure mode: register a DRAFT `TASK-001`, attach generic verified evidence, call `defect.fix`, run the required independent synthetic PASS retest, and provide a reviewer closure record.
- Reproduction: an isolated temporary DB moved a `CRITICAL` defect through `OPEN → FIXED → RESOLVED → CLOSED` while `TASK-001.state=DRAFT` and the V2 project contained zero tasks.
- Impact: the platform can represent a critical product defect as closed even though no fix implementation was completed. Independent retest/review identity checks do not repair the missing implementation fact.
- Required remediation: define one authoritative completed-task reference (prefer a typed V2/current work-order bridge), lock its revision/attempt, require its full quality loop to be `DONE`, and reject DRAFT/stale/invalidated task evidence. Recheck that completion at resolve and close time.
- Retry evidence: the defect fix now binds a current BASELINED/APPROVED TASK artifact to an actual same-project V2 task whose current revision/attempt is `DONE` with implementation, unit, integration and independent review PASS runs. Resolve and close revalidate that completion. The old DRAFT/no-task reproduction is covered by a failing negative test and no longer succeeds.

### P1 — Prior Gate PASS remains consumable after its locked repository evidence changes — RESOLVED / VERIFIED

- Affected requirements: `REQ-V3-004`, `REQ-V3-009`, `NFR-V3-005`; design section 8 Gate freshness/all prerequisites.
- Evidence: `policy_inputs()` / `evaluate()` in `rd_platform/lifecycle_governance.py` represent prerequisite Gates only by cached `gate_status` and `current_assessment_id`. They do not validate each prior assessment digest or rerun `content_current()` for prior input/evidence versions.
- Failure mode: obtain a synthetic-fixture G0 PASS using path-backed artifact/evidence, mutate the locked file directly in the repository, and assess G1.
- Reproduction: after the G0 document hash no longer matched, `G0.gate_status` remained `PASS`; `gate.assess(G1)` returned `candidate=PASS`, `missing=[]`.
- Impact: every later Gate can be decided on top of stale prerequisite evidence. Current-Gate freshness during `gate.decide` is insufficient because already-decided prerequisite Gates are trusted without freshness validation.
- Required remediation: before assessment/decision, recursively validate every prerequisite PASS decision against its immutable assessment inputs and current locked content. On drift, invalidate/supersede the affected Gate plus all downstream decisions and emit auditable events.
- Retry evidence: later-Gate assessment rejects a stale prerequisite. In addition, the read projection recalculates current freshness: a drifted Gate and every downstream cached PASS are returned with `gate_status=null`, `evaluation_state=NOT_EVALUATED`, and `freshness=STALE`; the historical result remains separately available as `recorded_gate_status` and in the immutable decision record. Report/release eligibility consumes the effective current projection and fails closed. The path-drift regression passes.

### P1 — Lifecycle evidence and source packages can expose secrets under common non-matching keys/files — RESOLVED / VERIFIED

- Affected requirements: `NFR-V3-004`; design section 10 privacy/package boundary.
- Evidence: `LifecycleBase.safe_json()` scans only dictionary key names. `lifecycle_snapshot()` returns full evidence locators. A secret embedded in `locator.inline_json.stdout` is therefore not inspected or redacted. Separately, `_source_manifest()` in `rd_platform/stack_harness.py` excludes only `.env*` and filenames containing `private_key`; it packages files such as `.npmrc` and `credentials.json` without content scanning.
- Reproduction A: a synthetic locator `{"stdout":"Authorization: Bearer SYNTHETIC_DO_NOT_USE_123"}` was accepted as `VERIFIED` and the exact token appeared in `/api/lifecycle` data.
- Reproduction B: a synthetic `.npmrc` containing `_authToken=...` and `credentials.json` were both present verbatim in the generated delivery ZIP.
- Impact: credentials can be persisted in SQLite, exposed to any local board reader, and shipped in deterministic delivery archives.
- Required remediation: use a shared recursive value-aware redactor/validator for lifecycle payloads and snapshot projections; return secret references/digests rather than inline raw output. Default-deny known credential stores (`.npmrc`, `.pypirc`, netrc, cloud credentials, key/cert stores, etc.) and add content/signature scanning before package creation. A filename denylist alone is not sufficient.
- Retry evidence: lifecycle writes now reject high-confidence secret-bearing string values and snapshot projection recursively redacts legacy values. The package scan excludes common credential stores and refuses high-confidence secret signatures without echoing the value. The final independent harness retry observed 24 PASS with one environment capability skip; synthetic Bearer content was rejected without the token in the error, and `.npmrc`/`credentials.json` were absent from the archive and listed as excluded.

### P2 — `work.claim` idempotent replay cannot recover from a lost response — RESOLVED / VERIFIED

- Affected requirements: `NFR-V3-003`; ADR-V3-005; design section 10 lease recovery.
- Evidence: `Runtime.execute()` hashes the request payload's lease token where present and strips the newly generated `lease_token` from the persisted `work.claim` result. Replaying the same request ID therefore returns only `lease_token_redacted=true` while the work order remains `CLAIMED`.
- Reproduction: first synthetic claim returned a token; an identical request-ID replay returned no token, and the lease remained claimed for the configured 3600 seconds.
- Impact: exactly the response-loss scenario that idempotency should recover leaves the host unable to heartbeat or finish. Work is unavailable until lease expiry/reap.
- Required remediation: implement a secure replay protocol (for example, caller-supplied proof/nonce with atomic token rotation) that never stores plaintext credentials but lets the same logical claimant recover ownership. Add concurrent same/different request-ID tests and response-loss recovery coverage.
- Retry evidence: same-request replay now atomically rotates a fresh random lease token, invalidates the prior token, extends the same current claim, and emits `work.lease_reissued`; no plaintext token is persisted. Focused response-loss coverage passes.

### P2 — Required lifecycle rollback and complete invalidation bookkeeping are missing — RESOLVED / VERIFIED

- Affected requirements: `REQ-V3-009`; design commands and section 8.
- Evidence: `lifecycle_control()` accepts only `pause|resume`, although the baselined contract requires `rollback` with an earlier `target_gate`. Artifact invalidation clears a current Gate but leaves the old assessment's `status` as `CURRENT`, rather than `SUPERSEDED`. Release invalidation checks only `artifact_refs + requirement_refs`, omitting `rollback_ref` and `known_issue_refs`.
- Failure mode: the requested lifecycle rollback command is rejected; consumers can see a historical assessment labelled current after invalidation; a released record can remain `RELEASED` after its locked rollback plan changes unless that document was redundantly placed in `artifact_refs`.
- Impact: required control behavior is absent and audit/readiness projections can remain materially stale.
- Required remediation: implement bounded earlier-Gate rollback with compensating work/events; explicitly supersede old assessments/decisions; include every locked release reference in the impact graph.
- Retry evidence: rollback now requires an earlier target Gate, a current CR and explicit affected references; it creates compensating work and retains decision history. Assessment supersession and release rollback/known-issue reference invalidation are included. A forward-target negative test passes.

### P2 — Formal report release recommendation ignores adverse release state — RESOLVED / VERIFIED

- Affected requirements: `REQ-V3-007`, `REQ-V3-008`.
- Evidence: `lifecycle_report()` in `rd_platform/lifecycle_reporting.py` derives `recommend_release` from tests, open defects, traceability, truncation, and G0–G10 statuses, but never evaluates `releases[*].status`.
- Failure mode: once G10 remains cached PASS, a later `DEPLOYMENT_FAILED`, `ROLLBACK_FAILED`, or `CHANGE_PENDING` release does not add a release reason and can still yield `recommend_release=true`.
- Impact: the formal projection can contradict the persisted release fact and mislead an operator.
- Required remediation: require an explicitly eligible current release revision/status, reject adverse/stale states, and bind the recommendation to that release ID/version and current G10 assessment.
- Retry evidence: the report now refuses recommendation when a release is absent or any release is not `READY|RELEASED`; focused absent/failed release tests pass. Cached Gate freshness remains separately open above.

### P2 — Package manifest can disagree with archive contents under concurrent source change — RESOLVED / VERIFIED

- Affected requirements: `NFR-V3-003`, `NFR-V3-005`; delivery manifest integrity in `REQ-V3-007`.
- Evidence: `_source_manifest()` hashes each file, then `package_app()` independently reads each source path again while writing ZIP entries.
- Failure mode: a file changes after the manifest hash pass but before the ZIP read.
- Reproduction: a deterministic synthetic mutation hook changed `source.txt` from `before` to `after` after `_source_manifest()` returned. Packaging returned PASS; the declared entry SHA-256 was `6db7...`, while the actual ZIP entry SHA-256 was `f395...` (`match=false`).
- Impact: the signed/delivered file list can claim hashes for bytes that are not in the archive. The archive-level hash only authenticates the inconsistent ZIP, not the per-file manifest claim.
- Required remediation: package an immutable one-read source snapshot, or rehash every ZIP entry and compare it with the declared list before atomic publication. Any drift must fail closed and clean temporary files. Add deterministic mutation and real concurrent-write tests.
- Retry evidence: scan, per-file digest and ZIP entry now use the same captured bytes; a pre-publication drift check and `finally` cleanup were added. The deterministic mutation regression now rejects packaging. Independent harness rerun: 24 PASS and one symlink capability test `NOT_EXECUTED`.

### P2 — Lifecycle collections are truncated but cannot be paged beyond the first window — RESOLVED / VERIFIED

- Affected requirements: `REQ-V3-008`, `NFR-V3-002`; design sections 4, 10 and 11.
- Evidence: `after_sequence` pages only lifecycle events. Every other collection is queried as ascending `rowid LIMIT ?`; no per-collection cursor is accepted by Runtime, CLI, or HTTP.
- Failure mode: after 500 work orders/artifacts/cases/executions/defects/releases, public readers can see `collections_truncated=true` but cannot retrieve any later row. The board shows the oldest window, not the newest blockers or owners.
- Impact: target-capacity projects cannot be fully inspected, reported, or operated through the supported read API. Honest truncation prevents a false PASS but does not satisfy pagination or explain current work.
- Required remediation: add stable per-collection keyset cursors (or bounded collection-specific endpoints), deterministic current-first/default ordering where appropriate, total counts, and no-gap/no-duplicate concurrent pagination tests. Preserve event sequence pagination independently.
- Retry evidence: a whitelisted lifecycle-collection reader now exposes project/collection-bound keyset cursors through Runtime, CLI and loopback GET. It strips internal digests and applies projection redaction. A 501-row synthetic fixture was retrieved in 73-row pages with no duplicate/omission; cross-project cursor and invalid collection/query negatives pass.

### P2 — Test model is not a source-bound, revisable versioned artifact — RESOLVED / VERIFIED

- Affected requirements: `REQ-V3-002`, `REQ-V3-005`, `REQ-V3-009`.
- Evidence: `test_model.create` writes `lc_test_models(version=1)` directly, does not require a corresponding `TEST_MODEL` artifact or source provenance, and has no revise/obsolete command. A second create with the same ID fails.
- Failure mode: after requirements/risks/test points change, the model cannot append version 2 and invalidate dependent current Test Cases through the supported command contract.
- Impact: cases remain locked to an unchangeable version-1 structure; source and change provenance required by the baselined design are absent.
- Required remediation: bind the structured model to a source-bearing TEST_MODEL artifact/version, add optimistic append-only revise/obsolete commands, and propagate review-required/stale state only to affected current cases/evidence/Gates.
- Retry evidence: create now requires provenance and atomically creates matching TEST_MODEL artifact/model version 1; revise appends both histories under an optimistic version and invalidates dependent cases; OBSOLETE models cannot create cases. Generic artifact create/revise rejects TEST_MODEL to prevent split-brain versions. Explicit legacy adoption marks original source `NOT_AVAILABLE`. Five model tests plus the combined lifecycle/model/query suite pass.

## Verification performed

- `\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests/runtime -p 'test_lifecycle*.py' -v`
  - Final result observed during review after all model/query edits settled: **40/40 PASS** in 7.326 seconds.
- `\.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_stack_harness tests.independent_v3.test_stack_harness_independent -v`
  - Final result observed during review: **24 PASS, 1 NOT_EXECUTED** in 2.639 seconds. The unexecuted case requires host symlink creation privilege; no PASS is claimed for that capability.
- `\.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_v3_adapters tests.runtime.test_lifecycle_reporting -v`
  - Final result observed during review: **8/8 PASS** in 1.093 seconds.
- Six isolated temporary-database/package reproductions were executed for approval spoofing, missing fix completion, stale prerequisite Gate evidence, secret-bearing snapshot/package, claim-response replay, and package hash/write TOCTOU. All data and identities were explicitly synthetic fixtures.
- HTTP review: V3 writes/command execution are not exposed by `HTTP_COMMANDS`; Host and Origin checks remain loopback-pinned. Board rendering uses `textContent`, so no DOM-XSS finding was identified in the reviewed adapter diff.
- Reporting review: the CLI's `limit=500` snapshot becomes `CONDITIONAL PASS` when collection truncation is declared; the separate collection API supplies bounded continuation. Absent/adverse releases and stale effective Gate decisions prevent release recommendation.

## Independent review conclusion

**APPROVED for the scoped V3 runtime/lifecycle/harness/adapter changes.** No unresolved P0/P1 was found after retry review. This conclusion does not convert template-mode validation into a project Gate PASS and does not assert human acceptance, production approval, release, deployment, or the Windows symlink capability that was not executable in this environment. Repository-wide regression, independent platform/application test conclusions, documentation governance, and final release/closure remain owned by their respective evidence records.
