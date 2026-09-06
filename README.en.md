# Codex R&D Platform

> [中文](README.md) · English

This is a local R&D control plane for **Codex host-assisted collaboration**. It stores projects, tasks, quality checks, versioned lifecycle artifacts, test executions, defects, Gate-assessment candidates, and multi-stack validation in SQLite; source and documented facts remain in the Git worktree.

It is not a model-calling cloud service, a multi-tenant system, or a production-release platform. The current source includes a trusted-host resident `worker-service`, an SSH Ed25519 approval adapter, a controlled deployment executor, and a Linux setup script; they expose no anonymous remote-command surface. A confirmed safety probe showed that Codex auto-review can read/write outside its workspace, so the production Codex backend is now fail-closed disabled; separating the control DB and workspace is operational hygiene, **not** isolation. The default proposal path is moving to no-tools HTTPS Responses, where the model has no direct file/command tool and the host alone performs controlled writes and DRAFT registration. Runtime validates, records, and displays facts. The endpoints remain under independent review: there is no real human approval, production deploy/rollback, customer acceptance, successful live-Codex smoke, or live Responses execution conclusion. Start with the [V3 operating guide](docs/platform-v3/README.md) and [V3 delivery record](docs/platform-v3/delivery-record.md).

## Current scope and version

- V3 uses GitHub branch `codex/platform-v3-lifecycle`; this continuation started from `2d77904`. See the [completion delivery record](docs/platform-v3/completion-delivery.md) for verified source commits and corresponding CI. It is **not merged into `main`**; a default-branch clone does not contain this V3 work.
- V2 provides project/task management, four quality Run phases (implementation, unit, integration, review), a board, and controlled local command execution. V3 adds versioned artifacts, traceability, test models/Cases/Executions, work leases, Gate assessment, release/rollback facts, paginated reads, and a five-stack Harness.
- Local source-validation, independent-test, and review records exist, but they are engineering-scope evidence, not formal product acceptance or a production release. See the scoped [traceability index](docs/platform-v3/traceability.md), [final local-validation JSON](docs/platform-v3/evidence/final-local-validation.json), and [capability status](docs/platform-v3/capability-status.md).
- Top-level `platform-manifest.json` remains `lifecycle_mode: template`. A template validation pass, `DONE` task, Harness `PASS`, or Case-report `PASS` is not any G0–G11 `PASS`, human acceptance, or release recommendation.

## Architecture and responsibilities

```text
Git worktree ──source, docs, manifests, review changes──> Git / GitHub
     │
Codex / trusted host ──actual dispatch, commands, cancellation──> Agent / terminal / browser
     │                                                               │
     └──controlled Runtime commands, run evidence, lifecycle facts───┘
                              │
                       SQLite (.rd-platform/state.db)
                              │
               loopback board 127.0.0.1 (observation and limited V2 control)
```

Developers implement, testers test independently, reviewers review independently, and release managers retain real release evidence. An Agent name on the board is not a started model; `ACTIVE` is not evidence of a still-running background process.

## Get the correct source

For a first GitHub checkout, explicitly choose the feature branch:

```powershell
git clone --branch codex/platform-v3-lifecycle --single-branch https://github.com/leongibhub/codex-rd-platform.git
Set-Location codex-rd-platform
git rev-parse --short HEAD       # record the actual output; see the completion delivery record for verified source commits and matching CI
git status --short
```

For an existing clone, first add this branch to `origin`'s fetch refspec. In Windows PowerShell:

```powershell
git remote set-branches --add origin codex/platform-v3-lifecycle
git fetch origin
git show-ref --verify --quiet refs/heads/codex/platform-v3-lifecycle
if ($LASTEXITCODE -eq 0) {
  git switch codex/platform-v3-lifecycle
  git merge --ff-only origin/codex/platform-v3-lifecycle
} else {
  git switch --track -c codex/platform-v3-lifecycle origin/codex/platform-v3-lifecycle
}
git status --short
```

In a Linux/macOS POSIX shell, use the same Git logic:

```bash
git remote set-branches --add origin codex/platform-v3-lifecycle
git fetch origin
if git show-ref --verify --quiet refs/heads/codex/platform-v3-lifecycle; then
  git switch codex/platform-v3-lifecycle
  git merge --ff-only origin/codex/platform-v3-lifecycle
else
  git switch --track -c codex/platform-v3-lifecycle origin/codex/platform-v3-lifecycle
fi
git status --short
```

Until a merge happens, do not treat `main` as the V3 baseline described here. The existing-branch path permits only a fast-forward; if `merge --ff-only` fails because of local commits or changes, preserve and review work before resolving it—never force-switch over it. Work in your own branch/worktree, inspect Git status and recent history first, and preserve other collaborators’ uncommitted changes.

## Install and verify

