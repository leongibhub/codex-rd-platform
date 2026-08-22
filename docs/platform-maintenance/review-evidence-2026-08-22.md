# 2026-08-22 平台维护独立审查证据

- Record Type: PLATFORM_MAINTENANCE
- Evidence ID: EVD-T8-REVIEW-20260822
- Linked BUG / Task: [BUG-001](BUG-001-platform-self-check-false-positive.md) / [TASK-001](TASK-001-platform-readiness-repair.md)
- Design / plan: [approved design](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md), [implementation plan](../superpowers/plans/2026-08-22-platform-readiness-repair.md)

## Initial Independent Review

- Review target: `2d3ae0a90fdf73d6e2f0494d7c02f18c5b0c2543`.
- Findings: 0 P0, 0 P1, 5 P2, 5 P3.
- Conclusion: `NEEDS_FIXES`. This review is not a PASS conclusion.
- Evidence source: [SDD progress record](../../.superpowers/sdd/2026-08-22-platform-readiness-repair/progress.md) (Task 8 review-loop entries) and the retained independent tester evidence in [EVD-T8-TEST-20260822](test-evidence-2026-08-22.md).

## P2 Remediation and Directed Re-review

| Finding | Remediation commit / evidence | Directed re-review disposition |
|---|---|---|
| Manifest/runtime duplicate identifiers could false-green via set comparison. | `ce9ca0e`; [five P2 contracts](evidence/2026-08-22/15-five-p2-directed-contracts-final.txt) | CLOSED in directed re-review. |
| Canonical MCP containment did not prove correct-layout junction rejection. | `ce9ca0e`; [junction probe](evidence/2026-08-22/13-correct-layout-junction-probe.txt) | CLOSED in directed re-review. |
| `enabled` and timeout fields lacked exact type/value invariants. | `ce9ca0e`; [five P2 contracts](evidence/2026-08-22/15-five-p2-directed-contracts-final.txt) | CLOSED in directed re-review. |
| Gate decision status/evidence semantics allowed contradictory or unevidenced states. | `ce9ca0e`; [five P2 contracts](evidence/2026-08-22/15-five-p2-directed-contracts-final.txt) | CLOSED in directed re-review. |
| `setup.ps1` did not restore the caller cwd in all paths. | `ce9ca0e`; [five P2 contracts](evidence/2026-08-22/15-five-p2-directed-contracts-final.txt), [same-process setup](evidence/2026-08-22/19-same-process-clone-setup-final.txt) | CLOSED in directed re-review. |

- Directed re-review target: `ce9ca0e2162b6612deb03209de1130330ae4c14b`.
- Directed re-review result: 0 P0, 0 P1, 0 P2; a command-junction fixture P3 remained.
- The independent retest evidence is recorded separately in [EVD-T8-TEST-20260822](test-evidence-2026-08-22.md). This document does not issue a project Gate, release or acceptance decision.

## P3 and Historical Diagnostic Disposition

These are review findings, not entries in a product risk register. None is marked CLOSED.

| Review Finding ID | Item | Evidence / rationale | Next action | Status |
|---|---|---|---|---|
| RF-T8-001 | `requests` dependency bounds are not validated by the validator. | Deferred P3 in the Task 8 review loop; current evidence validates the declared MCP constraint and installed dependency consistency, not validator enforcement of `requests` bounds. | Evaluate a scoped hardening change and regression test before relying on validator enforcement. | OPEN_P3 |
| RF-T8-002 | Unicode suffix after placeholder may false-reject. | Progress record identifies `PENDING状态` boundary behavior as a deferred P3. | Define the intended Unicode token-boundary rule and add a regression test if behavior is changed. | OPEN_P3 |
| RF-T8-003 | `runtime_executed` may become true after import before callable precision is established. | Deferred P3 in review loop; full/static outputs alone do not prove a narrower internal state transition. | Decide status semantics and add targeted callable-resolution coverage if required. | OPEN_P3 |
| RF-T8-004 | Mutation helper writes before `try`. | Deferred P3 in Task 8 review loop; not addressed by the P2 remediation. | Review failure-path rollback/cleanup behavior in a separate scoped change. | OPEN_P3 |
| RF-T8-005 | Command-junction fixture layout differs from the actual configured `Scripts\\python.exe` layout. | Directed fixture used a different shape; independent [correct-layout probe](evidence/2026-08-22/13-correct-layout-junction-probe.txt) still observed public rejection. | Align the regression fixture to the exact existing-target layout. | OPEN_P3 |
| RF-T8-006 | Historical CLIXML diagnostic root cause. | Legacy capture logs contain Error-stream deserialization diagnostics. Available artifacts do not prove the wrapper implementation or exclusive cause; fresh direct same-process evidence has no such diagnostic. | Preserve logs and investigate only with a reproducible capture wrapper; causal conclusion remains pending. | PENDING |

## Review Boundary

The review did not execute or infer Redmine, RAGFlow or GitLab external calls. Codex restart and current-session MCP visibility remain `NOT_EXECUTED` and are governed by [TC-002](TC-002-codex-restart-validation.md).
