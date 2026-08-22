# Requirement Traceability Matrix

`Lifecycle Mode: TEMPLATE`. This empty matrix is a platform contract, not a record of product requirements, coverage, test execution, releases, or approvals. Add exactly one row for each real `REQ-xxx` or `NFR-xxx` only after an active project establishes those facts.

`Trace ID` must be a unique `TRACE-xxx` record identifier. Active linkage fields use typed references: `BG-xxx`, `PRD-xxx`, `REQ-xxx`/`NFR-xxx`, `DES-xxx`/`ADR-xxx`, `TASK-xxx`, `CR-xxx`, commit SHA or `MR-xxx`, `TC-xxx`, `EVD-xxx`, `BUG-xxx`, and `REL-xxx`. A typed cell is a complete set of comma-, semicolon-, or `<br>`-separated references; every token must exactly match that column's allowed type, with no prose or placeholder fragment. Active `EVD-xxx` references must be declared in a repository document other than the active RTM or Gate Register.

| Trace ID | Scope Status | BG | PRD | REQ/NFR | Acceptance Criteria | DES/ADR | TASK | CR | Commit/MR | TC | Test Execution/Evidence | Verification Result | BUG | Defect Disposition | REL | Traceability Status | Evidence Status | Last Verified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Coverage Rules

- Every `IN_SCOPE` REQ/NFR must link to measurable acceptance criteria.
- Every implemented REQ/NFR must link to relevant design/ADR, task, and commit/MR evidence.
- `PASS` or a populated `REL-xxx` requires `TC`, actual `EVD-xxx` test-execution evidence, an explicit result other than `NOT_EXECUTED`, the applicable `REL-xxx`, and `Evidence Status: VERIFIED`. `FAIL` and `BLOCKED` likewise require `TC`, actual `EVD-xxx`, and `Evidence Status: VERIFIED`, but do not require a release. `PENDING`, `NOT_AVAILABLE`, `NOT_EXECUTED`, and `INFERRED` evidence must not support a `PASS` verification result.
- A closed BUG requires the corrective commit/MR, `TC`, regression evidence, `Verification Result: PASS`, `Evidence Status: VERIFIED`, and `Last Verified`; do not infer closure from a code change.
- An approved CR requires a real `EVD-xxx` approval reference in `Test Execution/Evidence`, `Evidence Status: VERIFIED`, and traceability to every affected REQ/NFR, DES/ADR, TASK, and TC.
- `Traceability Status: COMPLETE` requires BG, PRD, REQ/NFR, acceptance criteria, DES/ADR, TASK, Commit/MR, and TC, plus every applicable evidence and release rule.
- Traceability and evidence states use the state domains in [Gate Management](../08-project-management/gate-management.md). Missing links remain explicit; implementation alone never establishes verification or a release decision.
