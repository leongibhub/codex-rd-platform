# V3 independent completion QA record

## TASK-V3-005 — lifecycle benchmark

Test record: `TEST-V3-IND-BENCH-001`  
Requirements: `NFR-V3-002` → `DES-V3-001` → `TASK-V3-005`  
Tester: `/root/v3_qa_platform` (independent tester)  
Execution date: 2026-09-06  
Environment: local Windows workspace; `.venv\Scripts\python.exe`; isolated
temporary directories only. No network, package installation, project runtime
database, full-profile run, or eight-hour soak was used.

### Risk model and scope

| Risk | Independent check | Evidence boundary |
| --- | --- | --- |
| Claimed full seed does not match 100 projects / 100,000 versions / 1,000,000 events | Inspect profile contract, then run an exact-count small SQLite seed and query tables directly. | The full workload itself is `NOT EXECUTED` by this record. |
| Existing state is replaced | Create a sentinel `state.db`, invoke capacity, and compare its bytes after refusal. | Test-local sentinel only. |
| Disk or time limit can produce a false PASS | Run a one-byte disk-budget seed and a zero-second time-budget seed; inspect terminal JSON. | These prove abort semantics, not the 1.5 GiB/600 s full-budget outcome. |
| Exception or Ctrl+C is recorded as success | Inject a seed exception and a post-capacity soak `KeyboardInterrupt`; inspect terminal status and exit code. | Fault injection is test-only. |
| Short soak/percentile evidence is ambiguous | Run an actual one-second small soak; check checkpoint, samples, nearest-rank percentiles, and terminal. | Not evidence of long-term stability. |
| Supported command line differs from callable API | Run the smoke capacity command through Python subprocess and parse its emitted JSON. | Isolated temporary output only. |

### Executed cases

Command executed after the test fixture was corrected for its own Windows
SQLite connection cleanup:

```text
& .venv\Scripts\python.exe -m unittest tests.independent_v3.test_benchmark_independent -v
```

Observable result: `Ran 7 tests in 4.328s` and `OK`.

| ID | Objective and exact observable checks | Actual result | Status |
| --- | --- | --- | --- |
| TC-V3-IND-601 | Confirm `full` contract is `(100, 100000, 1000000, 100)`; run a 3-project/31-version/79-event/4-sample capacity fixture; direct SQLite counts must be 3 `projects`, 3 `lc_projects`, 36 gates, 31 artifacts, 31 artifact versions, and 79 events. | Profile values and all direct counts matched; capacity terminal was `PASS`; both public-read percentile sets had four samples and no errors. | PASS |
| TC-V3-IND-602 | Refuse a directory that already holds `state.db` and preserve sentinel bytes. | `FileExistsError` was raised; sentinel bytes were unchanged. | PASS |
| TC-V3-IND-603 | Force a one-byte disk budget and a zero-second elapsed-time budget; neither terminal may be `PASS`. | Both isolated runs produced terminal `ABORTED`, exit code 2, respectively `disk budget exceeded` and `time budget exceeded`. | PASS |
| TC-V3-IND-604 | Inject seed exception; inject `KeyboardInterrupt` after soak capacity succeeds. | Capacity terminal was `FAIL`, exit code 1; soak terminal was `INTERRUPTED`, exit code 130 and checkpoint exists. Neither was `PASS`. | PASS |
| TC-V3-IND-605 | Execute one-second soak on a 1-project/9-version/17-event fixture; verify checkpoint, terminal, samples, and monotonic p50 ≤ p95 ≤ p99. | Terminal `PASS`; elapsed time was at least one second; checkpoint and percentile/sample assertions passed. | PASS |
| TC-V3-IND-606 | Verify nearest-rank percentile calculation on known samples and reject duration 0, duration 259201, boolean duration, interval 0, and boolean interval before database activity. | Deterministic p50/p95/p99 values matched; all invalid inputs raised `ValueError`. | PASS |
| TC-V3-IND-607 | Execute `scripts/benchmark_lifecycle.py capacity --profile smoke` via subprocess and parse stdout/terminal JSON. | Exit code 0; emitted `PASS`, with 2 projects, 200 versions, and 1,000 events; terminal file exists. | PASS |

The only pre-correction run ended with an unclosed **test fixture** SQLite
connection preventing temporary-directory cleanup on Windows. It was repaired
in `tests/independent_v3/test_benchmark_independent.py` before the recorded
execution above; it is not a product failure and is not logged as a defect.

### Coverage and result boundary

