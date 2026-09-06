# V3 five-application independent code review

- Reviewer: `/root/v3_review_apps` (`reviewer`, independent of implementation and QA)
- Date: 2026-09-06
- Scope: only `examples/multistack/{cpp_inventory,python_expenses,web_notes,java_booking,wechat_expenses}`, their app specifications, the shared multistack acceptance baseline, manifests, and `.rd-platform/reviews/v3-apps.diff`
- Lifecycle boundary: the repository is in `template` mode. This is G8 review evidence, not a project Gate decision, release decision, native WeChat validation, or human acceptance.
- Method: source/specification inspection plus targeted reproductions only. Developer and Tester run outputs remain separate evidence and are not promoted by this review.

## Review conclusion

**NOT APPROVED.** One unresolved P1 data-integrity defect exists in the WeChat application. Five P2 requirement/reviewability defects also remain. No P0 finding was identified.

| Application | Specification and quality verdict | Key evidence |
| --- | --- | --- |
| C++ inventory | **CONFORMANT in reviewed scope.** Invalid/corrupt input is fully loaded and validated before mutation; insufficient deduction does not call `save`; committed writes use a temporary sibling and rename. Build/test outputs are directed under `.rd-platform/build/cpp_inventory`. The documented single-writer and WSL-only native boundary is material but explicit. | `inventory.cpp:24-44,51-88,90-124`; `main.cpp:22-49`; `verify.py:13-16,33-69` |
| Python CSV expenses | **NOT CONFORMANT.** Decimal accumulation can silently round valid, unbounded inputs (REV-V3-APP-002), and the manifest unit phase can still write bytecode into the source application rather than `{build}` (REV-V3-APP-003). Ordinary invalid CSV/CLI cases otherwise return nonzero without success JSON. | `expense_analyzer.py:44-55,58-86,95-106`; `manifest.json:8-26` |
| Web notes | **NOT CONFORMANT.** `localStorage` operation failures are caught by the domain adapter, but failure while obtaining `window.localStorage` crashes module startup (REV-V3-APP-004). The XSS-sensitive render path is sound: user note content is assigned only through `textContent`, and no `innerHTML` sink exists. | `notes.js:27-42`; `app.js:11,19-28,38-63` |
| Java booking | **NOT CONFORMANT to its portable manifest acceptance.** Functional single-writer persistence, malformed-data rejection, overlap rejection, and adjacency are correctly implemented, but the integration executable hardcodes Windows `java.exe` (REV-V3-APP-005). | `BookingStore.java:24-50,68-123,132-140`; `BookingCliProcessTest.java:42-50`; app README REQ-MATRIX-JAVA-06 |
| WeChat expenses | **NOT CONFORMANT / P1.** An overflowing cumulative total is persisted before it is rejected, leaving state that crashes the next load (REV-V3-APP-001). The native/stub evidence boundary itself is correct: Node tests inject an explicit fake `wx`; the manifest says native import/runtime/device/publication are `NOT_AVAILABLE` or unexecuted and does not claim native success. | `expense-domain.js:39-51,60-75`; `pages/index/index.js:31-47`; `manifest.json:6-11` |

## Findings

### REV-V3-APP-001 — P1 — WeChat persists an unsafe cumulative total before validation

- Affected requirements: `REQ-MATRIX-WECHAT-002`, `REQ-MATRIX-WECHAT-003`, `REQ-MATRIX-WECHAT-004`, `NFR-MATRIX-WECHAT-001`.
- Evidence: `appendExpense` validates only each individual `amountCents` and returns the appended array (`expense-domain.js:39-51`). `onAddExpense` calls `storage.write(records)` before `pageState(records)` invokes `totalCents` (`pages/index/index.js:34-47`).
- Failure mode and impact: if existing valid records total `Number.MAX_SAFE_INTEGER`, adding `0.01` writes a two-record collection whose sum is unsafe. The current action reports an overflow only after persistence; the next `onLoad` throws while computing the total. This violates “invalid input does not change data,” safe accumulated cents, and restart recovery, and can strand locally persisted user data.
- Targeted reproduction: create a fake `wx` store containing one individually valid record with `amountCents: Number.MAX_SAFE_INTEGER`; create the page adapter; submit `0.01`. Observed: `storedCount=2` and error `合计超出可安全记录的范围`; constructing a fresh adapter and calling `onLoad()` throws the same error.
- Remediation: validate the candidate collection and derive its view state before `setStorageSync`; write only after all domain invariants pass. Also make `onLoad` fail closed to a recoverable empty/error state. Add a page-adapter regression test that asserts storage byte/value stability at the cumulative boundary and successful subsequent reload.

### REV-V3-APP-002 — P2 — Python silently rounds valid large Decimal totals

