# TASK-V2-003 Discovery and Reporting Implementation

- Task: `TASK-V2-003`
- Requirements: `REQ-V2-007`, `REQ-V2-008`
- Design: `DES-V2-001`
- Change: `CR-V2-001`
- Implementation status: COMPLETE (local unit verification only)
- Independent test/review: `NOT_EXECUTED`
- Human approval/acceptance: `PENDING`

## Scope and interfaces

`rd_platform.discovery` provides pure, standard-library-only functions:

```python
discover(idea: str) -> dict
freeze(model: Mapping[str, Any], answers: Mapping[str, str]) -> dict
```

`discover` rejects an empty idea and produces an explainable baseline discovery
model: source facts, explicitly labelled inferences, unknowns, candidate
business flow, permission/data/NFR concerns, and at most three required
questions. Each question includes a suggested answer and the reason it is
important. `discovery_mode` is `baseline_no_model`; this is basic discovery
assistance, not a claim that a background model understood the request. The
`host_enhancement` field records that a trusted host may later enrich the
model.

`freeze` requires a nonblank response for each required question. It exports a
`DRAFT` SRS and `PARTIAL` RTM suitable for a subsequent requirements/design
workflow. Neither function invents a human approval: `approval_status` remains
`NOT_APPROVED`.

The frozen input is now schema-validated as `discovery-v1`: it requires the
three canonical required question IDs (`Q-001` through `Q-003`), well-typed
nonempty question fields, nonempty answers, a nonempty idea, structured facts
and inferences, and a string-list of unknowns. A caller cannot substitute a
custom question such as `Q-X`, omit canonical confirmations, or pass a string
as facts and receive forged empty requirement confirmations.

`rd_platform.reporting` provides:

```python
report(snapshot: Mapping[str, Any]) -> dict
build_report = report
```

The report reads the frozen `Runtime.snapshot` dictionaries and returns a
`MODULE_QUALITY` report: module-test counts, a deliberately partial
requirement-to-task test trace, defect counts, and a non-release recommendation.
For each task it considers only runs whose `revision` and `attempt` exactly
equal the task's current revision and attempt. Earlier retry evidence remains
audit history but cannot make the current retry pass. Both `unit` and
`integration` records with evidence are required for a task test PASS.

`module_test_coverage` is the explicit unit-quality metric. Its `total` uses
the labelled `task` denominator; `executed` includes only PASS or FAIL task
test outcomes, never BLOCKED or SKIPPED. It records check-level unit and
integration counts and a `pass_rate` with explicit numerator/denominator;
the rate is `null` when nothing executed. `test_execution` remains a compatible
alias of the same module-quality data, while `module_quality.status` is the
module test verdict.

## Result rules

- Missing current test records yield `NOT_EXECUTED`; skipped records cannot
  yield PASS.
- A current `FAIL` is reported as `FAIL`, even if another required phase is
  missing; `BLOCKED` remains distinct.
- Current Runtime task state takes precedence over historical module runs:
  `SKIPPED` remains `SKIPPED`, `REJECTED`/`PAUSED` are `BLOCKED`, and `FAILED`
  is `FAIL`. Thus a later skip cannot inherit a prior unit/integration PASS.
- The runtime snapshot has no design, code-change, or release mapping fields,
  so every trace row is `PARTIAL`; passing module tests cannot make the RTM
  `COMPLETE`.
- Only a `CLOSED` defect is closed. `RESOLVED` remains open for this report.
- A unit/integration PASS without the runtime's final `DONE` state is also
  `DO_NOT_RELEASE`; this preserves the required independent review boundary.
- This report never returns `RELEASE_CANDIDATE`. It returns `DO_NOT_RELEASE`
  for observed module-quality failures, unresolved defects, or known
  incomplete tasks; otherwise it returns `NO_RELEASE_EVIDENCE`. Both
  `human_acceptance` and `deployment` remain `NOT_EXECUTED`.

## Test-first evidence

The task tests were written before the module implementation. Before
implementation, the specified command failed with `ModuleNotFoundError: No
module named 'rd_platform'`, which is the observed initial RED state. The
report-scope corrections were also written as RED tests first: they failed for
missing `module_quality`, counting BLOCKED/SKIPPED as executed, and treating
`RESOLVED` as closed. After the scoped implementation:

```text
python -m unittest tests.runtime.test_discovery tests.runtime.test_reporting -v

Ran 10 tests in 0.132s
OK
```

The tests cover empty ideas, the fact/inference boundary, three-question cap,
missing freeze answers, DRAFT/PARTIAL export without approval, no execution
not passing, failure and open-defect release blocking, stale retry evidence not
passing a new attempt, BLOCKED/SKIPPED accounting, and an actual temporary
`Runtime.snapshot` completing the four-phase quality flow without fabricating
release evidence or complete traceability.

## Reviewer correction evidence

The reviewer findings were converted to two additional RED tests before code
changes. The first used a real temporary `Runtime`, recorded implementation,
unit, and integration PASS, then skipped the task; the old report incorrectly
returned task and test execution PASS. The second passed a custom `Q-X` model
and string facts to `freeze`; the old code accepted it. After state precedence
and schema validation were added:

```text
python -m unittest tests.runtime.test_discovery tests.runtime.test_reporting -v

Ran 12 tests in 0.227s
OK
```

## Traceability

| Requirement | Implementation | Unit evidence |
| --- | --- | --- |
| REQ-V2-007 | `rd_platform/discovery.py` | `tests/runtime/test_discovery.py` |
| REQ-V2-008 | `rd_platform/reporting.py` | `tests/runtime/test_reporting.py` |

No project Gate decision or final system acceptance is asserted by this task.