### Windows (provided one-step path)

Prerequisites: Git, PowerShell, Python 3.11+, and configured repository `git user.name` / `git user.email`. If this clone is not configured, set an approved identity **in this repository only**; do not alter global configuration or copy a real identity into documentation:

```powershell
git config --local user.name "YOUR_APPROVED_DISPLAY_NAME"
git config --local user.email "your-approved-address@example.invalid"
git config --local --get user.name
git config --local --get user.email
```

Replace the placeholders with your approved, auditable identity. These values are written only to this clone’s `.git/config`; they do not modify system or global Git configuration.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --help
& .\.venv\Scripts\python.exe -X utf8 scripts\validate_platform.py
```

`setup.ps1` creates or reuses `.venv`, installs constrained dependencies from `tools/mcp/company-context/requirements.txt`, runs `pip check`, creates `knowledge\local`, writes current-worktree MCP absolute paths, and runs platform validation. It does not upgrade pip or persist user environment variables by default. Use `-SkipDependencyInstall` only with a prepared environment; only `-PersistLocalRoot` persists `COMPANY_LOCAL_ROOTS`.

The normal and **recommended** installation path remains `git clone --branch ... --single-branch` above, repository-local `git config --local`, then `setup.ps1`. That gives the target its own auditable Git identity and branch history; do not copy a source worktree's local Git configuration into another location.

#### Optional: Windows fixed-commit advanced delivery helper

Use root-level `install-to-D.ps1` only when a GitHub clone is unavailable and the delivery operator can verify a fixed commit. It is not a routine sync, incremental-update, or backup tool: it initializes a Git repository in the target, depth-1 fetches source `HEAD^{commit}`, makes a detached checkout with **no configured remote**, and only then runs target `setup.ps1`. It does not recursively copy the source `.git`, ignored/untracked files, `.venv`, `.rd-platform`, worktrees, caches, `.env`, or local knowledge. The sole narrow exception is committed public stub `knowledge/local/README.md`, which must also match blob `f361c8f3bd3b7bb62af25fb46bb48c0965c2e263`. This is not local-data migration.

Prerequisites and rejections:

- The target must be a new directory or an existing **empty** ordinary directory. The helper rejects `-Force`, a non-empty directory, the source itself or a source descendant, and a reparse point in either source/target ancestor path. It never merges with, overwrites, or deletes an existing target.
- A fresh target does not inherit source `.git/config`. `setup.ps1` must still see `git user.name` and `git user.email` in the target process. Prefer the recommended clone path and its repository-local configuration above. If organizational policy allows and this helper is the only option, provide an approved identity for the **current PowerShell process** (not global/system configuration):

```powershell
$env:GIT_CONFIG_COUNT = "2"
$env:GIT_CONFIG_KEY_0 = "user.name"
$env:GIT_CONFIG_VALUE_0 = "YOUR_APPROVED_DISPLAY_NAME"
$env:GIT_CONFIG_KEY_1 = "user.email"
$env:GIT_CONFIG_VALUE_1 = "your-approved-address@example.invalid"
.\install-to-D.ps1 -Destination "D:\your-empty-target"
```

Replace the placeholders with an approved, auditable identity. Those environment variables affect only Git child processes launched from this PowerShell; they do not write the identity into source or target Git configuration. If initialization, fetch, checkout, or setup fails, the helper prints no success message and does not automatically clean or reuse the directory. When this invocation created the target, it leaves `.install-failed` for diagnosis. Preserve the error and target, review them, then choose a new empty target or explicitly clean up before retrying.

The revision-3 helper has independent evidence of unit 12/12, integration 10/10, and reviewer 22/22 PASS. A real isolated installation from `527dae1b7f75d6b526682d1c5a6407c1b3fc6a53` ran full setup, dependencies, and MCP checks; its recorded result is `PASS (TEMPLATE MODE)` with `Evaluated Gates: NONE`. See the [independent installation-transfer review](docs/platform-v3/install-transfer-review.md) and [real isolated-install validation](docs/platform-v3/install-real-validation.md). The former recursive-copy implementation is retained historical BUG-INSTALL-001; the real `c3eb271` public-stub rejection is BUG-INSTALL-002. Neither describes this helper's behavior nor proves release or human acceptance.

### Linux (verifiable manual venv path)

Linux uses the manual installation below; the config generator now supports native `.venv/bin/python`. Use `--copies` to keep the interpreter inside the repository for MCP's resolved-path trust checks; do not bypass them with an interpreter symlink pointing outside the checkout.

```bash
python3 --version                     # must be 3.11 or newer
python3 -m venv --copies .venv
. .venv/bin/activate
python -m pip install -r tools/mcp/company-context/requirements.txt
python -m pip check
mkdir -p knowledge/local
export COMPANY_LOCAL_ROOTS="${COMPANY_LOCAL_ROOTS:-$PWD/knowledge/local}"
python scripts/write_local_config.py "$PWD"
python -X utf8 scripts/validate_platform.py
python -X utf8 -m rd_platform --help
python -X utf8 -m rd_platform stack-probe
```

`validate_platform.py` actually starts MCP and checks its tool list; its observed health result is the evidence for your machine. Do not reuse `.codex/config.toml` from another checkout. Remote MCP services still need real network access and accounts. See the [CI execution record](docs/platform-v3/ci-execution.md) for the exact commits and hosted Linux/Windows results.

## Start or continue in Codex

Open the repository in Codex and read rules/current facts before development.

Short prompt for a new project:

> Use `platform-orchestration` to start a local project for “<business goal>”. Read `AGENTS.md`, current Git state, and the Runtime snapshot first; make the requirements and acceptance boundary explicit; record real host-Agent work on the board, and ask me only about material business choices.

Short prompt for continuation:

> Use `platform-orchestration` to continue “<goal>” in `<repository or directory>`. Read source, Git, Runtime `lifecycle`/`report`, and project documents first; do not rebuild completed work, and advance from missing evidence and unmet Gate prerequisites.

The Skill is a work-method constraint, not a service launcher. It requires the host to snapshot first, use actual developer/tester/reviewer roles, and link actual results. Codex-host delegation differs from the Runtime, which does not dispatch unattended cloud Agents.

You can start with a no-model requirements-discovery draft:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform discover "Build an internal test-management system"
```