- Affected requirement: `REQ-MATRIX-PY-02`; design claim that inputs have no amount-digit limit and accumulation does not round.
- Evidence: input parsing accepts every finite, non-negative `Decimal`, while `categories[...] + amount` and `total += amount` use the default finite Decimal context (`expense_analyzer.py:44-55,58-78`).
- Failure mode and impact: valid inputs beyond the default 28-digit precision produce a successful but wrong financial total rather than an explicit rejection.
- Targeted reproduction: analyze two rows in one category with amounts `9999999999999999999999999999` and `2`. Mathematical total: `10000000000000000000000000001`. Observed successful JSON: `{"categories":{"x":"1.000000000000000000000000000E+28"},"total":"1.000000000000000000000000000E+28"}`.
- Remediation: either perform addition in a context sized from validated input digits/exponents, or baseline and enforce explicit precision/exponent limits and reject out-of-range input with `InputError`. Add CLI tests just below/at/above the supported precision boundary and assert the exact string.

### REV-V3-APP-003 — P2 — Python manifest execution is not fully confined to `{build}`

- Affected requirement: shared manifest contract in `2026-09-06-multistack-selftest.md`; build-output confinement.
- Evidence: the current build argv now uses `-X pycache_prefix={build}/pycache`, but the unit argv invokes Python without that option (`manifest.json:8-26`). Importing the application during unit discovery therefore uses the default source-adjacent cache. Current source-tree observation includes `examples/multistack/python_expenses/__pycache__/expense_analyzer.cpython-313.pyc` and a test `__pycache__` `.pyc`.
- Failure mode and impact: the declared unit phase mutates the source application and leaves compiled artifacts outside `.rd-platform/build`; the harness/package source enumerator merely ignores those files. A nominal matrix success therefore does not prove the output-confinement contract.
- Minimal validation: in a disposable checkout, run the manifest unit argv, then search `examples/multistack/python_expenses` for `__pycache__`/`*.pyc`; outputs appear below `{app}`.
- Remediation: add `-X pycache_prefix={build}/pycache` (or an equivalent argv-only confined adapter) to every Python phase that imports/compiles application code, not only `build`. Add a before/after source-tree digest assertion to independent manifest validation.

### REV-V3-APP-004 — P2 — Web startup can crash when the localStorage accessor is unavailable

- Affected requirement: `REQ-MATRIX-WEB-05` (“malformed or unavailable stored data ... without crashing”).
- Evidence: `loadNotes` catches failures from `storage.getItem` (`notes.js:27-37`), but `app.js:11` evaluates `window.localStorage` before entering that function. The same unguarded accessor is used for every persist (`app.js:19-21`).
- Failure mode and impact: a browser/security context that throws while resolving the storage accessor aborts module initialization, so the app never reaches its empty-state fallback.
- Targeted reproduction: define a window-like object whose `localStorage` getter throws `SecurityError: storage denied`, provide the queried DOM stubs, and import `app.js`. Observed import rejection: `startup=SecurityError: storage denied`.
- Remediation: acquire the browser storage object inside a guarded adapter factory and retain one safe storage adapter. On unavailability, initialize an empty in-memory view and display a nonfatal persistence warning. Add a browser/module test for both an accessor throw and `getItem`/`setItem` throws. Preserve the current `textContent`-only rendering discipline and add an actual DOM assertion for stored XSS.

### REV-V3-APP-005 — P2 — Java integration test is Windows-specific despite portable manifest acceptance

- Affected requirement: `REQ-MATRIX-JAVA-06` and `TC-JAVA-008`.
- Evidence: the manifest correctly expands `{java}`, but `BookingCliProcessTest.invoke` constructs its child executable as `<java.home>/bin/java.exe` (`BookingCliProcessTest.java:42-50`).
- Failure mode and impact: on Linux/macOS, a valid JDK and successful manifest build/unit phase still lead integration to spawn a nonexistent `java.exe`. This makes the Java slice non-portable and can be misreported as an application failure rather than an adapter defect.
- Minimal validation: compile on a non-Windows JDK and run the manifest integration argv; the child path ends in `bin/java.exe` and process creation fails.
- Remediation: use the platform executable name (`java` versus `java.exe`) or pass the already resolved `{java}` path into the process test. Add a platform-neutral path-resolution unit test or CI run on one non-Windows host.

### REV-V3-APP-006 — P2 — The supplied five-app review diff is corrupted and not auditable

- Affected evidence: `.rd-platform/reviews/v3-apps.diff`; independent review traceability.
- Evidence: Git warnings were merged into patch bodies, including the opening line and source hunks such as lines 130-133 (`returnwarning: ...`). Similar corruption occurs throughout all five app sections.
- Minimal reproduction: `git apply --numstat .rd-platform/reviews/v3-apps.diff` returns exit `128` with `error: corrupt patch at line 131`; `git apply --check --reverse` fails identically.
- Impact: the artifact cannot be parsed, applied, or used to establish exactly what change set was reviewed. This review therefore used the current working files directly, but the persisted review input remains unsuitable for later audit/replay.
- Remediation: regenerate the scoped diff with stdout and stderr separated, then verify it using `git apply --numstat` and `git apply --check` (or reverse-check against the matching tree) before attaching it as evidence.

