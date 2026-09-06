# Worker service / Worker 服务

Traceability: `TASK-V3-016`, `REQ-V3-016`, `DES-V3-003`, `CR-V3-004`.

Document state: `DRAFT`. `run_service(runtime, config, *, once=False, stop_event=None)` is a trusted-host dispatcher for Runtime work leases. It is not an HTTP execution endpoint, an approval provider, a multi-tenant sandbox, or a Gate decision.

## Security ruling / 安全裁定

A real isolated sentinel probe established that Codex auto-review could read and write outside its workspace under the same OS identity. Therefore the production `codex` backend is fail-closed rejected. Separating the control DB from a workspace remains good operational practice, but is **not** a model-isolation boundary. Do not re-enable Codex by adding `approval_mode`, `persist_session`, sandbox flags, or path separation.

The model-facing production path is a no-tools HTTPS Responses proposal transport. It sends `tools: []`, `tool_choice: "none"`, `store: false`, and a strict JSON schema. The model has no direct shell, filesystem, browser, MCP, or Runtime DB handle. `argv` remains available only as an already approved trusted-host command; it is not a sandbox for unknown code.

## Configuration / 配置

The top-level JSON object requires `project_id`, existing `repository_root`, and nonempty `workers`; `max_concurrency` is 1 through the worker count and `poll_interval_seconds` is finite. Every worker must have a previously registered `agent_id` whose role exactly matches one of the nine actual roles: `requirement_analyst`, `researcher`, `product_manager`, `architect`, `developer`, `tester`, `reviewer`, `documentation_manager`, or `release_manager`.

Each worker has finite `lease_seconds`, `timeout_seconds`, `max_output_bytes`, `safe_to_retry`, `source_paths`, and `backend`. `source_paths` defaults to `[]`, but a nonempty allowlist is required to publish a proposal. Its entries are confined, relative, non-control paths; every path that a proposal will create **or** update must appear in this list, including a path that does not exist yet. The host sends allowlisted existing files as UTF-8 bytes + SHA-256 and lists an allowlisted new path as `sha256:null, content:null`.

```json
{
  "project_id": "PROJECT_ID",
  "repository_root": "D:\\workspaces\\actual-project",
  "max_concurrency": 1,
  "poll_interval_seconds": 0.5,
  "workers": [{
    "agent_id": "host-developer", "role": "developer",
    "lease_seconds": 300, "timeout_seconds": 1200,
    "max_output_bytes": 65536, "safe_to_retry": false,
    "source_paths": ["src/app.py", "docs/implementation.md"],
    "backend": {
      "type": "responses", "model": "MODEL_ID",
      "api_key_env": "OPENAI_API_KEY",
      "endpoint": "https://api.openai.com/v1/responses",
      "max_output_tokens": 2048
    }
  }]
}
```

`api_key_env` names the host environment variable; never put its value in JSON, Git, evidence, or output. On the current host `OPENAI_API_KEY` is unavailable, so live Responses execution is `NOT_EXECUTED`. Existing transport/fixture tests do not prove a live model execution or production safety outcome.

`--once` performs one polling/dispatch pass. Without it, the process stays foreground-resident until its host stop event is set. It reaps expired leases, limits active claims to `max_concurrency`, heartbeats owned leases, and asks the bounded owned process to cancel when the service stops, lifecycle pauses, or the lease is invalidated. Reconcile actual process state: a pause or OS signal is not evidence of successful cancellation. An expired lease with unknown side effects is not retried unless `safe_to_retry:true` is explicit.

## Proposal admission / 提案准入

Responses must return exactly one structured object with `status`, `summary`, and `proposals`. A `DONE` Responses result requires at least one proposal. Each proposal contains exactly these seven fields:

```json
{
  "action": "update",
  "id": "CODE-APP-002",
  "type": "CODE_CHANGE",
  "title": "Apply bounded fix",
  "relative_path": "src/app.py",
  "content": "new UTF-8 content\\n",
  "expected_sha256": "SHA256_OF_CURRENT_src/app.py"
}
```

- `action:create` requires a new allowlisted path and `expected_sha256:null`.
- `action:update` requires an existing allowlisted regular file and the exact current lowercase SHA-256 in `expected_sha256`.
- An update uses a **new artifact ID**; it does not overwrite the previous artifact record, so Runtime keeps history.
- `relative_path` rejects absolute paths, traversal, `.git`, `.codex`, `.rd-platform`, symlinks, junctions, and other escape paths.
- `output_refs` is never a pass-through mechanism. A legacy envelope must use `output_refs:[]`; a Response proposal has no old-input/output-ref channel.

Before any write, the host validates the complete batch and prepares a durable journal. It applies creates/updates with CAS and atomic replacement, then creates hash-verified artifacts as `DRAFT` and finishes the work in one SQLite transaction. Any admission/DB failure rolls the whole uncommitted batch back; pause before admission creates no proposal file. If an OS failure occurs after the DB commit, the journal remains and next service startup proves the exact artifact refs before committing recovery; it does not silently discard or repeat bytes. A concurrent external change produces a CAS failure and is preserved.

Current host-side temporary-project evidence: `test_proposal_admission` covers create→update, full-batch rollback, pause-before-admission/no write, CAS conflict preservation, post-DB-commit recovery, cross-project separation and malformed recovery records. Exact current execution counts are in the independent test report; they are not live Responses, human approval, Gate, deployment or acceptance evidence.

Recovery journals bind the project, control DB, work ID and attempt. Recovery validates their root/path/digest structure and only reconciles the owning project. If an external actor has changed a file, recovery preserves those bytes, retains the journal and records a failed work with `recovery_required`; the operator must reconcile the conflict before restarting that project. Never delete journals to hide a recovery failure.

Responses cancellation/deadline bounds the calling worker, including a blocked connection. At most eight unfinished transport requests retain process-local slots; capacity exhaustion fails closed. A network request may remain active after local cancellation, so the observation reports `request_may_still_be_running:true`. This does **not** establish remote cancellation or stopped billing. Socket operations have at most 30 seconds of idle timeout; the configured total deadline applies separately. Do not blindly retry an unknown external outcome.
