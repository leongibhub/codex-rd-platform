# Stack harness

Task: `TASK-V3-002`

Requirements: `REQ-V3-010`, `NFR-V3-004`
Run: `run-a9b1a1c43fa24acd900496a1284f36a9` / `task-ee636acafdb649eea24dc4a22ddcba5f`

`rd_platform.stack_harness` is the trusted-local CLI boundary for a multistack
`manifest.json` (schema version 1). It accepts argv arrays only and invokes
the existing bounded `runner.run_command`; it neither exposes HTTP command
execution nor interprets shell strings.

## Interface

```python
probe_tools(overrides: dict | None = None) -> dict
run_matrix(manifest_path, *, root=None, tools=None, phases=None) -> dict
package_app(manifest_path, *, root=None) -> dict
```

Tool observations always contain `python`, `node`, `java`, `javac`, and `cxx`.
Python is the running interpreter; Node is resolved from `PATH`; Java uses the
local `JAVA_HOME` or `PATH` before the observed `C:\Program Files\Java\jdk-1.8\bin`
fallback on Windows (a Linux `JAVA_HOME` uses unextended `java`/`javac` names).
On Windows, `cxx` observes an available native `g++`/`g++.exe`; an adapter may
still explicitly choose WSL only when that native compiler is absent. A phase using an unavailable tool is
`NOT_AVAILABLE`; an absent command is `NOT_EXECUTED`, never `PASS`.

`TASK-V3-013` / `BUG-CI-003` aligns this observation with the native C++ adapter
and adds probe contracts for Windows GNU C++ and Linux `JAVA_HOME`. These are
tool-availability observations, not evidence that a compiled program executed successfully.

Only `build`, `unit`, and `integration` are executable phases. Manifest argv
placeholders are `{python}`, `{node}`, `{java}`, `{javac}`, `{cxx}`, `{root}`,
`{app}`, and `{build}`. Unknown placeholders, non-string argv values, paths
outside `root`, duplicate selected phases, non-finite/deep JSON, and source
symlinks are rejected. IDs are portable, single components matching
`[A-Za-z0-9][A-Za-z0-9_-]*`, so they cannot alter build or delivery bases.
Runner evidence is bounded
to 65,536 bytes and returned per actual phase. An optional `output_budget`
must be an integer from 1 through 65,536 bytes.

For any argv element containing `{root}`, `{app}`, or `{build}`, its rendered
path must remain under `root`; `--option={build}/file` is supported. This is a
confinement check for explicit workspace templates, not a claim that arbitrary
trusted manifest argv or the executed program is a security sandbox.

`package_app` writes a deterministic ZIP and a sorted SHA-256 JSON manifest
only to `<root>/.rd-platform/deliveries`; it includes source file hashes and an
aggregate source hash. Its filenames include that aggregate hash and it refuses
to overwrite a mismatched existing delivery. It does not package build/runtime
directories (`.git`, `.rd-platform`, `node_modules`, `__pycache__`, `build`),
secret-like `.env*` or private-key filenames, and it refuses symlinks/junctions
before traversal.

Known sensitive configuration is excluded and reported as `excluded_sources`:
`.npmrc`, `.pypirc`, `.netrc`, `credentials*.json`, `*secret*.json`,
service-account JSON, `.aws/`/`.azure/`, private-key names, PEM/key/P12/PFX
files, and `.env*`. Before hashing or packaging any
remaining file, the harness fails closed if it finds one of its documented,
high-confidence signatures (PEM private-key header, AWS access-key ID, GitHub
token, `sk-` API-key, npm `_authToken`, or Authorization Bearer pattern); the error reports only the relative path and
signature class, never the matched value. This is a small safety check, not a
claim of a complete or general-purpose secret scanner.

For data integrity, packaging captures each included source file once into an
in-memory verified snapshot. The exact snapshot bytes are scanned, hashed, and
written to the ZIP. Immediately before ZIP creation, the current source hashes
are compared to that snapshot; any drift fails closed rather than creating a
delivery. ZIP/JSON temporary files are removed on every packaging failure. This
is a detection boundary, not a cross-process source-locking guarantee: a change
after the check cannot alter the snapshot bytes written to the ZIP.

Verification: `python -m unittest tests.runtime.test_stack_harness -v`.
The test suite covers missing tools, omitted phases, real Python execution,
failed execution evidence, placeholder/path rejection, argv validation, and
repeatable archive hashes. This is local implementation evidence, not a final
system acceptance or release decision.
