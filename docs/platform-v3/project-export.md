# TASK-V3-007: complete reports and isolated project exports

Document State: DRAFT. Scope: REQ-V3-002/003/004/008 and NFR-V3-002/004/005. This is an implementation contract, not project approval or release evidence.

## Design and acceptance criteria

1. `lifecycle_report_from_runtime(runtime, project_id, page_size=200)` collects every public entity page inside one read transaction, including all traceability rows, and computes the latest execution per current Case version in linear time. More than 500 cases/executions must not truncate report totals or hide a late failure.
2. `export_project(runtime, project_id, destination, page_size=200)` captures the same consistent read view plus immutable version metadata and a source revision fingerprint. It does not mutate the source database, top-level template manifest, Gate Register or RTM.
3. The destination must be a new directory with an existing non-link parent. Existing files/directories, traversal components and link/junction ancestors are rejected. A manifest starts `IN_PROGRESS`; only a completely written, hashed bundle becomes `COMPLETE`. A failure records `FAILED` when possible; an interrupted `IN_PROGRESS` bundle is never complete. No preexisting destination is overwritten or removed.
4. Fixed output paths contain an active-project manifest, Gate state/evaluation register, RTM, artifact/case/release version and evidence indexes, formal JSON/Markdown test report and summary. Undefined Gate decisions remain null/UNDECIDED, stale decisions retain history and never become PASS. The export is a read-only projection of the source revision, not a new authoritative decision.
5. Export only metadata/indexes; never copy source files, inline artifact bodies, raw execution output, command arguments or credentials. Known secret fields/text and URL credentials/query strings are omitted/redacted. All destination file names are fixed or selected from a code-owned collection whitelist, never constructed from artifact IDs.
6. Regression tests cover >500 entities, latest failure beyond the first page, source database digest unchanged, stale/undecided Gates, path rejection, secret exclusion, version history, no overwrite and interrupted/failed export markers. Developer results and independent QA/review are recorded separately.

Integration: callers import the two functions above; CLI wiring belongs to the primary coordinator. No new HTTP writes or approval adapter are introduced.

## API and bundle contract

```python
from rd_platform.lifecycle_reporting import lifecycle_report_from_runtime
from rd_platform.lifecycle_export import export_project

report = lifecycle_report_from_runtime(runtime, project_id, page_size=200)
manifest = export_project(runtime, project_id, destination, page_size=200)
```

`page_size` must be an integer from 1 through 500; it limits each database query, not the completed report. The report's `complete_snapshot` is true only after all collection pages have been captured. The pure `lifecycle_report(snapshot)` API remains available for caller-supplied views and still flags truncated inputs as incomplete.

The returned export manifest contains `destination`, `status`, per-file SHA-256/byte counts, collection counts and `source_revision`. The same manifest, without the local destination field, is at `export-manifest.json`. Consumers must require `COMPLETE` and verify the listed file hashes. A directory's mere existence, or an active exported manifest, is not completion or acceptance. Failed output is retained for diagnosis and must not be reused as a destination; this API never deletes it. Marker replacement is atomic; the whole directory is not an atomic rename. Failure while recording failure may leave the prior `IN_PROGRESS` marker, which is explicitly incomplete.

The bundle contains a README summary, active read-only platform manifest, Gate register and decision/assessment JSON, RTM and full typed/versioned trace edges, current artifact/evidence indexes, immutable artifact/Case/release version indexes, and declared-scope JSON/Markdown test reports. Missing decisions are JSON null / displayed UNDECIDED, separate from Evaluation State. Stale recorded decisions remain visible only as history. A test-scope PASS does not imply a release recommendation or execution of unrepresented test types.

The source revision uses `lifecycle-project-records-v1`: SHA-256 over project collections, immutable version records, project events and lifecycle migration records in deterministic database order. Event count and final event sequence support audit correlation. It is a project-record fingerprint, not a Git revision or a hash of the entire SQLite file. SQLite records are captured in one read transaction; external artifact-file freshness is checked during projection and those files are not locked or archived. A subsequent filesystem change requires a fresh report/export. No reproducible source-code archive or immutable backup of external evidence is claimed.

## Developer verification

2026-09-06, local Windows Python environment:

- `.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests/runtime -p test_lifecycle_export.py -v`: 9 tests PASS (6.342 seconds).
- `.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests/runtime -p test_lifecycle_reporting.py -v`: 5 tests PASS (0.032 seconds).

Tests include 507 current Cases and executions with a failure after row 500; concurrent writer isolation; immutable version history; stale/undecided Gates; source database digest and template preservation; secret/raw-body exclusion; Markdown escaping; no overwrite; path/link rejection; and a simulated write failure with a FAILED manifest. Fixtures and Gate decisions belong to temporary test databases and are not approvals or acceptance for this project. Independent QA/review remains a separate quality stage owned by the coordinator.

Collections are retrieved in bounded pages, but the completed metadata view and rendered bundle are assembled in memory. The 507-row regression proves nontruncation, not million-row capacity. Link/junction ancestors are rejected and generated paths are fixed; the local destination parent must remain trusted during export (no hostile concurrent filesystem replacement). Known credential fields/text and URL user information/query strings are removed, but arbitrary confidential prose must not be placed in public metadata in the first place. Source bodies and raw process output are intentionally excluded rather than classified as safe documentation.

## Review repair: current execution evidence

The initial developer results above preceded an independent P1 finding: a recorded PASS survived modification or removal of its hashed result file in the formal report/export. That review failure is retained in Runtime history; the repair runs under implementation `run-80db6eae6886406cb0609a54e309a34c`, attempt 2.

Complete Runtime reports now reapply `LifecycleBase.evidence_refs` verification inside the read transaction. For every observed PASS/FAIL, the projection checks the current baselined/approved Case version, executor role, requirement references, qualified environment evidence, and qualified tester execution evidence. Evidence must be nonempty, current rather than superseded, VERIFIED with the correct kind/role, and content-hash valid; linked subjects must still be current. Execution identity, observer identity, recorded result, exact Case version and observation time are checked using the same bindings enforced at admission. Missing, changed or malformed evidence projects to `result: BLOCKED`, `freshness: STALE`, with `freshness_reason`. No historical database result is rewritten.

`observed_result` and `historical_execution_counts` preserve the original observation. Current totals and release recommendations use the revalidated projection. JSON and Markdown distinguish these fields explicitly. The pure `lifecycle_report(snapshot)` helper only summarizes a caller-supplied view: absent a verified capture its rows state `freshness: NOT_CHECKED`; it does not access files or independently authenticate those inputs. Formal CLI reporting and export use `lifecycle_report_from_runtime` / `export_project`, not that helper alone. Filesystem evidence can change after capture, so freshness remains a time-of-read assessment, not a permanent guarantee.

Repair developer checks, 2026-09-06:

- Export/report integration suite: 12 tests PASS, 23.987 seconds. Real local subprocess evidence was overwritten and then deleted; both report and export became BLOCKED while preserving historical PASS and unchanged database contents. Negative bindings include missing/superseded evidence, role, actor, status, kind, result, execution identity, Case version, missing Case binding, old observation time and wrong hash.
- Pure report aggregation suite: 5 tests PASS, 0.032 seconds.
- Scale fixtures now contain explicit synthetic requirement/environment/typed evidence bindings and hashes, not evidence-free PASS records. The 507-Case test still verifies 506 current PASS and the late current FAIL. These fixtures are never real project test evidence or human acceptance.

Independent re-test/re-review is pending separately; developer checks do not supersede the recorded review failure.
