# Requirement Traceability Matrix

`Lifecycle Mode: TEMPLATE`. This empty matrix is a platform contract, not a record of product requirements, coverage, test execution, releases, or approvals. Add exactly one row for each real `REQ-xxx` or `NFR-xxx` only after an active project establishes those facts.

| Trace ID | Scope Status | BG | PRD | REQ/NFR | Acceptance Criteria | DES/ADR | TASK | CR | Commit/MR | TC | Test Execution/Evidence | Verification Result | BUG | Defect Disposition | REL | Traceability Status | Evidence Status | Last Verified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Coverage Rules

- Every `IN_SCOPE` REQ/NFR must link to measurable acceptance criteria.
- Every implemented REQ/NFR must link to relevant design/ADR, task, and commit/MR evidence.
- A verified or released REQ/NFR requires actual test-execution evidence, a verification result, and the applicable `REL-xxx`; `PENDING`, `NOT_AVAILABLE`, `NOT_EXECUTED`, and `INFERRED` evidence must not support a `PASS` verification result.
- A closed BUG requires the corrective commit/MR, regression evidence, and an evidence-backed closure basis; do not infer closure from a code change.
- An approved CR requires real approval evidence and traceability to every affected REQ/NFR, DES/ADR, TASK, and TC.
- Traceability and evidence states use the state domains in [Gate Management](../08-project-management/gate-management.md). Missing links remain explicit; implementation alone never establishes verification or a release decision.
