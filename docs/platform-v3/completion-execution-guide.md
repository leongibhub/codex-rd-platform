# CR-V3-003 execution guide / 执行端使用指南

Traceability: `CR-V3-003` → `DES-V3-003` → `REQ-V3-016..020` →
`TASK-V3-016..020`.

Document state: `DRAFT`. This guide routes the implemented, trusted-host
interfaces; it is not a Gate decision, production runbook, approval record,
or release recommendation. The root [Chinese README](../../README.md#cr-v3-003-执行端受控使用当前实现待最终复审) and [English README](../../README.en.md#cr-v3-003-execution-endpoints-controlled-use-implemented-pending-final-review) contain the full end-to-end command and configuration examples.

## 1. Start and isolate / 启动与隔离

Use `orchestrate-start` only with a stable `--request-id`, a protected control
database outside the project workspace, and an existing `--repository-root`.
Repeating the same input is bootstrap-idempotent: it does not create a second
BG or a second G0–G11 work chain. Its result is `PLANNED`, never a test,
approval, Gate `PASS`, or release.

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db D:\rd-control\state.db orchestrate-start `
  --name 'Actual project name' --idea 'Actual supplied business goal' `
  --repository-root D:\workspaces\actual-project --request-id bootstrap-actual-001
```

`worker-service` validates that its `project_id` belongs to that exact
repository root. Keep the control DB separate for operational hygiene, but it
is **not** an OS/process isolation boundary: a confirmed Codex auto-review
probe read and rewrote a harmless sibling sentinel outside the workspace.
Production Codex backend use is therefore fail-closed disabled. Register every worker ID in that same control DB using
the actual role: `requirement_analyst`, `researcher`, `product_manager`,
`architect`, `developer`, `tester`, `reviewer`, `documentation_manager`, or
`release_manager`.

## 2. Worker backend schema / Worker 后端配置

The protected JSON configuration has `project_id`, `repository_root`,
`workers`, optional `max_concurrency` (1 through worker count), and optional
finite `poll_interval_seconds`. A worker has `agent_id`, exact `role`, finite
`lease_seconds`, `timeout_seconds`, `max_output_bytes`, `safe_to_retry`,
explicit `source_paths`, and a trusted `backend`. `source_paths` must list
every repository-relative path the model may create or update—even a new path;
an empty allowlist cannot write. Start one observable pass before a resident process:

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db D:\rd-control\state.db worker-service --config D:\rd-control\worker-service.json --once
```

Without `--once` it remains foreground-resident; supervise it with an approved
host/service manager. Reconcile actual processes with `work.reap` and
lifecycle facts on stop, pause, or invalidation. A pause or OS process signal
is not itself evidence that a child command stopped. An expired lease is not
replayed unless the trusted configuration explicitly sets `safe_to_retry:true`.

### Proposal backend / 提案后端

The current production-safe default is `backend.type:"responses"` with exact
fields `model`, `api_key_env`, optional trusted HTTPS `endpoint` (default
`https://api.openai.com/v1/responses`), and finite `max_output_tokens`
(1–16384; default 2048). The HTTP request fixes `tools:[]`,
`tool_choice:"none"`, `store:false`, and strict JSON schema output. The model
has no direct shell, filesystem, browser, MCP, or Runtime-database tool.

```json
{"agent_id":"host-developer","role":"developer","lease_seconds":300,"timeout_seconds":1200,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["src/app.py","docs/implementation.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}}
```

The model returns `status`, `summary`, and `proposals`; a `DONE` Responses
result needs a nonempty proposal list. Every proposal has exactly seven fields:
`action` (`create` or `update`), `id`, `type`, `title`, `relative_path`,
UTF-8 `content`, and `expected_sha256`. A create must target a new allowlisted
path with `expected_sha256:null`; an update must target an existing allowlisted
regular file with its exact current SHA-256 and use a **new artifact ID** so
history remains append-only. `output_refs` is not accepted as a pass-through
channel: it must be `[]` for a legacy envelope, and every new output must be
admitted in the current claim.

The host validates version-bound input content, complete allowlist and batch,
path/link restrictions, byte limits, and expected SHA-256; it journals the
batch, applies exclusive/CAS writes, hashes them, and registers only admitted
outputs as `DRAFT` in the same finish transaction. Admission/DB failure rolls
back the uncommitted batch; pause-before-admission writes nothing; a post-DB
commit journal is recovered only after exact artifact-ref proof. A proposal is
not VERIFIED evidence, an approval, a test result, or a Gate decision.

The current host has no `OPENAI_API_KEY`, so live Responses execution is
`NOT_EXECUTED`; no earlier Codex tests prove this new safety path. `argv`
remains permitted only for a pre-approved trusted-host command and is not an
unknown-code sandbox. The confirmed external-workspace sentinel finding means
production Codex/`auto-review` is fail-closed disabled; do not attempt to
recover it with `approval_mode`, `persist_session`, path separation, or flags.

## 3. Waiting for a human / 等待人工

Workers may return `WAITING_USER` for an actual material decision, external
approval, credential, or authority. `lifecycle.control resume` may make a
recoverable paused/waiting workflow eligible for a fresh claim after the human
has supplied the missing fact. Resume does **not** register a human approval,
change a Gate, certify a test, or turn an earlier model response into an
executed result. Preserve the reason and use the SSH approval flow where a
cryptographic Gate approval is really required.

## 4. Approval, deployment, and Linux routes / 审批、部署与 Linux 路由

1. `approval-challenge` writes exact canonical challenge bytes. A real human
   signs that file outside the platform with SSH Ed25519; `approval-register`
   verifies current scope/binding and records only that authenticated fact.
   Challenge creation is `WAITING_FOR_SIGNATURE`, not approval.
2. `deploy-run --action deploy|rollback` accepts only hash-pinned explicit
   argv, separate health and rollback-health commands, and durable receipts.
   `trial` remains outside release truth. `formal` additionally requires a
   READY release, current G10 `PASS`, a non-Agent operator, release-manager
   executor, deployment-environment evidence, and release evidence refs.
3. `scripts/setup.sh` is the Linux native path. The Task-V3-019 venv
   `--copies` correction is still under implementation/review. Do not report
   a target Linux install/MCP health PASS until the final script runs there
   with Python 3.11+ and the real validator succeeds.

For all three routes, do not put private keys, tokens, cookies, passwords, or
secret paths in JSON, Git, receipts, stdout/stderr, or documentation. A
fixture signature, test HTTP target, static script assertion, exit code zero,
or a disabled Codex approval mode never substitutes for a real approval, deployment,
rollback, acceptance, or Gate decision.