The script's seed design was inspected: it creates each configured project and
its 12 gates, batch-inserts configured artifact/version rows and event rows,
and invokes public `Runtime.lifecycle_collection()` and
`Runtime.lifecycle_snapshot()` for timed reads. The executed small fixtures
independently confirmed the corresponding database count behavior.

This is a passing **independent small-fixture and safety-semantic** result for
the seven cases above. It does not establish any of the following:

| Item | Status | Reason |
| --- | --- | --- |
| Full 100-project / 100,000-version / 1,000,000-event capacity result | NOT EXECUTED | A separate 600-second full run was already in progress; this tester did not duplicate it and has no terminal result to assess. |
| 1.5 GiB / 600-second full-budget compliance | NOT EXECUTED | Requires completed full workload evidence. |
| Eight-hour soak stability | NOT EXECUTED | Not launched; no long-duration result is asserted. |
| Runtime quality-phase record for TASK-V3-005 | NOT EXECUTED | Implementation run was still open when this investigation ran; lifecycle registration/retest is deferred to the task controller. |
| Release, Gate, deployment, or human acceptance | NOT EXECUTED | No such authority or evidence was provided. |

### Defects

No product defect was observed in this bounded independent execution. This is
not a claim that the unexecuted full capacity or long soak is defect-free.

## Follow-up budget and soak-evidence review

This follow-up began after the initial seven-case result, in response to the
need for whole-run deadline enforcement and evidence suitable to assess a
future long soak. It is recorded separately because production changes were
being made concurrently; no result below is silently folded into the earlier
seven-case PASS.

| ID | Requirement / risk | Actual evidence | Status |
| --- | --- | --- | --- |
| TC-V3-IND-608 | `NFR-V3-002`; the documented 600-second capacity cap must include public `Runtime` read measurement, not just synthetic seed batches. | Initial controlled-clock RED: both seed guards were within 600 seconds, then a 601-second total result was returned as `PASS`. Current source subsequently added a read deadline. After adapting the test fixture to invoke that deadline, the command below returned `ABORTED` with exit code 2 and reason containing `time budget exceeded during public read measurement`. | PASS on current source; pre-repair RED retained as `BUG-V3-004` history. |
| TC-V3-IND-609 | Before an eight-hour soak can support stability assessment, each persisted checkpoint must retain RSS, CPU, and DB-size samples; the terminal must state the public read-only workload. | Initial RED raised `KeyError: 'workload_scope'`. After repair, a one-second actual soak checkpoint contained aligned `resource_samples` with `rss_bytes`, `cpu_seconds`, and `database_bytes`; result scope declared exactly `Runtime.lifecycle_collection` and `Runtime.lifecycle_snapshot`, and explicitly excluded write throughput, full-system stability, and write consistency. | PASS on current source; BUG-V3-005 history retained. |

Commands and observable outputs:

```text
& .venv\Scripts\python.exe -m unittest -v tests.independent_v3.test_benchmark_independent.IndependentBenchmarkTests.test_tc_v3_ind_608_total_capacity_deadline_covers_public_read_measurement
# Ran 1 test in 0.190s; OK

& .venv\Scripts\python.exe -m unittest -v tests.independent_v3.test_benchmark_independent.IndependentBenchmarkTests.test_tc_v3_ind_608_total_capacity_deadline_covers_public_read_measurement tests.independent_v3.test_benchmark_independent.IndependentBenchmarkTests.test_tc_v3_ind_609_soak_persists_resource_trends_and_read_workload_scope
# Ran 2 tests in 1.352s; FAILED (TC608 assertion text was then narrowed to semantic containment;
# TC609 remains a real missing-key failure.)
```

### Defect records

| ID | Severity | Requirement | Reproduction | State |
| --- | --- | --- | --- | --- |
| BUG-V3-004 | High | NFR-V3-002 / 600-second capacity safety limit | Original TC-V3-IND-608 controlled-clock run returned `PASS` after read work took total elapsed past the limit because read measurement had no deadline. | Remediated in concurrently edited source; independent current-source TC608 retest PASS. Closure is not asserted until the whole independent suite is green. |
| BUG-V3-005 | Medium | Pre-long-soak evidence contract supplied by task controller; NFR-V3-002 capacity/stability evidence | Initial TC-V3-IND-609 had checkpoint resource trend but no `workload_scope`, so a reviewer could not bind samples to declared read-only operations. | Remediated in current source and independently retested PASS; no formal project defect-closure approval is asserted here. |

### Final current-source independent rerun

After the workload-scope repair, the entire owned benchmark suite was rerun:

