# V3 Independent Platform Tests

- Test record: `TEST-V3-IND-001`
- Task: `TASK-V3-002` (Stack harness)
- Tester role: independent tester
- Date: 2026-09-06
- Repository state: V3 work is uncommitted; this record is independent test evidence only, not a Gate, release, deployment, or human-acceptance decision.

## Scope and risk model

This first pass covers the trusted-local harness and its public CLI commands
`stack-probe`, `stack-run`, and `stack-package`.  It is derived from
`REQ-V3-010`, `NFR-V3-004`, `DES-V3-001` section 10, and
`docs/platform-v3/stack-harness.md`, rather than implementation-test claims.

| Risk ID | Risk | Linked requirement | Independent test cases |
|---|---|---|---|
| RISK-V3-IND-001 | A manifest causes shell interpretation or arbitrary CLI state writes. | NFR-V3-004 | TC-V3-IND-201, TC-V3-IND-202 |
| RISK-V3-IND-002 | Missing tools/commands or a failed phase are presented as a pass. | REQ-V3-010 | TC-V3-IND-203, TC-V3-IND-204 |
| RISK-V3-IND-003 | IDs, roots, or placeholder-resolved workspace paths escape the selected project root. | NFR-V3-004 | TC-V3-IND-205, TC-V3-IND-206, TC-V3-IND-211 |
| RISK-V3-IND-004 | A symlink/junction places external content in source or delivery material. | NFR-V3-004 | TC-V3-IND-207 |
| RISK-V3-IND-005 | Delivery includes runtime/secret material, is nondeterministic, or overwrites a different existing delivery. | REQ-V3-010, NFR-V3-004 | TC-V3-IND-208, TC-V3-IND-209, TC-V3-IND-210 |

## Environment and execution evidence

| Field | Observed value |
|---|---|
| Environment | Windows PowerShell, repository `D:\\codex-rd-platform`, `.venv\\Scripts\\python.exe` |
| Test asset | `tests/independent_v3/test_stack_harness_independent.py` |
| Isolated data | Per-test `TemporaryDirectory(prefix="ind-v3-stack-")`; no project source or implementation file is modified. |
| Independent suite command | `& .venv\\Scripts\\python.exe -m unittest tests.independent_v3.test_stack_harness_independent -v` |
| Initial independent-suite result | Before the repair: 9 PASS, 1 FAIL (`TC-V3-IND-211`), 1 NOT EXECUTED. Its real result was registered after the repair was detected as `run-300f7ffe0c374c379894e8c53b87365b`; that record explicitly says it is late registration, not a current execution. |
| Retest developer unit-suite evidence | `run-67d0e0bbf37e4b4fbea8b4fe4326071d`; `& .venv\\Scripts\\python.exe -m unittest tests.runtime.test_stack_harness -v`; exit code `0`, 11/11 PASS. |
| Retest independent-suite evidence | `run-8584a3f6ce8944cfb9233910d8b5e693`; `& .venv\\Scripts\\python.exe -m unittest tests.independent_v3.test_stack_harness_independent -v`; exit code `0`, 10 PASS, 1 NOT EXECUTED. |

## Test cases and results

