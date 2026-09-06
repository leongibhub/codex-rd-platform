# V3 Completion Independent Review

- Review role: independent reviewer (`/root/v3_review_runtime`)
- Review state: **COMPLETE — TASK-V3-005/006/007/009/010 approved after independent retry where required**
- Initial review date: 2026-09-06
- Task: `TASK-V3-010`
- Frozen scope: `rd_platform/lifecycle_runner.py`, the `test-run` CLI integration, `LifecycleService.COMMANDS`, `test_execution_abort`, and `tests/runtime/test_lifecycle_runner.py`
- Additional completion scope: full lifecycle report/project export, capacity/soak interruption handling, cross-OS CI/native-driver changes, and the bilingual README executable-document contract. Python project G0–G8 review remains owned by a separate reviewer and is excluded here.
- Evidence boundary: all reproductions below used an isolated temporary database and synthetic fixture identities. They are contract tests only; they are not real project execution, human approval, Gate, release, deployment, or acceptance evidence.

## Findings

### P1 — Host interruption is recorded as a verified product failure and opens a defect — RESOLVED / VERIFIED

- Requirement: `REQ-V3-006`, `NFR-V3-003`, `NFR-V3-005`, `TASK-V3-010`.
- Evidence: `lifecycle_runner.run_case` catches `BaseException`, synthesizes a `FAIL` command, registers `status=VERIFIED` test-execution evidence, and calls `test_execution.finish`; the latter atomically opens a defect for every `FAIL`.
- Failure mode: patching the adapter to raise `KeyboardInterrupt` caused `run_case` to re-raise only after persisting a `FINISHED/FAIL` execution, one VERIFIED `test_execution` record with result `FAIL`, and an OPEN defect. No assertion result was produced.
- Impact: user cancellation or interpreter interruption is falsely represented as an executed product failure. This pollutes defect, trace, reporting, and Gate inputs with a claim stronger than the observable fact.
- Required remediation: abort the active execution as `BLOCKED`, with no test-execution result evidence and no defect, before re-raising the interruption. Preserve only an honest interruption/admission-failure fact.
- Retry evidence: `KeyboardInterrupt` now uses `test_execution.abort`, leaves the execution `BLOCKED`, creates no test-execution evidence or defect, and is re-raised. The focused regression passed independently.

### P1 — A cwd symlink race executes code outside the versioned repository boundary — RESOLVED / VERIFIED

- Requirement: `NFR-V3-004`, `REQ-V3-006`, `TASK-V3-010`, and ADR-V3-005's repository-controlled plan boundary.
- Evidence: `run_case` resolves and checks `cwd` before creating the execution, but `runner.run_command` later resolves that absolute pathname without receiving the expected project root. Final source/version validation happens only after the process exits.
- Failure mode: in a WSL/Linux synthetic fixture, the checked `work` directory and its versioned `check.py` were removed immediately before the actual adapter launch and replaced by a directory symlink to an external temporary directory containing another `check.py`. The external program executed and created an external marker. Final admission was correctly BLOCKED, but execution had already occurred. Observed: `LINUX_CWD_RACE BLOCKED True PASS None`.
- Impact: a filesystem race can make the trusted host execute unversioned, out-of-project code with the runner's privileges. Post-execution drift detection prevents false PASS evidence but cannot undo the security boundary violation.
- Required remediation: bind the launch-time working directory to the expected repository root using a non-following directory handle or equivalent containment primitive, and make the lower-level runner enforce the expected root. A pathname re-resolution plus post-execution reference check is insufficient. Add a deterministic Linux regression; record `NOT_EXECUTED` where the host cannot create the required symlink fixture.
- Retry evidence: the workspace directory is now pinned component-by-component. POSIX passes the directory descriptor through `/proc/self/fd`; Windows holds non-delete-sharing, non-reparse handles. Replaying the Linux directory replacement executed the pinned `OWNED` file, did not create the external marker, and correctly blocked admission because the repository pathname had drifted.

### P1 — Full reports preserve PASS after execution evidence is tampered or missing — RESOLVED / VERIFIED