```text
& .venv\Scripts\python.exe -m unittest tests.independent_v3.test_benchmark_independent -v
# Ran 9 tests in 4.993s; OK

& .venv\Scripts\python.exe -m unittest tests.runtime.test_benchmark_lifecycle -v
# Ran 5 tests in 1.895s; OK
```

The observed scope is deliberately bounded to local SQLite public read probes:
`Runtime.lifecycle_collection` and `Runtime.lifecycle_snapshot`. Its persisted
exclusions say it is not Runtime write-throughput, full-system stability, or
write-consistency testing. The passing one-second soak establishes checkpoint
schema behavior only. It does not make an eight-hour soak executed or make any
full-system stability claim.

## TASK-V3-008 — actual Python CLI lifecycle execution

Test record: `TEST-V3-PLC-001`  
Requirements under execution: `REQ-MATRIX-PY-01` through `REQ-MATRIX-PY-04`,
and `NFR-MATRIX-PY-001` through `NFR-MATRIX-PY-003`  
Actual tester: `/root/v3_qa_platform`  
Harness developer: `/root/v3_skill_forward`  
Isolated run: `python-lifecycle-f4a27c6be645459d8a7ee45cfb0ea167` / project
`project-337a2843b20e407981e60c2a28c605e4`

After reading the BASELINED requirements, execution plan, current-source
architecture observation, and independent-review contract, this tester
confirmed the catalog defines 37 distinct cases: 22 negative, 10 boundary, 2
functional, 2 data-consistency, and 1 compatibility. Requirements occur in
case references as follows: REQ-01 8, REQ-02 4, REQ-03 15, REQ-04 23,
NFR-001 3, NFR-002 9, and NFR-003 2. These are coverage references, not a
review conclusion.

The actual command issued under the tester's host assignment was:

```text
& .venv\Scripts\python.exe -B -X utf8 scripts/validate_python_lifecycle.py execute --output-dir .rd-platform/python-lifecycle/actual --actor /root/v3_qa_platform --host-assignment 'Codex root assigned v3_qa_platform independent TASK-V3-008 testing in current turn'
```

The outer command observer did not return a reliable captured stdout payload,
so no console text is reconstructed here. Instead, the post-execution
read-only Runtime snapshot and generated files supplied the following
observable evidence:

| Check | Actual observation | Status |
| --- | --- | --- |
| Per-case execution result | 37 result JSON files; Runtime shows 37 `FINISHED` executions and report counts `PASS:37, FAIL:0, BLOCKED:0, NOT_EXECUTED:0`. | PASS |
| Actual tester identity | `run.json` records `/root/v3_qa_platform`; each test-execution evidence record is registered by the tester role. | PASS |
| Execution traceability | 38 test-execution evidence items exist (37 case records plus current conclusion); both `test-report.json` and path-backed Markdown report hashes are present. | PASS |
| Requirements/test boundary | Cases use synthetic CSV data and compare input/source hashes; the app source is not modified by this test execution. | PASS for the recorded local execution only |
| Review and Gates | `review_evidence:0`; G0–G11 have null Gate statuses in the actual snapshot. | PENDING / NOT EXECUTED |
| Human acceptance, release, deployment | No provider, acceptance decision, release, or deployment fact was created. | NOT EXECUTED |

### Traceability defect and versioned correction

`BUG-V3-006` — The generated `DOC-PLC-TEST-REPORT` artifact was created with
`source.actor=/root/v3_skill_forward` (the prepare developer) even though the
actual test evidence is correctly recorded by `/root/v3_qa_platform`. This
misattributes the authored execution report and weakens role traceability.

After the harness owner declared the correction frozen at source SHA-256
`78aea9fc1ba77ee061b8f36314f27dfb8dd4a44637562a2b7cb90f5ef06b93d7`, the
actual report author made a non-material, versioned correction in the same
isolated Runtime:

- `DOC-PLC-TEST-REPORT` was revised from v1 to v2 with
  `source.actor=/root/v3_qa_platform` and an explicit correction reason.
- `EVD-PLC-G7-DOC-V2` superseded `EVD-PLC-G7-DOC`, and
  `EVD-PLC-CONCLUSION-V2` superseded `EVD-PLC-CONCLUSION`; both point to the
  unchanged report hash, current report v2, and the original 37 execution IDs.
- No test execution, review evidence, human-approval fact, or Gate decision
  was created by this correction.

