# CI validation contract

Record: `TASK-V3-006`; requirement: `NFR-V3-003`; design baseline: `DES-V3-001`.

## Small design

`.github/workflows/platform-validation.yml` is a GitHub Actions validation workflow, not a deployment, release, Gate decision, or human acceptance channel. It runs on push, pull request, and manual dispatch; has only `contents: read`; cancels superseded runs for a ref; and gives every job a timeout. Runtime/platform and multistack jobs each use an Ubuntu/Windows matrix. The runner uses Python 3.11 or newer, installs the repository's only declared Python dependency set (`tools/mcp/company-context/requirements.txt`), and records both runtime/platform contracts and the five manifest-driven sample stacks. The native mini-program remains a Node adapter validation, not a claim that a WeChat IDE, device, or publication ran.

Both matrix jobs establish Node `22` and real Temurin JDK `8`. Runtime/platform
therefore validates its Java clean-build and Node-backed adapter contracts on the
same tool baselines as the five-stack manifest job; it does not inherit a hosted
runner's newer default JDK as a substitute for Java 8 compatibility.

The workflow invokes every phase actually declared by each current manifest. It explicitly selects build/unit for Python and unit for Web because their manifests deliberately have no integration command; those unavailable activities remain `NOT_EXECUTED` in the product evidence and are not converted to a CI PASS.

Action majors were checked against the first-party action documentation on 2026-09-06: [`checkout@v7`](https://github.com/actions/checkout), [`setup-python@v7`](https://github.com/actions/setup-python), [`setup-node@v7`](https://github.com/actions/setup-node), [`setup-java@v6`](https://github.com/actions/setup-java), and [`upload-artifact@v7`](https://github.com/actions/upload-artifact). The Java setup is deliberately pinned to real Temurin JDK `8`, matching the five-stack Java baseline; it does not claim compatibility by compiling on a newer JDK with `--release 8`. The workflow syntax and read-only token permission are defined by [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) and [GitHub token guidance](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token). These are floating first-party major tags, so the CI contract test is intentionally responsible for detecting an accidental downgrade; a future supply-chain policy may require SHA pinning.

The workflow has no retry/`continue-on-error` path that could convert a failed or unavailable phase into PASS. It uploads generated runner evidence and captured unittest output on failure (and when successful) for a bounded retention period. Online execution is `NOT_EXECUTED` until GitHub Actions reports an actual run.

For runtime/platform validation, the workflow creates a real repository-local
`.venv` with `--copies`, installs the declared dependency set through that
interpreter, and regenerates the local MCP launch configuration from
`$GITHUB_WORKSPACE`. Windows uses `.venv/Scripts/python.exe`; Linux uses
`.venv/bin/python`; every runtime/platform test uses that selected interpreter.
This preserves the MCP health check's resolved-path containment contract rather
than pointing configuration at a global runner interpreter. `TASK-V3-014` /
`BUG-CI-004` records this as a CI-boundary repair; it does not relax the
repository, symlink, or command trust checks.

`cpp_inventory/verify.py` selects the native `g++` on Linux and whenever a Windows native GNU compiler is already on `PATH`; it preserves WSL argv support only for existing local Windows environments without such a compiler. The CI Windows job separately requires native `g++.exe`, asks that selected compiler for its `libstdc++-6.dll` location, and adds both the compiler and verified runtime directories to later-step `PATH` (with the runtime directory written last for runner prepend precedence); a missing compiler or runtime DLL fails the job and is never skipped or marked PASS. In runs `34029576291` and `34030786796`, native build succeeded but the Windows unit executable ended with `0xC0000139`; this is recorded as a GNU DLL-resolution mismatch, not a claim that a particular DLL path has been observed as the cause. `TASK-V3-013` / `BUG-CI-003` therefore statically links `libstdc++` and `libgcc` only for native Windows outputs, while retaining normal Linux and WSL flags; both CLI and unit-test binaries are covered. A fresh online run is still required to determine the effect. All compiler and executable invocations use argument vectors and no shell, preserving the build directory confinement already supplied by the adapter. Artifacts are restricted to the generated `.rd-platform/ci` evidence directory; the workflow explicitly permits that hidden path and does not upload the broader runtime/build cache or database.

## Acceptance criteria

| ID | Acceptance criterion | Local verification |
| --- | --- | --- |
| AC-CI-001 | Workflow is stored in `.github/workflows`, has minimal read-only permissions, concurrency, timeouts, failure evidence upload, and Python >= 3.11. | `tests/platform/test_ci_contract.py` |
| AC-CI-002 | Workflow runs runtime/platform contracts and each of the five manifest adapters without treating unavailable/not-executed states as PASS. | `tests/platform/test_ci_contract.py` |
| AC-CI-003 | C++ verification uses Windows WSL argv only on Windows and native `g++` argv on Linux. | `tests/platform/test_ci_contract.py` and Linux command execution |

Local verification establishes implementation behavior only. Hosted execution
must be observed separately from branch protection, Gates, release, and acceptance.

## Observed hosted execution

The actual [third run, 34031461586](https://github.com/leongibhub/codex-rd-platform/actions/runs/34031461586)
finished SUCCESS for source `62c153e8a14425ce4aa3146519129521ded25af5`:
all four Windows/Linux jobs passed, including native Windows C++ execution.
The [execution and defect record](ci-execution.md) preserves the first two failed
runs, independent fix verification, exact job IDs, phase limits, and test counts.
This establishes hosted validation of that commit only. Branch protection,
human acceptance, production deployment, and later code changes are not
established by this result.