- Requirement: `REQ-V3-004`, `REQ-V3-006`, `NFR-V3-005`, `TASK-V3-007`, and the project-export freshness contract.
- Evidence: `_capture_project` retrieves public evidence and execution rows, but `lifecycle_report` selects the stored execution result without revalidating its evidence references and locator digest. The export contract says external artifact-file freshness is checked during projection.
- Failure mode: a temporary real runner execution produced PASS and a hashed repository result file. After overwriting that file, `lifecycle_report_from_runtime` still reported conclusion PASS, PASS count 1 and the Case result PASS. Observed: `EVIDENCE_DRIFT_REPORT PASS PASS {'PASS': 1, 'FAIL': 0, 'BLOCKED': 0, 'NOT_EXECUTED': 0} PASS`.
- Impact: a formal report and exported test report can assert a current PASS when its only execution observation has been modified or deleted. Gate freshness may separately fail closed, but that does not correct the false test conclusion presented to report consumers.
- Required remediation: within the same read projection, revalidate every PASS/FAIL execution's evidence type, identity/result binding, current locator digest and locked subject versions. Downgrade an execution with missing/stale evidence to a non-PASS evidence state with an explicit reason. Cover modified and deleted path locators and keep report/export source reads non-mutating.
- Retry evidence: the projection now revalidates the current Case, tester identity, requirement/environment/evidence references, locator digest and exact execution binding in its consistent read transaction. Seventeen report/export unit checks and three independent CLI/export checks passed. Overwriting and then deleting a real runner observation produced current result `BLOCKED`, observed result `PASS`, freshness `STALE`, unchanged historical counts, `recommend_release=false`, and no source-database mutation. Review run `run-3a04b6b730d54b65b07248309e758eef` completed PASS.

### P2 — A DRAFT Test Case can produce VERIFIED PASS evidence — RESOLVED / VERIFIED

- Requirement: `REQ-V3-002`, `REQ-V3-004`, `REQ-V3-006`, `TASK-V3-010`.
- Evidence: `run_case` validates version, automation and subject state but not Case state; `test_execution.start/finish` reject `OBSOLETE` or `REVIEW_REQUIRED`, not `DRAFT`. The CLI describes `test-run` as executing a baselined Case.
- Failure mode: a current synthetic Case revised to `state=DRAFT` with argv automation returned execution `PASS` and persisted VERIFIED `test_execution` evidence.
- Impact: an unbaselined assertion definition can be treated as current PASS by reporting and G7 current-case checks, weakening version/status governance.
- Required remediation: require Case state `BASELINED` or `APPROVED` before launch and revalidate that state at evidence admission/finish time. Add negative coverage for DRAFT.
- Retry evidence: the runner rejects a DRAFT Case before invoking the command; the focused negative regression passed independently. A concurrent Case revision also produces BLOCKED with no result evidence or defect.

### P2 — Unadmitted command output is left and returned as if it were the admitted result path — RESOLVED / VERIFIED

- Requirement: `NFR-V3-003`, `NFR-V3-004`, `NFR-V3-005`, `TASK-V3-010` and the design file-durability rule.
- Evidence: result bytes are written directly with `open('xb')` before the final project/source/model/requirement checks. The exception path aborts the database execution but neither removes nor distinguishes the file. It also omits temporary-file write, flush/fsync and atomic rename.
- Failure mode: a synthetic CODE_CHANGE path was mutated while the patched command returned PASS. Admission correctly became `BLOCKED` and no test-execution evidence was registered, but `run_case` returned a non-null `result_path` and that file remained under `.rd-platform/test-runs/.../result.json`.
- Impact: callers can mistake an unadmitted observation for registered evidence; crashes or admission failures leave partial/orphan output, and a database record could be committed without the promised file durability boundary.
- Required remediation: durably write the raw observation through a confined temporary file plus flush/fsync and atomic rename; publish a separate admitted receipt or explicitly name the raw observation. On BLOCKED, do not return it as the admitted `result_path`; either safely clean it or return a clearly distinct unadmitted-observation field.
- Retry evidence: raw output is explicitly labelled `RAW_COMMAND_OBSERVATION`; `admission.json` records `ADMITTED` or `NOT_ADMITTED`; BLOCKED returns `result_path=None` and a distinct unadmitted locator. Publication is exclusive, flushed and pinned to the guarded directory.

