# Gate Management

## Authority and modes

For an active project, `docs/08-project-management/gate-register.md` is the only authoritative source for G0–G11 Gate status. Lifecycle documents may define criteria and link evidence, but must not independently declare a Gate decision.

`templates/gate-register-template.md` is a platform template, not an active register and not project evidence. In `Lifecycle Mode: TEMPLATE`, no active project or active Gate Register is required. A platform validator result in template mode only confirms the template contract; it does not establish a project Gate decision.

An initiating project changes `lifecycle_mode` to `active`, creates the central register at the manifest path, and records each Gate only with actual baseline, evidence, and approval references. Missing evidence remains a recorded gap, not an inferred decision.

## State domains

Do not move values between state domains.

| Domain | Permitted values | Use |
|---|---|---|
| Gate Status | `PASS`, `FAIL`, `BLOCKED` | A decision recorded only in the active central Gate Register. |
| Evaluation State | `NOT_EVALUATED`, `IN_REVIEW`, `DECIDED` | Progress of the Gate evaluation. |
| Document State | `DRAFT`, `BASELINED`, `APPROVED`, `OBSOLETE` | Lifecycle-artifact control state; it is not a Gate outcome. |
| Evidence Status | `PENDING`, `NOT_AVAILABLE`, `NOT_EXECUTED`, `INFERRED`, `OBSERVED`, `VERIFIED` | Availability and strength of cited evidence. |
| Traceability Status | `COMPLETE`, `PARTIAL`, `GAP`, `NOT_APPLICABLE` | RTM linkage completeness. |
| Verification Result | `PASS`, `FAIL`, `BLOCKED`, `NOT_EXECUTED` | Test/verification result tied to actual execution evidence; it is not a Gate Status. |

## Active-register controls

The active register must contain exactly one record for every Gate G0–G11. Every record has the fields in the approved template. Gate Status accepts only the Gate Status domain. A `PASS` Gate row must cite non-placeholder Evidence IDs; if human approval is required, cite the real approval evidence rather than a name, signature placeholder, or inferred outcome.

Before a Gate evaluation, check required artifacts, consistency, RTM links, actual evidence, open risks, defects, and approved changes. Record missing information as `PENDING`, `NOT_AVAILABLE`, `NOT_EXECUTED`, or `BLOCKED` in its appropriate domain. Do not write an approval, signature, test result, deployment result, customer acceptance, or defect closure without evidence.