`discover` results are marked `baseline_no_model`; `freeze` only makes DRAFT SRS/RTM from confirmed answers. Neither replaces stakeholder discovery, review, or human approval.

## Runtime, board, and CLI

The default database is `.rd-platform/state.db` in the current directory. Start the local board:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform serve
# Open http://127.0.0.1:8020/
```

The board listens only on `127.0.0.1` and reads persisted projects, tasks, Agents, Runs, events, and V3 lifecycle summaries. The V3 view actually shows project state, current Gate, number of decided Gates (explicitly “not all passed”), artifact count, trace gaps, open defects, and paginated detail. Auto-refresh pauses while evidence is expanded, so the detail is not collapsed; refresh manually when needed. Use CLI cursors for complete rather than page-limited data.

The browser is not an arbitrary-command, Run-finish, human-approval, Gate-decision, release, or deployment interface. Trusted CLI/host actions remain required after real evidence exists.

Useful read-only commands; replace `PROJECT_ID` with a real ID and never invent a cursor:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform snapshot
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform snapshot --project-id PROJECT_ID
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle --project-id PROJECT_ID --limit 200
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle-collection --project-id PROJECT_ID artifacts --limit 200
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle-report --project-id PROJECT_ID
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform project-export --project-id PROJECT_ID --output-dir NEW_DIRECTORY
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform report --project-id PROJECT_ID
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-probe
```

`report` is the V2 `MODULE_QUALITY` report. `lifecycle-report` captures **all** versioned lifecycle collections through a consistent, paginated Runtime read and then reports current-version declared Test Cases; its totals are not the first 500-row page. The two reports have different scope/denominator. `lifecycle-report` changes no Gate; `complete_snapshot=true` or all Cases passing alone is insufficient to recommend release. Gate, traceability, defect and release-evidence criteria must also be satisfied.

### Complete reports, project export, and version-bound automated Cases

`project-export` makes a read-only document-index package for an active project. `NEW_DIRECTORY` must have an existing trusted parent while the destination itself is new; the command rejects overwrite, links/traversal, and existing output. It stores indexes for artifacts/versions/traces/Gates/evidence, formal JSON/Markdown test reports, collection counts, and a project-record fingerprint from one consistent read. `export-manifest.json` must be `COMPLETE`, with each listed SHA-256, before it is a finished projection. It modifies neither source database nor Gates and deliberately excludes source files, inline artifact bodies, raw command output, and secrets. It is a **document projection, not an executable backup, Git archive, or approval package**.