The original execute command was then run through its documented recovery
path. Its observable JSON reported 37 PASS, zero FAIL/BLOCKED/NOT_EXECUTED,
complete traceability for all seven REQ/NFR artifacts, null G0–G11 statuses,
`recommend_release:false`, review `PENDING`, and human acceptance `PENDING`.
Independent post-recovery inspection confirmed exactly 37 finished executions
(zero new executions), report v2 owned by the tester, both v2 evidence records
properly superseding v1 and referring to report v2, `CODE-PLC-HARNESS` v2 in
the regenerated promotion-plan, zero review evidence, and no non-null Gate.

`BUG-V3-006` is therefore remediated and independently retested for the
versioned report-provenance scope. This is not a review conclusion, Gate
decision, human acceptance, release recommendation, or assertion that all
project lifecycle Gates pass.

## Registered independent quality runs

The following are real host Runtime quality records, registered by
`/root/v3_qa_platform` through `rd_platform run`. They establish only their
listed unit/integration checks; review remains a separate reviewer activity.

| Task | Phase / Runtime run | Actual command result | Task state after integration |
| --- | --- | --- | --- |
| TASK-V3-005 `task-dca65f42ba9c4f8abc1fe48e93fa5390` | Unit `run-b8da47cbbe944950b6f3e1b8b2d2c309` | `tests.runtime.test_benchmark_lifecycle`: 5 tests, exit 0, 2.469151 s. | READY / `review` |
| TASK-V3-005 `task-dca65f42ba9c4f8abc1fe48e93fa5390` | Integration `run-4836938350404dad9b78524eccb14c43` | `tests.independent_v3.test_benchmark_independent`: 9 tests, exit 0, 6.731462 s. | READY / `review` |
| TASK-V3-006 `task-d90b3e88be7d40a6a1c9f077c6205df0` | Unit `run-d28f1432a68c4663a190fb8aff2079c4` | `tests.platform.test_ci_contract`: 3 tests, exit 0, 0.5942 s. | READY / `review` |
| TASK-V3-006 `task-d90b3e88be7d40a6a1c9f077c6205df0` | Integration `run-ed60741900cc42a5a1764d8b6c9e986b` | Confirmed module `tests.independent_multistack.test_cpp_inventory_blackbox`: 2 public-CLI checks through the documented WSL executable, exit 0, 6.804079 s. | READY / `review` |
| TASK-V3-008 `task-a21f85188f1b439096f4351c54cea0cf` | Unit `run-26aa937db13442a1a6b67e7c8027993f` | `tests.runtime.test_python_lifecycle_selftest`: 9 tests, exit 0, 30.803238 s. | READY / `review` |
| TASK-V3-008 `task-a21f85188f1b439096f4351c54cea0cf` | Integration `run-0e542d0f60b541f299dc989929fd070e` | Actual `validate_python_lifecycle.py execute` recovery path: exit 0, 2.402961 s; 37 existing execution records remain finished PASS and no new case execution was created. | READY / `review` |

The Python integration result is **recovery/idempotency evidence only**. It
does not recast the previously recorded 37 actual CLI executions as a new run,
and it creates no reviewer decision, Gate decision, human approval, release,
or deployment evidence.

### Benchmark setup-interrupt regression

After the benchmark owner declared the setup-interrupt repair frozen at
`scripts/benchmark_lifecycle.py` SHA-256
`98404402ec84fe1ed96b84bdde3883e1f348f8c5ae599f23f695836b1a3579b`, the
independent suite added `TC-V3-IND-610`.

| ID | Risk and procedure | Actual result | Status |
| --- | --- | --- | --- |
| TC-V3-IND-610 | Patch only test-local `_seed` to raise `KeyboardInterrupt` during `run_soak` capacity setup. Assert the soak's own checkpoint and terminal, exit code 130, `capacity_setup` phase, and zero collection/snapshot/resource samples. | The new test and all existing independent benchmark tests passed: `Ran 10 tests in 5.042s; OK`. | PASS |

`BUG-V3-007` records the setup-interrupt terminal gap reported before this
frozen repair: a Ctrl+C during soak capacity setup could escape without a soak
`INTERRUPTED` terminal. The original RED was not executed by this tester; this
record preserves that provenance boundary. TC-V3-IND-610 independently verifies
the repaired behavior without interacting with the live eight-hour soak.

The post-repair task retry was separately registered through the host Runtime,
not inferred from the earlier direct test invocation: TASK-V3-005 attempt 2
unit `run-3b05cbcaa1ec41d5b6cbc6e822f8ba9c` ran the six-test developer suite
with exit 0 in 2.275277 seconds; integration
`run-2074846c1a424321bcca9f02437c1805` ran the ten-test independent suite
with exit 0 in 5.503288 seconds. The task is `READY` for review. The existing
long soak uses an older script SHA and was neither restarted nor represented as
post-repair evidence.