| Test case | Type | Objective / observable expected result | Actual result and evidence | Status | Defect |
|---|---|---|---|---|---|
| TC-V3-IND-201 | CLI / regression | `stack-probe` returns precisely the five contract tool records and does not create the supplied DB file. | CLI subprocess returned `0`; parsed keys were `python,node,java,javac,cxx`; isolated `unused.db` did not exist. | PASS | — |
| TC-V3-IND-202 | Integration / security | A semicolon-containing argv element is output as literal argument text and creates no sentinel file. | `stack-run` returned `0`; phase output contained literal `literal; echo injected`; sentinel was absent. | PASS | — |
| TC-V3-IND-203 | Negative / equivalence | Required missing tool is `NOT_AVAILABLE`; absent selected command is `NOT_EXECUTED`, neither PASS. | Controlled `node: None` returned `NOT_AVAILABLE`; no selected integration command returned `NOT_EXECUTED`. | PASS | — |
| TC-V3-IND-204 | Reliability / error priority | An execution failure overrides prior omitted phase and stops the following phase. | `build=NOT_EXECUTED`; unit exit code was `17`; top-level state was `FAIL`; integration evidence was absent (not run). | PASS | — |
| TC-V3-IND-205 | Negative / contract | CLI rejects a manifest outside declared root without traceback. | CLI returned nonzero; stderr contained `manifest escapes root`, not `Traceback`. | PASS | — |
| TC-V3-IND-206 | Boundary / security | Portable ID contract rejects traversal, separators, dot, whitespace and shell punctuation; duplicate phase selection rejects. | All five malicious IDs and duplicate `unit` selection raised controlled `ValueError`. | PASS | — |
| TC-V3-IND-207 | Security / compatibility | A source symlink must be rejected before source traversal. | Test setup could not create a symlink on this Windows environment: `OSError`. No claim about rejection behavior is made. | NOT EXECUTED | — |
| TC-V3-IND-208 | Packaging / security | Archive excludes `.env*`, private-key name, `.npmrc`, credential filename, `node_modules`, `build`, and `__pycache__`; includes normal source. | ZIP names contained `source.txt` and `manifest.json`; `.env.production`, `my_private_key.pem`, `.npmrc`, `credentials.json`, `id_rsa`, and runtime directories were absent. | PASS | — |
| TC-V3-IND-209 | Regression / deterministic build | Source timestamp-only change produces byte-identical archive and SHA-256. | Archive bytes and reported archive SHA-256 were equal before and after `os.utime`. | PASS | — |
| TC-V3-IND-210 | Reliability / recovery | A mismatching pre-existing archive is not overwritten. | After controlled archive tampering, package raised `ValueError: refusing to overwrite existing delivery archive`; tampered bytes remained unchanged. | PASS | — |
| TC-V3-IND-211 | Security / negative / regression | A `{root}` placeholder expanded with `..` outside root is rejected before execution. | Initial result: FAIL (`ValueError` not raised), preserved as late-registration evidence in `run-300f7ffe0c374c379894e8c53b87365b`. Retest: PASS in `run-8584a3f6ce8944cfb9233910d8b5e693`; the expected containment `ValueError` was raised and the outside target remained absent. | PASS | BUG-V3-001 (resolved) |
| TC-V3-IND-212 | Reliability / data integrity | Package refuses a source byte change after the file-hash pass but before ZIP entry read. | The initial integration record `run-0326efdffb0746598fc8da384f496afe` was **not valid product-failure evidence**: Windows path aliasing prevented its mock mutation from engaging. After normalizing both paths with `resolve()`, the controlled drift is exercised and `package_app` rejects it. Fresh independent integration evidence: `run-fcfa39a14b704595b5d4d01060b991d0`. | PASS | BUG-V3-003 (reclassified) |

## Defects

| Bug ID | Severity | Linked REQ / test | Observed defect | Status | Evidence |
|---|---|---|---|---|---|
| BUG-V3-001 | High | NFR-V3-004; TC-V3-IND-211 | The manifest argv element `{root}/../outside-target.txt` was placeholder-expanded and accepted by `run_matrix`, rather than being resolved and rejected as outside the selected root. This conflicted with the V3 workspace-path rule and stack-harness contract. | RESOLVED; independent review closure pending | Initial evidence: `run-300f7ffe0c374c379894e8c53b87365b`, `AssertionError: ValueError not raised`. Retest PASS: `run-8584a3f6ce8944cfb9233910d8b5e693`. |
| BUG-V3-003 | — | REQ-V3-010, NFR-V3-004; TC-V3-IND-212 | Initial independent report was a QA-fixture false positive: its mutation hook did not target the Windows-canonical path. This BUG ID is retained for traceability and must not be cited as a confirmed product defect from `run-0326...`. The corrected controlled-drift regression now passes. | RECLASSIFIED: INVALID TEST EVIDENCE | Corrected evidence: `run-fcfa39a14b704595b5d4d01060b991d0`; TC-V3-IND-212 PASS. |

## Conclusion

The harness has observed evidence for literal argv execution, controlled
tool/phase states, CLI root validation, ID validation, failure ordering,
source/delivery exclusions, deterministic ZIP bytes, overwrite protection, and
the repaired workspace-placeholder containment rule. `BUG-V3-001` is resolved
by independent retest but is not closed pending independent review. Symlink/
junction source traversal remains `NOT EXECUTED` because this test environment
cannot create its required fixture. Broader lifecycle and multistack
application validation is out of scope until its implementations are ready; no
result is inferred for those modules.

## Lifecycle independent integration (attempt 1)

Task `TASK-V3-001` is tested separately from the stack harness. The developer
unit suite was independently executed as runtime record
`run-2713940ee75841a5ae402600fd21fecb`: 17/17 PASS. It is implementation
regression evidence, not the black-box conclusion below.

