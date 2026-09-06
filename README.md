# Codex R&D Platform

A repository-first multi-agent software/product development operating system for Codex.

## What this package contains

- 9 specialized Codex agents
- 14 repository Skills
- lifecycle Gates G0–G11
- full project documentation set from initiation to closure
- requirement traceability matrix (RTM)
- risk / issue / change management
- task / defect / change templates
- Company Context MCP:
  - local files
  - Redmine
  - RAGFlow retrieval
  - GitLab project/issues
- Windows PowerShell setup
- platform validator

## V2 local runtime

The repository now includes a local task/agent/event runtime and a Chinese dashboard, in addition to the original SDLC templates. From the repository root:

```powershell
& .\.venv\Scripts\python.exe -m rd_platform serve
```

Open `http://127.0.0.1:8020`. Runtime records live in the ignored `.rd-platform/` directory. No cloud service or new dependency is required for this runtime. See [V2 operation guide](docs/platform-v2/README.md) for CLI, quality checks, backup/recovery, tests and limitations.

This is a **trusted local operator / host-assisted runtime**, not an autonomous model server or a multi-user security boundary. The browser cannot execute arbitrary commands or submit verification results. Use the `platform-orchestration` Skill with real host agents to connect actual work to the board. The existing template-mode Gate rules still apply; module DONE is not release or human acceptance.

## Important evidence rule

This platform intentionally does **not** fabricate:
- approvals
- signatures
- test results
- performance data
- customer acceptance
- deployment success
- defect closure

Missing evidence remains `PENDING`, `NOT_AVAILABLE`, or `NOT_EXECUTED`. `BLOCKED` is a Gate or verification-result state, never an Evidence Status.

## Windows installation

From PowerShell in the extracted folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install-to-D.ps1
```

Default target:

```text
D:\codex-rd-platform
```

If the target is nonempty, the installer stops by default. `-Force` explicitly permits merge/overwrite and currently copies broad source contents; prefer working in a clean clone and running setup there. Do not target the source directory or its descendants.

Then:

```powershell
cd D:\codex-rd-platform
.\scripts\setup.ps1
```

`setup.ps1` requires an existing Git work tree with `user.name` and `user.email`, and Python 3.11 or newer. It creates or reuses `.venv`, installs only the version-constrained MCP requirements, runs `pip check`, creates `knowledge\local`, and runs the complete platform validator. It does not upgrade `pip` or write user-level environment variables by default.

For a repeat setup that reuses the existing dependencies:

```powershell
.\scripts\setup.ps1 -SkipDependencyInstall
```

`COMPANY_LOCAL_ROOTS` is set only for the setup process unless you explicitly request persistence:

```powershell
.\scripts\setup.ps1 -PersistLocalRoot
```

The repository starts in **template mode**. A successful platform-validator result in this mode confirms only that the reusable platform contracts are structurally valid. It does not mean any product project has started or that any G0–G11 Gate has passed. Start a project through G0 before creating an active Gate Register, requirement rows, or project evidence.

## Optional internal-system configuration

Store secrets as Windows environment variables; do not commit them.

Example:

```powershell
[Environment]::SetEnvironmentVariable("REDMINE_BASE_URL", "https://redmine.example.com", "User")
[Environment]::SetEnvironmentVariable("REDMINE_API_KEY", "<secret>", "User")

[Environment]::SetEnvironmentVariable("RAGFLOW_BASE_URL", "http://ragflow.example.com:30080", "User")
[Environment]::SetEnvironmentVariable("RAGFLOW_API_KEY", "<secret>", "User")
[Environment]::SetEnvironmentVariable("RAGFLOW_DATASET_ID", "<dataset-id>", "User")

[Environment]::SetEnvironmentVariable("GITLAB_BASE_URL", "https://gitlab.example.com", "User")
[Environment]::SetEnvironmentVariable("GITLAB_TOKEN", "<secret>", "User")
[Environment]::SetEnvironmentVariable("GITLAB_PROJECT_ID", "<numeric-id-or-urlencoded-path>", "User")
```

Open a fresh terminal after changing persistent user environment variables.

## Local knowledge

Default local context root:

```text
D:\codex-rd-platform\knowledge\local
```

You can configure multiple roots, separated by semicolons:

```powershell
[Environment]::SetEnvironmentVariable(
  "COMPANY_LOCAL_ROOTS",
  "D:\Knowledge;D:\Projects\Specs;\\server\share\docs",
  "User"
)
```

The MCP intentionally permits `read_local_doc` only under approved roots.

## First Codex run

Open `D:\codex-rd-platform` as the repository/workspace and ask:

```text
Read AGENTS.md.
Inspect the custom agents, repository skills, Git status and MCP availability.
Run the platform self-check.
Do not start a product project yet.
Report:
1. loaded orchestration rules;
2. available agents;
3. available skills;
4. MCP/tool status;
5. Git status;
6. missing configuration;
7. whether the platform is ready for an end-to-end trial.
```

Then start a project with a goal such as:

```text
Create a new project from this business idea.
Run the full lifecycle from G0 through G11.
Use specialized agents and parallelize independent research.
Persist every lifecycle artifact in Git.
Do not fabricate approvals or test evidence.
Stop/mark BLOCKED only where a real human decision or unavailable external evidence is required.
```

## RAGFlow note

RAGFlow API shapes can differ by version/deployment. The provided MCP uses a common `/api/v1/retrieval` pattern and is intentionally marked for contract validation before production use.

## Suggested first commit

```powershell
git add .
git commit -m "chore(platform): initialize Codex multi-agent R&D operating system"
```