For a versioned functional/general automated Case, invoke the public CLI below; the command line cannot supply or override the test command:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db PATH test-run --project-id ID --case-id TC-ID --case-version N --executor-id REAL_TESTER --timeout 60
```

`test-run` reads argv only from the exact Case version’s `automation.argv` and launches under an `executor-id` declared by the trusted host and registered as a tester. That ID is only a Runtime role check: it is not identity authentication and does not impersonate another OS user. Independence still requires real host assignment and evidence. The runner rechecks the project, Case version, Test Model, requirements, and locked code references. The Case must be `BASELINED` or `APPROVED`; a suitable automation definition is:

```json
{
  "automation": {
    "status": "AUTOMATED",
    "method": "argv",
    "tool": "python",
    "entrypoint": "tests/assertions.py",
    "argv": ["{python}", "tests/assertions.py"],
    "cwd": ".",
    "subject_refs": [{"type": "CODE_CHANGE", "id": "CODE-xxx", "version": 1}]
  }
}
```

Every `CODE_CHANGE` must be a `BASELINED`/`APPROVED` repository-file artifact fixed by `path` and SHA-256; inline content is not a substitute. The runner supports only declared `{python}`/`{root}` placeholders, repository-relative `cwd`, and argv; it is not an arbitrary-code sandbox. This generic runner rejects `PERFORMANCE`, `STRESS`, and `STABILITY` Cases: use a specialized metrics adapter that records measured values, never exit code zero as invented NFR metrics.

Trusted CLI can record a real V2 quality Run. First create a real task, register real roles, and let the developer complete implementation; tester/reviewer self-validation is prohibited:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform run --task-id TASK_ID --agent-id TESTER_ID --phase unit --cwd . --timeout 60 -- .\.venv\Scripts\python.exe -m unittest tests.runtime.test_stack_harness -v
```

`run` executes the argv after `--` without a shell and records start, exit code, output summary, timeout, and finish status. Exit code zero only means the command succeeded; it cannot establish enough testing, Gate passage, or product acceptance.

### Pause, resume, and host-process boundary

- Runtime `pause` invalidates active Runs and stops later Runtime scheduling. It does **not** terminate a process already launched by Codex, terminal, WSL, browser, or a remote system.
- Cancel external work through the real host/terminal, then record the actual result. Never equate “paused” with “process terminated”.
- `resume` only restores a resumable pause; a FAILED task must retry. `modify` creates a revision and expires downstream results; `reject`/`skip` are never PASS.
- Closing the board stops only the foreground HTTP process, not other writers or external Agents.

Use an isolated database for rehearsal:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db .rd-platform\trial.db snapshot
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db .rd-platform\trial.db serve --port 8021
```

## Five application types: build and test

Harness accepts only argv in controlled `manifest.json` files and writes build artifacts under `.rd-platform/build/<id>`. It is a trusted-local execution adapter, not a sandbox for unknown or malicious code.

```powershell
# C++: Python drives WSL Ubuntu g++; native Windows C++ is not the verified path.
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\cpp_inventory\manifest.json --phase build --phase unit --phase integration

# Python: manifest declares build/unit only; undeclared integration is NOT_EXECUTED.
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\python_expenses\manifest.json

# Web: Node unit test; observe real browser flow independently.
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\web_notes\manifest.json --phase unit
Push-Location examples\multistack\web_notes; python -m http.server 8080 --bind 127.0.0.1; Pop-Location

# Java: requires available javac/java; existing evidence used JDK 8.
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\java_booking\manifest.json --phase build --phase unit --phase integration

# WeChat: Node domain module and fake-wx page adapter only, not native mini-program execution.
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\wechat_expenses\manifest.json --phase unit --phase integration
```

`stack-probe` checks local tools. Missing tools are `NOT_AVAILABLE`; undeclared phases are `NOT_EXECUTED`; neither is PASS. Current evidence uses WSL for C++, contains one real-browser Web user flow, and still lacks WeChat Developer Tools, device, real `wx` storage, and publication evidence. See [Harness](docs/platform-v3/stack-harness.md), [browser validation](docs/platform-v3/browser-validation.md), and [live lifecycle validation](docs/platform-v3/live-lifecycle-validation.md).

To create local delivery archives (not a release):

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\cpp_inventory\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\python_expenses\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\web_notes\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\java_booking\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\wechat_expenses\manifest.json
```

Record ZIP/source/file SHA-256, Git SHA, command, environment, and operator. A successful archive is not a `REL-*`, successful deployment, or customer sign-off.

## MCP, secrets, and existing-repository onboarding

On Windows, `setup.ps1` rewrites `company_context` absolute paths in `.codex/config.toml`, forwarding only these **variable names**:

```text
COMPANY_LOCAL_ROOTS
REDMINE_BASE_URL, REDMINE_API_KEY, REDMINE_PROJECT
RAGFLOW_BASE_URL, RAGFLOW_API_KEY, RAGFLOW_DATASET_ID
GITLAB_BASE_URL, GITLAB_TOKEN, GITLAB_PROJECT_ID
```

`tools/mcp/company-context/.env.example` is only a variable inventory. Keep actual URLs, tokens, cookies, passwords, authorization headers, and private keys in secure OS environment variables or an approved secret manager—never README, example env, task evidence, terminal captures, or Git. Reopen terminal/Codex after configuration and run `scripts/validate_platform.py` for the current-machine health result. MCP reads local documents only under approved `COMPANY_LOCAL_ROOTS`; Redmine/RAGFlow/GitLab availability depends on real network, permission, and service contracts, and must be reported unavailable when not configured.