### P2 — The executed command can redirect platform-owned result files outside the repository — RESOLVED / VERIFIED

- Requirement: `NFR-V3-004`, `TASK-V3-010`, and the explicit repository-root confinement rule.
- Evidence: the result directory is created and resolved before `run_command`; the platform later opens the result and admission files by pathname without a non-following directory handle.
- Failure mode: in a WSL/Linux synthetic fixture, the patched command removed its newly created `case-*` result directory and replaced it with a directory symlink to an external temporary directory, then returned PASS. The final evidence locator validation correctly blocked admission, but only after platform code had created both `result.json` and `admission.json` outside the project. Observed: `LINUX_SYMLINK_REPRO BLOCKED True True None`.
- Impact: fail-closed database admission does not prevent the platform's own file writes from escaping the configured repository. The returned unadmitted locator also appears repository-relative while resolving outside it.
- Required remediation: do not expose/create the random output directory until the contained process has ended, and publish through a directory handle or equivalent no-follow/open-at primitive that cannot be redirected by a symlink/junction race. A second path `resolve()` check alone does not close the race. Add a Linux-capable deterministic mutation regression; record `NOT_EXECUTED` on hosts without the required symlink capability.
- Retry evidence: the random output directory is no longer created until the process tree has ended and is opened through the pinned workspace guard. The Linux replay saw zero `case-*` directories during the command and published both result/receipt inside the repository after completion.

### P2 — CI validates the Java 8 sample with JDK 17 — RESOLVED / VERIFIED

- Requirement: `REQ-V3-010`, `TASK-V3-006`, and the DES-V3 Java self-test matrix.
- Evidence: `.github/workflows/platform-validation.yml` configures Temurin `java-version: '17'`; the baselined design and `java_booking/manifest.json` require compilation and execution with a real Java 8 JDK and explicitly prohibit silently raising the baseline to Java 17. The CI contract test does not assert the selected Java version.
- Failure mode: `javac` 17 is invoked without `--release 8`, so it emits Java 17 class files and all Java execution occurs on Java 17.
- Impact: a green matrix would not establish the declared Java 8 compiler/runtime compatibility and could miss accidental use of APIs or bytecode unavailable on Java 8.
- Required remediation: install and run a real JDK 8 in this job and assert the exact version in the CI contract test. If the platform intends to change the Java baseline, update the baselined design and manifest through controlled change rather than silently weakening the test.
- Retry evidence: the workflow now selects Temurin Java 8 and the contract test explicitly requires 8 and rejects 17. The three local CI contract tests and two native-driver integration checks passed in the fresh attempt. Independent review run `run-573ea0df5e8247aa91109d80a2791567` completed PASS; GitHub-hosted workflow execution remains `NOT_EXECUTED` until externally observed.

### P2 — Soak interruption during capacity setup has no terminal result — RESOLVED / VERIFIED

- Requirement: `NFR-V3-002`, `NFR-V3-003`, `TASK-V3-005`, and the benchmark's documented interruption contract.
- Evidence: `run_soak` invokes `run_capacity` before entering the `try/except KeyboardInterrupt` around its sampling loop. `run_capacity` catches `Exception`, not `KeyboardInterrupt`.
- Failure mode: injecting `KeyboardInterrupt` from `_seed` propagated out of `run_soak`. The output contained only a `perf-*-checkpoint.json`; there was no capacity terminal and no `soak-*-terminal.json` with `INTERRUPTED`. Observed: `SOAK_SETUP_INTERRUPT [...checkpoint.json] 0 0`.
- Impact: interrupting the potentially long full-profile setup leaves operators without the promised terminal state and makes an intentional cancellation indistinguishable from an abandoned/crashed soak preparation.
- Required remediation: establish the soak run/checkpoint before capacity setup and cover setup plus sampling with the same interruption terminal state machine. Emit `INTERRUPTED`, exit code 130, actual phase and any available capacity checkpoint reference. Add a setup-phase interruption regression; do not reuse the existing sampling-phase-only test as proof.
- Retry evidence: independent execution of the six unit and ten independent benchmark checks passed. A separate narrow replay injected `KeyboardInterrupt` from `_seed` and returned `INTERRUPTED`, exit code 130, phase `capacity_setup`, zero samples/resource samples, and matching `INTERRUPTED` checkpoint and terminal documents. Review run `run-bab9e70580c44cebbb25ad9d2a086a16` completed PASS. This does not claim that the already-running eight-hour soak has completed or that its process was hot-updated.

