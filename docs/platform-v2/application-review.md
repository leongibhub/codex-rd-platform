# V2 Application Runtime Independent Review

- Review owner: `/root/v2_review_application` (`reviewer`)
- Scope: `rd_platform/runtime.py`, `store.py`, `discovery.py`, `reporting.py`,
  `web.py`, `cli.py`, `static/`, their focused tests, and
  `examples/task_board` against `examples/task_board/SPEC.md`.
- Excluded implementation review: process-tree runner and local-config rewrite;
  those have a separate independent reviewer.
- Design basis: `DES-V2-001`, `REQ-V2-001` through `REQ-V2-009`, and
  `DES-EXAMPLE-001` / `REQ-EXAMPLE-001` through `REQ-EXAMPLE-003`.
- Document State: `DRAFT`
- Evidence Status: `OBSERVED`
- Review method: source/diff inspection plus bounded temporary-database and
  loopback-HTTP reproductions. No product source, real runtime database, external
  system, or full test suite was modified or executed by this reviewer.

## Initial review checkpoint: FAIL

The initial review used `.rd-platform/reviews/platform.diff`, SHA-256
`72972C22FF59FEBBE7CBC24942DEE2FD32DFCDA89FBA28E3156842B7B592874F`.
The saved review diff exactly matched the selected working-tree paths at that
checkpoint, and `git diff --check` had no whitespace errors.

### Platform local foundation: FAIL / do not approve

| Severity | Requirement | Initial observed failure |
| --- | --- | --- |
| P1 | `REQ-V2-005` | `reassign` permanently bound an implementation-role Agent; after implementation PASS, the required tester could not start unit and no control action could clear the assignment. |
| P1 | `REQ-V2-002`, `REQ-V2-005` | Skipping/rejecting a DONE upstream did not invalidate transitive dependents. A downstream active review could still finish DONE while its dependency was SKIPPED. |
| P1 | `REQ-V2-004`, `REQ-V2-008` | A task skipped after unit/integration PASS was still reported as a PASS task and made the module execution status PASS, although release remained `DO_NOT_RELEASE`. |
| P1 | `REQ-V2-004`, `REQ-V2-008` | Four phases accepted PASS with explicit contradictory evidence (`timed_out: true`, `exit_code: null`, evidence `status: FAIL`) and produced `DONE` with four checks. |
| P2 | `REQ-V2-009` | A deeply nested JSON body below 64 KiB raised uncaught `RecursionError` and disconnected the HTTP client instead of returning a controlled client error. |
| P2 | `REQ-V2-007` | `freeze` accepted a forged question model and exported fixed requirements with empty confirmations; a string `facts` value became a character list. |
| P3 | performance / concurrency | `snapshot` used `BEGIN IMMEDIATE`, unnecessarily serializing reads with writers. |

After the first remediation, the evidence check still used `start_error` while
the real runner/CLI contract uses `launch_error`; a runner-shaped launch failure
with `exit_code: 0` was accepted as PASS. This residual P1 kept the review at
FAIL until the actual field was covered.

A subsequent boundary pass also found that Python's permissive JSON handling
accepted and stored `NaN` in task inputs, after which HTTP snapshots contained
non-standard JSON that browser `response.json()` cannot parse. This was P2 under
`REQ-V2-006` / `REQ-V2-009`.

The final public-Runtime boundary pass found one further P2: a directly supplied
5,000-level mapping raised `RecursionError`, rather than the frozen public
contract's `ValueError`, although the transaction remained unwritten. This
remained open until Runtime normalized deep JSON encoding/decoding failures.

### Example task-board application: FAIL

| Severity | Requirement | Initial observed failure |
| --- | --- | --- |
| P2 | `REQ-EXAMPLE-002` | A 5,000-level JSON body below 16 KiB raised uncaught `RecursionError` and disconnected instead of returning 400. |

The first parser fix covered recursion but not Python 3.11+'s ordinary
`ValueError` for a JSON integer longer than the configured integer conversion
limit. A 5,000-digit title value therefore still disconnected the client; the
example remained FAIL until this second boundary was covered.

The already observed developer `8/8` and independent black-box `6/6` results
were valid for their executed cases, but did not cover these failures and did
not override the source-review conclusion.

## Remediation re-review checkpoint: 2026-09-06 16:35 +08:00

### Platform local foundation: PASS for this scoped independent review

The reviewer replayed every original failure against the remediated working
tree using new temporary SQLite databases and real loopback HTTP requests:

- phase-scoped reassignment allowed the tester to start unit (`ACTIVE`, `unit`)
  after the assigned developer completed implementation;
- skipping a DONE upstream changed it to `SKIPPED`, advanced the active
  downstream to a new revision with zero current checks, and rejected the late
  review finish;
- a skipped task with historical unit/integration PASS records reported task
  `SKIPPED`, execution `NOT_EXECUTED`, and zero passed tasks;
- contradictory timeout/status evidence and runner-shaped nonempty
  `launch_error` evidence were rejected before advancing the task;
- non-finite nested task input was rejected before write, with the persisted
  task count unchanged;
- a direct 5,000-level Runtime mapping was normalized to `ValueError`, and the
  following snapshot remained empty;
- the forged discovery model/string-facts reproduction was rejected;
- deep nesting, a 5,000-digit integer, and explicit `NaN` returned controlled
  HTTP 400 responses; no invalid JSON record was persisted;
- `snapshot` now opens a deferred read transaction rather than an immediate
  write transaction.

Focused implementation evidence reported by the responsible developers at this
checkpoint was runtime `18` tests, discovery/reporting `12` tests, and web/CLI
`12` tests passing. These counts are recorded as developer evidence; this
reviewer did not relabel them as independent executions or rerun the suites.

No unresolved P0, P1, P2, or P3 finding remains in the reviewed platform
application scope. This PASS is review evidence only. It is not a project Gate,
release recommendation, production-security certification, deployment result,
human acceptance, full SDLC completion, or evidence of a background model
daemon. The report continues to distinguish module quality from absent release
evidence.

### Example task-board application: PASS for SPEC/source review

The reviewer replayed all discovered parser boundaries through the real HTTP
server. Deep nesting, a 5,000-digit integer, and explicit `NaN`, each below the
16 KiB limit, returned controlled 400 responses rather than disconnecting; the
normal visible task state was not changed. The implementation still clearly
states that `X-Role` is a trusted test-role header, not authentication.

The responsible developer reported `11` focused HTTP tests passing after the
second parser fix. Independent QA then recorded current attempt-3 unit `11/11`
and SPEC-derived black-box integration `8/8` PASS with real runner evidence;
the task reached `READY`, `next_phase: review`, and `3/4` checks without a
reviewer result. The QA report now consistently scopes its current conclusion
to `TC-EXAMPLE-901` through `TC-EXAMPLE-908`.

No unresolved P0, P1, P2, or P3 source/spec finding remains, and the example
receives a scoped independent-review PASS. This is not release, deployment,
real-login, security-certification, or human-acceptance evidence.

## Review-result ownership

The initial runtime review phase was pre-registered as
`run-fc00f8f2e6264772b175b1fc9877e464`. Runtime Run completion is performed by
the parent orchestrator from this independent conclusion; the developer and
this reviewer did not directly write or self-sign the real project database.
Any later review Run must be recorded only after its required independent test
phases have actually reached review. At the final checkpoint, sample review Run
`run-a9d2ae752d8549efbad49e49febe60f6` was ACTIVE and is parent-owned for
completion from this review verdict.