To onboard an existing repository:

1. Start in an independent branch/worktree; read `AGENTS.md`, requirements/design/test materials, Git state, recent commits, and evidence. Do not bulk-rewrite history.
2. Use a separate `.rd-platform/<project>.db`; register existing artifacts with path, version, and digest, then incrementally add real REQ/DES/TASK/CODE/TC/BUG/REL links.
3. Preserve `NOT_AVAILABLE` when historic model source is absent; explicitly adopt a new version and re-run applicable Cases. Never overwrite v1 history with a v2 result.
4. For verification-only work on existing code, record independent testing in V3 work and `test_execution`; do not fabricate historical V2 implementation PASS to satisfy implementation→unit order.
5. An `active` Runtime record from `lifecycle.initialize` only initializes that project’s fact model. Formal Gates still need that project’s central Gate Register, complete artifacts, resolvable evidence, and an authorized decision; it does not alter this repository’s top-level template state.

## Reports, backup, recovery, and current state

- `snapshot` is current Runtime state; `lifecycle` is the versioned snapshot; `lifecycle-collection` reads complete collections with cursors; `report` and `lifecycle-report` differ in scope.
- Evidence Status is only `PENDING`, `NOT_AVAILABLE`, `NOT_EXECUTED`, `INFERRED`, `OBSERVED`, or `VERIFIED`. `BLOCKED` is only for permitted Gate or verification-result domains.
- A Gate is assessed first and then decided by an authorized person with real, resolvable evidence. Human approval, executed tests, deployment, rollback, customer acceptance, and defect closure cannot be inferred from documentation, fixtures, model output, or exit code zero.
- The five samples completed legacy-model v2 adoption, Case v2, and independent retest. Their reports remain `recommend_release=false`, and G0/G7 have no formal decision. See [live lifecycle validation](docs/platform-v3/live-lifecycle-validation.md).
- The Python-expenses per-REQ/NFR local lifecycle project has 37/37 real current-Case PASS results and 7/7 `COMPLETE` RTM rows; after independent review, G0–G8 are `DECIDED PASS CURRENT`. Its finalization state is `G0_G8_COMPLETE_G9_PENDING`; G9–G11 remain `NOT_EVALUATED`, there is no human acceptance, and release is not recommended. See [Python lifecycle validation](docs/platform-v3/python-lifecycle/README.md), [independent review](docs/platform-v3/python-lifecycle/independent-review.md), and [completion delivery record](docs/platform-v3/completion-delivery.md).

### Implemented features and observed evidence