| Test case | Requirements / risk | Actual observable result | Status | Defect |
|---|---|---|---|---|
| TC-V3-IND-301 | REQ-V3-002/003/009; project isolation and affected-only invalidation | Cross-project trace reference rejected; revising REQ-IND-001 marked its case `REVIEW_REQUIRED`; unrelated REQ-IND-002 link remained `VALID`. | PASS | — |
| TC-V3-IND-302 | REQ-V3-006; independent execution, resolution and closure | Developer executor rejected; incomplete regression set rejected; developer close rejected; separate reviewer close succeeded and original FAIL execution remained recorded. | PASS | — |
| TC-V3-IND-303 | REQ-V3-004; false Gate/approval evidence | Empty G0 assessed `BLOCKED`; unsupported PASS decision, generic human_approval, and model-provenance VERIFIED gate evidence were all rejected. | PASS | — |
| TC-V3-IND-304 | REQ-V3-009, NFR-V3-003; pause/recovery | Pause invalidated active lease; old heartbeat and finish rejected after resume; an ordinary re-claim is now rejected as an unknown external outcome, while this no-external-process fixture explicitly sets `safe_to_retry:true` for its fresh token; snapshot has no lease token. | PASS on current r6 fixture rerun; no production or external-process cancellation fact is implied. | — |
| TC-V3-IND-305 | NFR-V3-004; repository and secret boundaries | Plaintext password inline field and `../` content path were rejected and no artifacts registered. | PASS | — |
| TC-V3-IND-306 | REQ-V3-004; human approval provenance | Bare operator without a trusted approval provider was rejected. No human approval was created. | PASS | — |
| TC-V3-IND-307 | REQ-V3-006; defect fix quality boundary | Initial failure preserved in `run-e507a53d5fc147f0a45dddaacf53722f`. Final isolated regression creates a DRAFT-only task and confirms `defect.fix` rejects it; the full qualified four-phase fixture in TC-V3-IND-302 then completes only with independent identities. | PASS | BUG-V3-002 (resolved) |
| TC-V3-IND-308 | NFR-V3-004; persisted output secrecy | Credential-bearing V3 evidence registration was rejected or redacted; token was absent from lifecycle snapshot and events. | PASS | — |

The independent integration command was
`& .venv\\Scripts\\python.exe -m unittest tests.independent_v3.test_lifecycle_independent -v`.
Runtime record `run-e507a53d5fc147f0a45dddaacf53722f` preserves its actual
`7 PASS, 1 FAIL` result, including the TC-V3-IND-307 assertion
`ValueError not raised`.

Current r6 fixture history: root frozen-head independent run of 109 tests
first failed only TC-V3-IND-304 because its former ordinary re-claim predated
the new fail-closed `safe_to_retry` contract. The test now first asserts that
rejection and then makes the explicit no-external-process fixture decision;
the first failure is retained as a test-contract update, not a product BUG.

| Bug ID | Severity | Linked REQ / TC | Status | Evidence |
|---|---|---|---|---|
| BUG-V3-002 | High | REQ-V3-006; TC-V3-IND-307 | RESOLVED; closure not asserted by this test record | Initial evidence `run-e507a53d5fc147f0a45dddaacf53722f`; fresh core integration `run-b8f97a4050c54570b523c63565622cc2` PASS includes TC-V3-IND-307. |

## Public lifecycle collection query

`TASK-V3-004` query extension was independently exercised after its owner unit
run `run-257a64d606b044c59421ffd9dec4f5da` (5/5 PASS). Independent integration
record `run-eecacd5f4c04423e934bdcf42bac6c9f` is PASS (3/3):

| Test case | Requirement / risk | Observable result | Status |
|---|---|---|---|
| TC-V3-IND-401 | REQ-V3-008, NFR-V3-002; pagination completeness | Public Runtime API created and retrieved 501 artifacts over 73-item cursor pages in insertion order with no duplicate or omission. | PASS |
| TC-V3-IND-402 | NFR-V3-004; cursor isolation | A cursor from one project was rejected for another project and another collection; the other project returned only its own row. | PASS |
| TC-V3-IND-403 | NFR-V3-002/004; boundary and malformed input | Cursor over 1024 characters, malformed base64, `2^63`/negative rowids, boolean version, limit 501, and `projects` collection were rejected. | PASS |

## Test-model provenance and versioning

`TASK-V3-004` model extension has independent unit evidence
`run-81f20abe85c3403daec4ab151950ebad` (5/5 PASS) and independent
integration evidence `run-081038cf87724189a4efebfd3ce789eb` (3/3 PASS).

| Test case | Requirement / risk | Observable result | Status |
|---|---|---|---|
| TC-V3-IND-501 | REQ-V3-002/005; source provenance | Creation without registered source was rejected; a source-bound model created matching TEST_MODEL artifact/version history. | PASS |
| TC-V3-IND-502 | REQ-V3-009; material invalidation | Material revision without CR rejected; CR-backed v2 revision marked its v1 dependent case `REVIEW_REQUIRED`. | PASS |
| TC-V3-IND-503 | REQ-V3-002; legacy provenance | Legacy model adoption required explicit current source and produced version 2 with original source status `NOT_AVAILABLE`; it did not claim an original author. | PASS |