### P3 — README release-recommendation sentence is overly broad — RESOLVED / VERIFIED

- Evidence: `README.md` and `README.en.md` say that even a complete snapshot or all Cases passing “does not recommend release.” The implementation can set `recommend_release=true` when those facts and all other release, traceability, defect, and G0–G10 conditions are also satisfied.
- Impact: a reader could interpret the sentence as saying the command can never recommend release, instead of the intended fail-closed rule that those two facts alone are insufficient.
- Recommendation: add “这些事实本身” / “alone” in both languages. This wording precision issue does not weaken the documented safety boundary and did not block `TASK-V3-009` approval.
- Retry evidence: both language versions now say that these facts alone are insufficient and name the additional Gate, traceability, defect and release-evidence conditions. The one-line correction introduces no command or control-flow change.

## Checks that passed in the initial review

- The runner uses argv arrays and the existing `shell=False` process adapter.
- The HTTP command allowlist does not expose `test-run` or arbitrary argv execution.
- Project state, Case version, Test Model version, requirement references and CODE_CHANGE subjects are rechecked after the subprocess before PASS/FAIL admission.
- A project paused before launch does not start the subprocess; a project changed during execution cannot admit PASS.
- Timeout values reject booleans, non-finite values, non-positive values and values above the declared bound.
- NFR performance/stress/stability cases are rejected from this process-count adapter and require a specialized measured-result schema.

## Incremental README contract-test review

The final `tests/platform/test_readme_contract.py` revision was reviewed after the production-module freeze. The feature-branch/clone contract no longer reads the host checkout's `origin` URL or advertised remote refs, which can legitimately differ or be absent in a GitHub Actions pull-request or shallow checkout. Instead it validates the documented clone/fetch/switch strings and creates an isolated temporary Git source repository plus a depth-one `main` clone. All Git invocations use argv lists without a shell; repository paths come only from `TemporaryDirectory`, and all remote/ref assertions are scoped to that fixture. No README-derived text is executed, so the change introduces no command-injection path.

Independent command:

```text
.venv\Scripts\python.exe -X utf8 -m unittest tests.platform.test_readme_contract -v
```

Result: 4/4 PASS. The shallow clone reported `--is-shallow-repository=true`, its fixture origin differed from the documented GitHub URL, and the V3 feature ref was absent, demonstrating that the contract test no longer assumes the host checkout's remote state. No P0–P3 finding remains from this increment.

## Decision

- `TASK-V3-010`: **APPROVED** after independent Windows and Linux retry. Actual Runtime review run: `run-b81a6a129e2945eca9cb0791f13dc00e`; task is DONE.
- `TASK-V3-007`: initial review **FAIL** (`run-4160a04d738e4a3ea70f8d82f2201cf2`); fresh retry **APPROVED** in `run-3a04b6b730d54b65b07248309e758eef` after 20/20 report/export checks and the tamper/delete replay.
- `TASK-V3-006`: initial review **FAIL** (`run-24e52a4ded0d4a489866474e5e3a99bb`); fresh retry **APPROVED** in `run-573ea0df5e8247aa91109d80a2791567`. Local contracts validate the JDK 8 declaration; hosted CI execution is still `NOT_EXECUTED`.
- `TASK-V3-005`: initial review **FAIL** (`run-2a4ad4fbb5314d30804d536236eb05b0`); fresh retry **APPROVED** in `run-bab9e70580c44cebbb25ad9d2a086a16`.
- `TASK-V3-009`: **APPROVED** after 8/8 executable-document and adapter-boundary checks. Actual Runtime review run: `run-e8ff4871967445a9bc5c22e158b4136f`; the later one-line P3 wording correction was narrowly verified.

These module decisions are implementation review facts only. They are not lifecycle Gate decisions, human approval, release permission, deployment evidence, or acceptance.