| Item | Current fact and boundary |
| --- | --- |
| Complete report, read-only project export, Case-bound runner | Implemented with local verification records. The report is not truncated at its first page; export refuses overwrite and excludes source/secrets; `test-run` executes only baselined version-bound argv, while an ordinary command outcome is not a Gate. See [export guide](docs/platform-v3/project-export.md) and [test-run validation](docs/platform-v3/test-run-validation.md). |
| SQLite read capacity | Synthetic `capacity --profile full` was observed: 100 projects, 100,000 artifact versions, 1,000,000 events; terminal JSON PASS in 129.7199 s at 294,764,544 bytes with no public-read errors. This measures only local SQLite `Runtime.lifecycle_collection`/`Runtime.lifecycle_snapshot` reads, not production throughput, write performance, SLO, Gate, or release. See [performance validation](docs/platform-v3/performance-validation.md). |
| Eight-hour soak | Started in `.rd-platform/benchmark-soak-8h-20260906-1`; the current run has a checkpoint but no terminal JSON, so there is no completion/PASS conclusion. The host’s 30-minute heartbeat is completion/failure notification only, not a benchmark result. |
| GitHub Actions CI | The real [run 34032990521](https://github.com/leongibhub/codex-rd-platform/actions/runs/34032990521) for `527dae1b7f75d6b526682d1c5a6407c1b3fc6a53` completed SUCCESS at `2026-09-06T12:32:02Z`, with 4/4 jobs SUCCESS (Windows runtime job `101485885964` completed at `12:32:01Z`). Earlier success for `62c153e` and `c3eb271`, first-/second-run failures, and remediation remain in the [CI execution record](docs/platform-v3/ci-execution.md); `c3eb271` workflow success does not erase its later retained real-install failure. This row covers only that source workflow, not subsequent documentation-only changes; Node/fake-`wx` is not WeChat IDE, device, or publication validation. |
| Python requirement-by-requirement lifecycle closure | The scoped existing Python-expenses CLI project completed 37/37 current-Case PASS, 7/7 `COMPLETE` RTM, and G0–G8 `DECIDED PASS CURRENT`. This is not G9 human acceptance, production deployment, or release recommendation. G9–G11 remain `NOT_EVALUATED`; finalization is `G0_G8_COMPLETE_G9_PENDING`. |

Capacity/soak use their specialized benchmark and a fresh isolated output directory. Do not target a project state database or reuse existing output:

```powershell
# Review smoke JSON first and reserve local CPU/disk before the full run.
& .\.venv\Scripts\python.exe -X utf8 scripts\benchmark_lifecycle.py capacity --output-dir D:\perf\lifecycle-full --profile full

# Start an authorized long read-path observation; terminal JSON is the completion record.
& .\.venv\Scripts\python.exe -X utf8 scripts\benchmark_lifecycle.py soak --output-dir D:\perf\lifecycle-soak-8h --profile full --duration-seconds 28800 --interval-seconds 1
```

While running, read `<output-dir>/perf-<run-id>-checkpoint.json` (capacity) or `<output-dir>/soak-<run-id>-checkpoint.json` (soak); on completion read the same-prefix `*-terminal.json`, checking status, budgets, and `seed_mode=synthetic_batch_sql`. Long-run data still covers public reads only, not Runtime write throughput, production user flows, or whole-system stability.

Before backup, stop the board, CLI, and other SQLite writers; preserve a timestamped copy of `.rd-platform/state.db`, and do not commit databases, run output, archives, or credentials. Save code Git SHA, artifact SHA-256, and external evidence locators together; after recovery compare `snapshot`, `lifecycle`, and digests. Recovery does not create test/approval facts. Roll back code with reviewed `git revert` or known-version deployment; V3 adds tables, so returning to V2 code must not delete `lc_` tables. Restore database only from a verified backup; no generic downgrade or automatic DROP-table plan exists. Once work genuinely enters release, a release manager records operator, reason, environment, and evidence using `release.rollback`; a code rollback or zero exit code is not proof of successful production rollback.

| Boundary | Current state | Required before completion can be claimed |
| --- | --- | --- |
| Trusted `worker-service` (not a cloud Agent) | `OBSERVED`: current source supplies durable workers, leases/heartbeats/cancellation, controlled `argv`, and no-tools Responses file proposals; the production Codex backend is fail-closed disabled. | Requires protected configuration, real work orders, and an observable host process. There is no successful resident-worker or live Responses execution fact, so autonomous project completion is not claimed. |
| Formal G0–G11 / human acceptance | No decision | Active-project central Gate Register, complete BG→PRD→REQ→DES→TASK→CODE→TC→BUG→REL trace, real evidence, and authorized decision. |
| SSH approval provider | `OBSERVED`: the optional Ed25519 adapter and challenge/register CLI are in source; an unconfigured default Runtime still refuses approval. | Requires operator-protected signer/trust configuration, an external signature, and actual authority. There is no project human approval or Gate decision. |
| Production deployment, release, rollback | `NOT_EXECUTED` | Authorized environment, `REL-*`, install/rollback instructions, known issues, real operator, and environment evidence. Git push is not a substitute. |
| WeChat native | `NOT_AVAILABLE` | Developer Tools, authorized project, real import/run/storage validation, and device/publication authority if required. Node fake-wx is not a substitute. |
| Production/user-flow write performance, cross-browser/cross-OS, complete security matrix | `NOT_EXECUTED` | Their own controlled environment, load/duration/metrics, raw output, and independent review; the synthetic SQLite read benchmark cannot be extrapolated. |
| One-step Linux MCP install | `OBSERVED`: `scripts/setup.sh` creates/reuses the checkout venv, generates configuration, and invokes the validator; native setup and repeat-install both succeeded in GitHub Actions Ubuntu job `101496781967`. | That job covers only its Ubuntu script version; it cannot be extrapolated to all target Linux hosts, production deployment, release, or acceptance. |

Do not expose the loopback board to a network. Harness has path/argv constraints but is not a malicious-code sandbox; run untrusted code in a separate controlled environment. Commands, logs, and evidence must not print secrets.

## Further reading

- [V3 local operation and recovery](docs/platform-v3/README.md)
- [Capability matrix and known boundaries](docs/platform-v3/capability-status.md)
- [Release readiness](docs/platform-v3/release-readiness.md)
- [Independent platform tests](docs/platform-v3/independent-platform-tests.md) and [Runtime review](docs/platform-v3/runtime-review.md)
- [Five-stack lessons learned](docs/platform-v3/lessons-learned.md)
- [V2 Runtime guide](docs/platform-v2/README.md)

## CR-V3-003 execution endpoints: controlled use (implemented, pending final review)

This is the current CLI/JSON contract, not a deployment claim. Keep the control plane and workspace in **different directories** for operational hygiene, but do not treat that as isolation for a model running under the same OS identity. Codex auto-review was confirmed able to read/write a harmless sentinel outside the workspace and is now fail-closed disabled in production. Replace every `PROJECT_ID`, operator, path, Git SHA, evidence ID, and hash below with current facts.

### Bootstrap a resumable work list from a rough idea

`orchestrate-start` is idempotent on `--request-id`: repeating the same request in one control DB returns the bootstrap fact rather than creating another G0–G11 work-order chain. It creates only a DRAFT BG, active lifecycle record, and `PLANNED` work; it creates no approval, test result, or Gate PASS.

```powershell
$controlDb = 'D:\rd-control\state.db'
$workspace = 'D:\workspaces\inventory-service'
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb orchestrate-start `
  --name 'Inventory service' --idea 'State the real business goal and known constraints; work items clarify unknowns.' `
  --repository-root $workspace --request-id 'bootstrap-inventory-20260906-001'
```

Record the returned `project_id`, then repeat the identical command to exercise retry. Do not copy the control DB into `$workspace\.rd-platform`, but do not mistake separated paths for a guarantee that a model cannot access it.

### Register real roles and run workers

Every `agent_id` in worker configuration must first be registered in the **same control DB**, with an exact role. Supported roles are `requirement_analyst`, `researcher`, `product_manager`, `architect`, `developer`, `tester`, `reviewer`, `documentation_manager`, and `release_manager`; each ID must represent the actual host responsibility.

```powershell
$roles = 'requirement_analyst','researcher','product_manager','architect','developer','tester','reviewer','documentation_manager','release_manager'
foreach ($role in $roles) {
  & .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb command agent.register ("{`"id`":`"host-$role`",`"role`":`"$role`"}") --request-id "register-$role-001"
}
```

Store this complete configuration in a protected, non-Git directory such as `D:\rd-control\worker-service.json`. The current safe default is the `responses` proposal backend: an HTTPS Responses request fixes `tools:[]` and `tool_choice:"none"`; the model returns only structured file proposals, and the controlled host checks version-bound context, path/size, and exclusive CAS creation before registering a new artifact as `DRAFT`. Every repository-relative path a worker may create or update, including a new file, must be explicitly listed in that worker's `source_paths`; an empty list cannot publish a proposal. `OPENAI_API_KEY` is currently `NOT_AVAILABLE` on this host, so this is not evidence of a completed live Responses run. `argv` is only for an already-approved trusted-host command; it is not a sandbox for unknown code.

```json
{"project_id":"PROJECT_ID","repository_root":"D:\\workspaces\\inventory-service","max_concurrency":3,"poll_interval_seconds":0.5,"workers":[
{"agent_id":"host-requirement_analyst","role":"requirement_analyst","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/requirements.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-researcher","role":"researcher","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/research.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-product_manager","role":"product_manager","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/product.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-architect","role":"architect","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/design.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-developer","role":"developer","lease_seconds":300,"timeout_seconds":1200,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["src/app.py","docs/implementation.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-tester","role":"tester","lease_seconds":300,"timeout_seconds":1200,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["tests/system_test.py","docs/test-report.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-reviewer","role":"reviewer","lease_seconds":300,"timeout_seconds":1200,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/review.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-documentation_manager","role":"documentation_manager","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/closure.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
{"agent_id":"host-release_manager","role":"release_manager","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/release.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}}
]}
```

Use one observable dispatch first; its `IDLE`/`DISPATCHED`/`WAITING_USER`/`FAIL` output is not a Gate conclusion:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb worker-service --config D:\rd-control\worker-service.json --once
```

Omit `--once` for a foreground resident worker. Run it through an approved service manager or controlled terminal and protect secret-free stdout/stderr logs. Production Codex `auto-review` is disabled: no `approval_mode`, `persist_session`, path separation, or extra CLI flag may re-enable it. The Responses proposal path grants the model no file/command tool; only the host writes after CAS, hash/path, and version checks, then creates a DRAFT artifact. On stop, pause, or invalidation, reconcile `lifecycle`/`work.reap` with the real process state; neither OS termination nor `pause` proves cancellation. An expired lease with unknown side effects is retried only when `safe_to_retry: true`.

### External SSH-signature approval

This is an unsigned request, with no private key. The canonical bytes are the UTF-8 `Store.dumps` challenge emitted by the CLI: never reformat, edit, reserialize, or reuse the signature after changing the request.

```json
{"project_id":"PROJECT_ID","kind":"human_approval","status":"VERIFIED","locator":{"inline_json":{"external_record":"APPROVAL-RECORD-REFERENCE"}},"observed_at":"2026-09-06T12:00:00+00:00","metadata":{"gate_id":"G9","decision":"APPROVE","statement":"Actual authorized decision text.","artifact_refs":[{"type":"REQ","id":"REQ-001","version":1}]}}
```

Keep `provider.json` protected, with actual project IDs and authorized operators; `allowed_signers` contains public keys only:

```json
{"provider_id":"corp-approval-ssh-2026","allowed_signers":"D:\\secure\\approval\\allowed_signers","ssh_keygen":"C:\\Windows\\System32\\OpenSSH\\ssh-keygen.exe","authorizations":[{"operator":"approved-operator","projects":["PROJECT_ID"],"gates":["G9","G10","G11"]}],"challenge_ttl_seconds":300,"timeout_seconds":10,"max_output_bytes":4096}
```

```powershell
$req='D:\secure\approval\request.json'; $provider='D:\secure\approval\provider.json'; $challenge='D:\secure\approval\challenge.json'
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb approval-challenge --provider-config $provider --request $req --operator approved-operator --challenge $challenge
# A human signs outside the platform. Do not record private-key material, path, or passphrase.
ssh-keygen -Y sign -f PATH_TO_PRIVATE_ED25519_KEY -n rd-platform-approval $challenge
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb approval-register --provider-config $provider --request $req --operator approved-operator --challenge $challenge --signature "$challenge.sig"
```

A challenge only means “waiting for signature”. Registration recomputes current project/Gate/decision/artifact-version/policy binding and rejects expiry, replay, unauthorized scope, a same-named Agent, or drift. Signature authentication also does not decide a Gate or prove customer acceptance.

### Trial deployment, formal deployment, and rollback

`deploy-run` runs only explicit configured argv; it does not derive commands from an environment label, HTTP, or model output. `trial` keeps durable receipts but never writes release/deployment truth. This is the complete trial shape; scripts live under `cwd`, and every `source_hashes` value is SHA-256 computed from the real pre-run file.

```json
{"project_id":"PROJECT_ID","environment":"isolated-local","mode":"trial","operation_id":"trial-20260906-001","cwd":"D:\\workspaces\\inventory-service\\ops","source_hashes":{"deploy.ps1":"ACTUAL_SHA256","rollback.ps1":"ACTUAL_SHA256","health.ps1":"ACTUAL_SHA256","rollback-health.ps1":"ACTUAL_SHA256"},"deploy":{"argv":["powershell","-NoProfile","-File","deploy.ps1"],"timeout_seconds":300,"output_limit_bytes":65536,"idempotent":true},"health":{"argv":["powershell","-NoProfile","-File","health.ps1"],"timeout_seconds":60,"output_limit_bytes":16384},"rollback":{"argv":["powershell","-NoProfile","-File","rollback.ps1"],"timeout_seconds":300,"output_limit_bytes":65536},"rollback_health":{"argv":["powershell","-NoProfile","-File","rollback-health.ps1"],"timeout_seconds":60,"output_limit_bytes":16384},"receipt_dir":"D:\\workspaces\\inventory-service\\.rd-platform\\deployment-receipts"}
```

Update hashes with `Get-FileHash`, then execute. The same `operation_id` may read only a completed matching fingerprint; drift or a leftover `STARTED` receipt requires human reconciliation, never blind replay:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb deploy-run --config D:\rd-control\trial-deploy.json --action deploy
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb deploy-run --config D:\rd-control\trial-rollback.json --action rollback
```

`formal` additionally requires `release_id`, a non-Agent human `operator`, a registered release-manager `executor_id`, current `G10 PASS`, a `READY` release, `environment_ref`, and nonempty `evidence_artifact_refs`. Runtime checks again around the physical action. Trial/exit-0/health success does not satisfy these conditions or prove production success. On health failure, the declared rollback and separate `rollback_health` run; their actual results stay in receipts.

### Native Linux setup

Run inside the target Linux checkout (no sudo, global Git/Python change, or deletion of existing data):

```bash
git config --local user.name 'YOUR_APPROVED_DISPLAY_NAME'
git config --local user.email 'your-approved-address@example.invalid'
./scripts/setup.sh --python-command python3.11
./scripts/setup.sh --skip-dependency-install  # dependencies already installed; regenerate config and health-check
.venv/bin/python -X utf8 -m rd_platform --help
```

The script first verifies Git identity and Python 3.11+, then creates/reuses the checkout `.venv`, runs `pip check`, `write_local_config.py`, and `validate_platform.py`. Only real successful validator output plus `Setup complete.` is installation/health evidence for that machine. Failure retains diagnostics and can be corrected/re-run.

Source, CLI help, and developer/independent test records for the endpoints are observable, but final review is pending; this change publishes no global PASS. The failed live Codex smoke remains read-only history and is not rewritten as success. See the [execution design](docs/platform-v3/completion-execution-design.md), [worker service](docs/platform-v3/worker-service.md), [approval provider](docs/platform-v3/approval-provider.md), [deployment executor](docs/platform-v3/deployment-executor.md), and [Linux setup](docs/platform-v3/linux-setup.md).
