# TASK-V3-011 / BUG-CI-001: deterministic JSON limits

Document State: DRAFT. This records implementation and developer verification, not independent acceptance or a successful CI rerun.

## Source failure and decision

The coordinator supplied real CI failure evidence from commit `a55e3ce`, GitHub Actions run `34029576291`, Ubuntu job `101476522763`: Python 3.13.15 accepted a 5,000-layer host JSON value, so `test_deep_host_json_is_value_error_without_write` failed because no ValueError was raised (179 tests, one failure, four skips). The original implementation relied on the JSON encoder reaching the host interpreter's recursion limit; Windows rejection did not establish a cross-platform data contract. This source failure remains historical evidence and is not replaced by the local results below.

Decision: validate structure iteratively in Store before encoding, and validate parsed data after decoding. No database schema, migration checksum, harness or locked self-test input is modified.

## Explicit contract and acceptance criteria

- Maximum **container depth is 64**, inclusive. A root list/object/tuple has depth 1; its nested container has depth 2. Scalar values do not add a container layer. A scalar root has depth 0. An enclosing Runtime request object therefore contributes one of these layers.
- Maximum **expanded JSON value nodes is 100,000**, inclusive. Containers and scalar occurrences count; object keys do not count as separate value nodes. For example, a root array of 99,999 scalar values is allowed; one of 100,000 scalar values exceeds the limit. This is a structural width/output-expansion bound, not a text-byte limit.
- Lists, tuples and dictionaries are traversed through iterator frames using O(depth) traversal state. Only containers on the active ancestry path are tracked for cycles. Shared acyclic objects remain legal; each reference occurrence consumes its full expanded node budget, preventing a small shared graph from producing exponentially large JSON output.
- Cycles, excessive depth/nodes and non-finite floats (including object keys) raise ValueError before `json.dumps` runs. Existing JSON scalar/type and deterministic serialization behavior remain enforced by the standard encoder. Decoder constants and exponent overflow such as `1e999` are rejected. Parser/encoder RecursionError is normalized to ValueError, not used as the structural limit.
- `Store.loads(None, default)` retains its existing default behavior. Already persisted JSON outside the new bounds is rejected on reading rather than silently accepted under a different host's recursion setting; no historical data is rewritten by this patch.
- Runtime must reject invalid payloads before creating tasks, events or idempotency records. Tests compare every database table through `iterdump`, not just a task count.

The HTTP body's existing **64 KiB** cap is a separate transport-byte limit. It is not a 64-layer nesting policy and is unchanged. Host-side strings may still be large; this patch does not claim an overall memory, string-length or arbitrary untrusted-Python-object sandbox. JSON decoding allocates the parsed representation before structural validation; HTTP byte limits remain the ingress guard for that route.

## TDD and developer checks

The permissive-encoder regression patches `json.dumps` to return successfully and verifies excessive-depth/circular/expanded-size inputs are rejected without invoking it. This reproduces the missing independent check without relying on a particular interpreter limit. The initial new suite produced seven failing assertions. A separate real Runtime command with a 65-layer nested value was accepted by the old implementation; after repair it raises ValueError with the entire database unchanged.

Executed on 2026-09-06:

- Windows: `.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests/runtime -p test_json_limits.py -v` — 8/8 PASS, 0.114 seconds.
- Windows: `.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests/runtime -p test_runtime.py -v` — 18/18 PASS, 1.605 seconds, including the original 5,000-layer regression.
- WSL Linux Python 3.10.12: `python3 -m unittest tests.runtime.test_json_limits tests.runtime.test_runtime -v` from `/mnt/d/codex-rd-platform` — 26/26 PASS, 1.803 seconds.
- `git diff --check -- rd_platform/store.py tests/runtime/test_json_limits.py` — no whitespace error; Git reported its existing CRLF conversion warning for Store.

An additional concurrent-worktree command, `.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests/runtime -v`, ran 194 tests in 105.069 seconds: **FAIL**, one failure, four errors, one skip. All five failures/errors came from the simultaneously introduced `test_java_clean_build` suite: four imports could not find `examples.multistack.java_booking.build`, and the real Java 8 build could not find its absent classes output directory. This run included that task's intermediate source state; the exact observations were handed to the coordinator and no Java files were changed here. It is not a full-suite PASS and must be rerun after the independent Java work is frozen. The other 188 tests passed, including the JSON limit regressions.

Covered boundaries: scalar root, depth 64/65/5,000, mixed enclosing object depth, direct/indirect cycles, legal shared DAG, exponential DAG expansion, exact node limit, finite/non-finite values and keys, exponent overflow, round-trip tuple encoding, and rejection with no database writes. All fixtures are temporary local test data.

Implementation run: `run-5e10fee8d392400f869fe3d31890f036`. The coordinator owns phase completion and dispatches independent testing/review. Real Python 3.13 GitHub CI rerun is still required; WSL 3.10 developer verification is not represented as that CI result.
