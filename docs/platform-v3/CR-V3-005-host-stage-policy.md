# CR-V3-005 — Host-enforced stage progression

Source: the user's explicit request to implement the remaining lifecycle vision, continued on 2026-09-07. Ordinary design/implementation choices are delegated to the engineering host. This authorization is not application acceptance, production deployment approval, or permission to fabricate Gate evidence.

## Reason and impact

Independent review found that `orchestrate-start`'s twelve dependency-linked work orders used only predecessor work `DONE` to permit the next claim. A model-generated DRAFT document could therefore unlock another stage's document generation without a current Gate decision. Formal deployment was separately protected, but the orchestration itself did not meet the user's quality-control goal. A further worker review found pause/resume could redispatch an unknown in-flight external action. That fix remains within REQ-V3-016; this change adds host progression policy as REQ-V3-021 / TASK-V3-021.

Impacted surfaces: bootstrap, work admission/lease completion, defect triage and repair scheduling, tests, status inspection, Skill/user guide and review. Existing generic lifecycle instances, all five sample applications and their immutable evidence must remain usable. No migration-1 rewrite or wholesale project regeneration is permitted.

## REQ-V3-021 acceptance criteria

1. New strict bootstrap projects identify their policy durably. Direct Runtime/CLI work claims and completion cannot bypass the same policy used by the worker service.
2. Work completion and Gate completion remain separate. Preparing DRAFT artifacts is useful work, but does not supply baseline, execution, independent review or human approval. The next normal stage requires the preceding current effective Gate PASS, using existing governance evidence and freshness checks rather than trusting model prose.
3. Claim, recovered claim and completion revalidate material prerequisites. A stale requirement/evidence or changed scope cannot admit results into a new baseline. A missing or failed prerequisite produces an explicit actionable reason; it never becomes an implicit PASS.
4. Use the existing Gate model's ordered criteria. Do not demand future code/tests at requirements discovery, or approval of an acceptance package before the package can be prepared. G9 approval controls progression to G10 through the existing Gate; signed acceptance and deployment evidence are never synthesized.
5. Real failed test executions preserve their original defect and cause bounded host-controlled triage/repair work. Classification is evidence-backed, not a blanket product-bug assumption. Fix, independent retest/regression and reviewer closure must use the existing evidence and quality chain, not just work `DONE`. Repeated failure must not create an unbounded queue or erase history.
6. Independent QA exercises negative bypass/restart/freshness/role cases and a positive bounded local application failure/fix/retest journey. Temporary synthetic governance fixtures are labelled as contract tests and never registered as real project acceptance.
7. Existing non-strict work contracts and the five application regressions remain valid. Tests/review run after implementation before the module is marked DONE. Full user vision acceptance is separate from this module's result.

## Engineering decision

Reuse the existing Runtime, SQLite transaction, versioned artifacts, governance evaluation, test executions and defect domain. Add a small host policy module and transactional hooks instead of a second scheduler state store or a parallel set of Gate definitions. Specialized agents retain development, independent testing and review responsibilities. The exact implementation and verification record are linked from [orchestration policy](orchestration-policy.md) and its independent report when present.

Status at change creation: implementation active; independent verification and review PENDING. Do not infer release readiness from this design record.