### TASK-V3-006 attempt 2 quality rerun

The earlier review failure remains historical. After its actual JDK-8 repair
and implementation retry, this tester registered a fresh quality chain:

| Phase / Runtime run | Actual result | State |
| --- | --- | --- |
| Unit `run-a2ed2a69d261431cbdbc3530fac50e55` | `tests.platform.test_ci_contract`: 3 tests, exit 0, 0.433374 s. | PASS |
| Integration `run-1002dbbc14284494b29f29f75a6ca839` | `tests.independent_multistack.test_cpp_inventory_blackbox`: 2 documented WSL public-CLI checks, exit 0, 8.830313 s. | PASS |

Task `task-d90b3e88be7d40a6a1c9f077c6205df0` is `READY` for an independent
reviewer. No review conclusion is asserted by this testing record.

### Python lifecycle recovery regression

TASK-V3-008 attempt 2 recorded a real unit PASS followed by a recovery
integration failure:

| Phase / Runtime run | Actual result | Status |
| --- | --- | --- |
| Unit `run-19e190fa00dc4c2ca1a44d0ddf8eb47b` | `tests.runtime.test_python_lifecycle_selftest`: 13 tests, exit 0, 45.267084 s. | PASS |
| Integration `run-d3ece0fdd6604ca584805c2c23a3cdd9` | Actual existing-run `execute` recovery: exit 2, `persisted execution report no longer matches current case/execution versions or results`. | FAIL |

`BUG-V3-008` — Backward-compatible recovery is broken for the already
persisted real report. Read-only comparison found that all 37 historical
`case_results` lack newly derived report fields `observed_result`, `freshness`,
and `freshness_reason`; the current reporter adds those fields. The 37 case
IDs, case versions, results, evidence references, aggregate counts, and report
hash are otherwise unchanged. This is a harness/report canonicalization defect,
not a test-case failure. The report and results must remain immutable; do not
rerun the 37 cases merely to regenerate a newer report. At this point the task
returned to implementation, and review/Gate work remains pending.

After the v4 compatibility repair was frozen at
`74e7e8e45eff52ec959dbb5924da39501bb1f717fe76f7067a7c290934753f8a`, TASK-V3-008
attempt 3 was separately registered through the host Runtime:

| Phase / Runtime run | Actual result | Status |
| --- | --- | --- |
| Unit `run-59085c8d26fa44c09cb1dbc83004b744` | `tests.runtime.test_python_lifecycle_selftest`: 16 tests, exit 0, 49.922070 s. The suite includes tampered-report rejection and legacy-report recovery contracts. | PASS |
| Integration `run-648d2d22ec674c44b8d7b1382bb6ec3c` | Same tester/actor recovery command against the actual isolated run: exit 0, 5.982997 s. | PASS |

The current official `lifecycle_report_from_runtime` projection was then read
without mutation: all 37 results and observed results are `PASS`, and all 37
freshness values are `CURRENT`. The database still contains exactly 37 unique,
finished executions; report v2 remains tester-sourced with its original
`3e7335ef45355cf1408319f59b4b66c640f85f54f66100f2ee5a9389c87e243d` hash;
`CODE-PLC-HARNESS` is v4. `BUG-V3-008` is independently retested as remediated
for this recovery compatibility scope. It does not become a review conclusion:
no review evidence or Gate decision existed at this handoff, and the task is
only `READY` for the authorized reviewer.

### Read-only verification of the developer full-run artifact

This tester did **not** execute a second full workload. At the task controller's
request, the existing developer artifact was read without mutation:

```text
Get-FileHash .rd-platform/benchmark-full-20260906-1/perf-29cadeac913240c4a8a2868c36a9788e-terminal.json -Algorithm SHA256
# BC88515F34D61FE7EF2B48B19DBA0ADE626233DD53B5021A8ED37FD2ABFF19D3
```

The parsed terminal reported `PASS`, 129.71990860020742 seconds,
294,764,544 database bytes, exact seeded values 100/100,000/1,000,000, 100
samples for each public read, and no read errors. A separate read-only SQLite
count query reported 100 `projects`, 100 `lc_projects`, 1,200 gates, 100,000
artifacts, 100,000 artifact versions, and 1,000,000 events. This verifies the
stored developer evidence's internal count consistency; it is not an
independent repeat of the full benchmark, an eight-hour soak result, a Gate,
release, deployment, or human acceptance.
