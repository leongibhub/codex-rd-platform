# CI validation contract

Record: `TASK-V3-006`; requirement: `NFR-V3-003`; design baseline: `DES-V3-001`.

## Small design

`.github/workflows/platform-validation.yml` is a GitHub Actions validation workflow, not a deployment, release, Gate decision, or human acceptance channel. It runs on push, pull request, and manual dispatch; has only `contents: read`; cancels superseded runs for a ref; and gives every job a timeout. Runtime/platform and multistack jobs each use an Ubuntu/Windows matrix. The runner uses Python 3.11 or newer, installs the repository's only declared Python dependency set (`tools/mcp/company-context/requirements.txt`), and records both runtime/platform contracts and the five manifest-driven sample stacks. The native mini-program remains a Node adapter validation, not a claim that a WeChat IDE, device, or publication ran.

The workflow invokes every phase actually declared by each current manifest. It explicitly selects build/unit for Python and unit for Web because their manifests deliberately have no integration command; those unavailable activities remain `NOT_EXECUTED` in the product evidence and are not converted to a CI PASS.

Action majors were checked against the first-party action documentation on 2026-09-06: [`checkout@v7`](https://github.com/actions/checkout), [`setup-python@v7`](https://github.com/actions/setup-python), [`setup-node@v7`](https://github.com/actions/setup-node), [`setup-java@v6`](https://github.com/actions/setup-java), and [`upload-artifact@v7`](https://github.com/actions/upload-artifact). The Java setup is deliberately pinned to real Temurin JDK `8`, matching the five-stack Java baseline; it does not claim compatibility by compiling on a newer JDK with `--release 8`. The workflow syntax and read-only token permission are defined by [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) and [GitHub token guidance](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token). These are floating first-party major tags, so the CI contract test is intentionally responsible for detecting an accidental downgrade; a future supply-chain policy may require SHA pinning.

The workflow has no retry/`continue-on-error` path that could convert a failed or unavailable phase into PASS. It uploads generated runner evidence and captured unittest output on failure (and when successful) for a bounded retention period. Online execution is `NOT_EXECUTED` until GitHub Actions reports an actual run.

`cpp_inventory/verify.py` selects the native `g++` on Linux and whenever a Windows native GNU compiler is already on `PATH`; it preserves WSL argv support only for existing local Windows environments without such a compiler. The CI Windows job separately requires native `g++.exe`; absence fails the job and is never skipped or marked PASS. All compiler and executable invocations use argument vectors and no shell, preserving the build directory confinement already supplied by the adapter. Artifacts are restricted to the generated `.rd-platform/ci` evidence directory; the workflow explicitly permits that hidden path and does not upload the broader runtime/build cache or database.

## Acceptance criteria

| ID | Acceptance criterion | Local verification |
| --- | --- | --- |
| AC-CI-001 | Workflow is stored in `.github/workflows`, has minimal read-only permissions, concurrency, timeouts, failure evidence upload, and Python >= 3.11. | `tests/platform/test_ci_contract.py` |
| AC-CI-002 | Workflow runs runtime/platform contracts and each of the five manifest adapters without treating unavailable/not-executed states as PASS. | `tests/platform/test_ci_contract.py` |
| AC-CI-003 | C++ verification uses Windows WSL argv only on Windows and native `g++` argv on Linux. | `tests/platform/test_ci_contract.py` and Linux command execution |

Local verification establishes implementation behavior only. GitHub-hosted execution, branch protection, Gate status, release readiness, and acceptance remain `NOT_EXECUTED`/unresolved until separately observed.
