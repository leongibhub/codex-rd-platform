# Host-enforced orchestration policy

Traceability: CR-V3-005, REQ-V3-021, TASK-V3-021. This is an implementation
policy for a future active project. It is not a Gate decision, approval,
deployment record, or claim that this template repository has completed a
project lifecycle.

## Purpose and activation

`orchestrate-start` persists `strict_policy: orchestration-v1` on each of its
twelve work orders. `work.create` inherits that durable marker for any later
work in the same project. The policy is checked inside the same SQLite
transaction as `work.claim`, lost-response claim recovery, lease heartbeat and
`work.finish`; it therefore cannot be bypassed by calling the raw Runtime CLI
instead of `worker-service` or a dashboard.

Existing projects and generic `work.create` callers without this bootstrap
marker retain their compatibility behavior. The marker is operational history,
not a prompt convention or a mutable model document.

## Stage admission

For strict work at Gate `Gn`, `G(n-1)` must have a current effective `PASS`:
the recorded assessment input digest is recomputed and all current evidence,
file hashes, artifact baselines and approval binding are re-evaluated. A stale
or missing predecessor rejects the claim with a stable policy reason. `G0` is
the deliberate exception because it creates candidate discovery material.

`DONE` means that one assigned activity has handed off candidate output. It
does not decide a Gate or unlock the next stage. Gate progression remains
`gate.assess` plus independent `gate.decide`, using the existing lifecycle
policy. G7 creates its test cases/executions, so it is not required to have a
complete test RTM before it starts; from G8 onward policy also checks that the
current RTM is complete. G10 can be claimed only after current G9 `PASS`; G9
contains the authenticated human-acceptance criterion. G11 similarly requires
G10 `PASS`. An Agent name, model text, a work completion, or a dashboard click
cannot substitute for a signed human approval.

The sole admission exception is repair work bound to an already persisted
`FAIL` test execution for its same defect. Requiring G7 `PASS` before claiming
that repair would make a G7 failure impossible to fix; the failed-execution
binding, bounded defect ID and stage-specific completion checks are the
narrower control.

Work outputs supplied through a strict `DONE` handoff must be versioned
`DRAFT` candidates. The policy rejects a baselined/approved artifact as an
Agent-completion authority. A trusted host may later baseline material through
the normal independent assessment/review process; the policy never does so.
Existing evidence provenance rules continue to reject model `VERIFIED` facts.

Before the next stage can claim, each predecessor-stage candidate consumed via
its declared dependency must have an explicit current `BASELINED` or
`APPROVED` revision with the identical content digest. That adopted current
version must be part of the predecessor Gate assessment input/evidence. The
claim stores these exact `dependency_input_refs`; later heartbeat/finish checks
reject changed adoption. Thus a reviewer cannot satisfy a Gate with an
unrelated document while a worker consumes another DRAFT, and an approved
content drift invalidates the Gate rather than silently changing context.

`TEST_CASE` is versioned structured lifecycle data rather than an artifact with
a content hash. Its adoption compares the complete declared semantic case
schema: identity, model and requirement scope, test point, type, priority and
risk, preconditions, data, ordered steps, expected result and automation. Only
lifecycle governance metadata (version, state, reason and creation time) may
differ. Changed steps, expected results or requirement references fail closed;
an unclassified new case field also fails closed until the policy schema is
explicitly updated.

## Failure and repair loop

For a strict project, a real `test_execution.finish(FAIL)` retains the normal
immutable failed execution and opens its normal `UNCLASSIFIED` defect. In that
same transaction it creates exactly one visible tester triage work order. The
system does not guess that every failed test is a product defect.

After evidence-led `defect.classify`, the stale triage work becomes
`REVIEW_REQUIRED` and emits the standard `work.invalidated` event (with
`external_process_cancelled:false`); a local worker uses that fact to cancel
only its own process tree. The old lease is rejected and a classified triage
cannot be retried into a second worker. One bounded chain is then created for
that defect:

```text
classified owner repair → independent tester retest → independent reviewer review
```

The owner comes from the existing category rules (for example product to
developer, requirement to requirement analyst, test-script to its permitted
owner). Each completion is additionally tied to the existing domain fact:
`defect.fix`, `defect.resolve`, and `defect.close` respectively. An arbitrary
code artifact, unrelated passing execution, or generic evidence cannot mark a
repair work order done. Reclassification is idempotent for the same defect;
new failed executions retain their own defect history instead of recursively
spawning unbounded retries.

Repair work must also return the exact proof persisted by that domain
transition: `defect.fix` evidence for the owner repair, the exact
`defect.resolve` passing execution references for retest, and `defect.close`
review evidence for closure. Omitted, substituted or extra references are
rejected even after the defect has moved to a later state. The common fix
contract is evidence, rather than a fictitious `CODE_CHANGE`, because a valid
repair owner can be a tester, architect or requirement analyst.

The existing defect API remains authoritative for regression scope, independent
identities and fresh review evidence. This policy creates observable handoffs;
it does not weaken defect closure rules or auto-close a defect.

Once the non-triage repair chain exists, its classification tuple (category,
severity, owner and rationale) is immutable. Repeating the exact same
classification is idempotent; an attempted material reclassification is
rejected before any chain or active owner lease changes. The host must first
dispose of the current chain through its normal evidence/change process rather
than silently assigning a claimed developer repair to a different owner.

The hard conservative automated-repair budget is three chains per exact test
case version and requirement scope. A fourth (or later) failure is still stored
as its own failed execution and open defect, but receives no new automated
triage/repair work. Its defect is marked `repair_disposition:PENDING_HUMAN`
and records `defect.repair_escalated`; a human must decide the next action.
Different case versions (including a distinct case against the same
requirement) have independent budgets. This is a cost/loop circuit breaker,
not a PASS, a defect closure, or a reason to discard evidence.

## Observable API

The normal public commands remain `orchestrate-start`, `work.claim`,
`work.heartbeat`, `work.finish`, `test_execution.finish`, and
`defect.classify`. The read-only `orchestrate-status --project-id …` command
reports stage-admission reasons using the same policy checks; it does not claim
worker availability, execute a model, or issue a Gate decision.

Developer contract tests use isolated temporary databases only:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_orchestration_policy -v
```

They prove raw Runtime bypass rejection, DRAFT-only candidate handoff, actual
failed-test defect/triage creation and the bounded role-separated repair chain.
Their evidence and fixture identities are synthetic; no test is a real human
approval, release, production deployment or user acceptance.