## Coverage and residual evidence

- No P0 finding identified. P1: 1. P2: 5. P3: 0.
- C++ and Java intentionally exclude concurrent writers; their read-modify-replace stores do not provide process locking. This is not recorded as a requirement defect because the exclusion is explicit, but widening either tool beyond single-writer use requires locking/version conflict detection and concurrency tests.
- C++ corrupt-input/no-write and Java corrupt-input/no-write paths conform by inspection. Python has no persistence. Web stored HTML is treated as text by the reviewed DOM sinks. WeChat fake-`wx` tests do not cross the native evidence boundary.
- Full developer suites, full independent QA suites, real-browser acceptance, and native WeChat validation were not rerun by this reviewer. The parent orchestrator must record an actual review-phase result only after independent QA evidence is available and the findings above are dispositioned.

## Remediation re-review — 2026-09-06

### Current conclusion

**APPROVED for the current five-application source/specification/manifest review scope.** This current-revision conclusion supersedes the initial technical rejection above without rewriting its history. REV-V3-APP-001 through REV-V3-APP-006 are resolved by inspection and focused regression checks; no new P0, P1, P2, or P3 finding was identified.

This is not a project Gate `PASS`, release approval, human acceptance, real-browser result, Linux/macOS Java execution result, or native WeChat result. The repository remains in `template` lifecycle mode. Independent QA evidence and Runtime review-phase recording remain owned by their respective roles; native WeChat validation remains `NOT_AVAILABLE`.

| Finding | Re-review status | Independent review evidence |
| --- | --- | --- |
| REV-V3-APP-001 | **RESOLVED** | `appendExpense` now validates `totalCents(candidate)` before returning; the page derives `nextState` before `storage.write`; `onLoad` catches an already-damaged cumulative total without rewriting it. Replaying the original fake-`wx` boundary left `storedCount=1`, preserved the original array, reported the overflow, and a fresh `onLoad` returned normally with one record. |
| REV-V3-APP-002 | **RESOLVED** | Python now bounds digits/exponents/rows and derives a local Decimal precision from exponent span and row count before accumulation (`expense_analyzer.py:22-24,47-63,66-97`). Replaying `9999999999999999999999999999 + 2` returned exact `10000000000000000000000000001`; `1e1001` was rejected with `InputError`. The calculation provides sufficient aligned coefficient digits plus carry for the documented non-negative input domain. |
| REV-V3-APP-003 | **RESOLVED** | Both manifest phases now place caches under `-X pycache_prefix={build}/pycache` (`manifest.json:9-28`). Unit discovery and application imports therefore share the confined prefix; the CLI subprocesses execute the main script and do not create a cache beside it. Pre-remediation ignored `__pycache__` files may remain as workspace debris, but the revised manifest no longer produces them outside `{build}`. |
| REV-V3-APP-004 | **RESOLVED** | `createSafeStorage(window)` resolves the accessor inside `try/catch`, caches one adapter, and downgrades get/set failures to in-memory state with a visible non-persistence warning (`storage.js:1-53`; `app.js:12-27,89-102`). Focused checks confirmed accessor denial and later `setItem` denial both remained usable, non-persistent, and warning-bearing. The existing `textContent`-only render path remains intact. |
| REV-V3-APP-005 | **RESOLVED** | The Java child launcher now selects `java.exe` only when `os.name` starts with `windows` (case-insensitive with `Locale.ROOT`) and otherwise selects `java` (`BookingCliProcessTest.java:44-68`). The explicit Windows/Linux/macOS name assertions cover the branch. No non-Windows process execution is inferred or claimed. |
| REV-V3-APP-006 | **RESOLVED** | The regenerated `.rd-platform/reviews/v3-apps.diff` contains no injected working-copy warnings. `git apply --numstat` returned `0` and enumerated all five application trees; `git apply --check --reverse` returned `0`, establishing that the patch parses and matches the reviewed working files. |

### Per-application current verdict

| Application | Current review verdict |
| --- | --- |
| C++ inventory | **CONFORMANT** within the explicit single-writer and WSL validation boundary. Independent retry results remain QA evidence, not reviewer-authored evidence. |
| Python CSV expenses | **CONFORMANT** to the reviewed CSV, exact-total, failure-output, and manifest confinement requirements after REV-002/003 remediation. |
| Web notes | **CONFORMANT** to the reviewed offline CRUD/search, unavailable-storage fallback, persistence-warning, and text-only rendering requirements after REV-004 remediation. Real-browser execution remains separate evidence. |
| Java booking | **CONFORMANT** to the reviewed single-writer booking and portable launcher requirements after REV-005 remediation. Linux/macOS execution remains unexecuted, as explicitly bounded above. |
| WeChat expenses | **CONFORMANT** to the reviewed domain and explicit fake-`wx` adapter scope after REV-001 remediation. Official developer-tool import, native runtime, device storage, and publication remain `NOT_AVAILABLE`/unexecuted and are not replaced by Node evidence. |
