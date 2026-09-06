# Execution endpoints implementation plan

> For agentic workers: use the repository implementation/testing/code-review skills and subagent-driven-development. Each task has independent test and review before completion.

**Goal:** Complete runnable worker, authenticated approval, deployment and Linux setup adapters, and integrate their actual use into the platform Skill.

**Architecture:** Add adapters around existing public Runtime contracts. Preserve lifecycle truth and fail-closed gates. Local trusted operators own configuration; no anonymous remote command surface.

**Tech Stack:** Python >=3.11, SQLite, existing bounded process runner, Codex CLI, public-key signatures, native OS venv.

**Spec:** docs/platform-v3/completion-execution-design.md

## Global Constraints

- Python >=3.11. Do not edit lifecycle migration 1 or hash-locked Python lifecycle evidence.
- No fabricated approvals, execution results or production deployment.
- Independent developer, tester and reviewer. Additive APIs; preserve existing commands.
- Explicit argv, finite time/output/concurrency budgets, secrets excluded from Git.
- Shared checkout: do not revert another worker. Primary owns central CLI/web integration and commits.

## TASK-V3-016: Worker service

Files owned: rd_platform/worker_service.py, rd_platform/worker_backends.py, tests/runtime/test_worker_service.py. Runner cancellation extension, if needed, owned by this task only.

Interface: `run_service(runtime, config, *, once=False, stop_event=None) -> dict`. Config binds project/repository and workers with actual ID, role, backend and bounded execution settings. Consume work.create/claim/heartbeat/finish/control/reap. Produce public Runtime work/event facts and actual command result evidence. Codex backend must use installed CLI flags, not invent model APIs.

- [ ] Write negative tests for empty output, role mismatch, expired/invalidated lease and budget exhaustion; run RED.
- [ ] Implement config validation, ready queue dispatch, process execution, heartbeat/cancel, output contract and durable result handoff.
- [ ] Test actual subprocess, competing claims, pause, retry and restart using temporary DBs.
- [ ] Independent tester/reviewer validate; fix and retest before DONE.

## TASK-V3-017: Authenticated approval

Files owned: rd_platform/approval_provider.py, tests/runtime/test_approval_provider.py, docs/platform-v3/approval-provider.md.

Interface: provider implements existing `verify(binding=..., approval_request=...)`; add public helper to generate immutable challenge and accept signed response via trusted CLI. Public-key trust maps authorized operator/project/Gate; private key remains outside platform. Signature payload includes expiry and unique verification ID plus exact binding digest. Expose helpers to primary for CLI integration, without modifying cli.py.

- [ ] RED tests: valid fixture signature, wrong key, expiry, wrong binding, scope/identity and replay rejection.
- [ ] Implement strict signature/config/payload parser and provider; preserve Runtime default refusal.
- [ ] Execute fixture integration against Runtime.register_human_approval and current binding invalidation.
- [ ] Independent tester/reviewer validate; no fixture approval in real project DB.

## TASK-V3-018: Deployment execution

Files owned: rd_platform/deployment.py, tests/runtime/test_deployment.py, docs/platform-v3/deployment-executor.md.

Interface: `execute_deployment(runtime, config, *, action='deploy') -> dict`; config identifies project/environment, trusted argv/cwd/source hashes, health and compensation commands, role/operator, optional formal release ID. Only formal path can call release.record_deployment/rollback after existing gates. Trial deployment explicitly separate from release.

- [ ] RED: hash drift prevents launch, command success/health failure, failed compensation and unauthorized formal release.
- [ ] Implement bounded execution, append-only operation record, health verification and declared rollback. Interrupted operation cannot silently repeat destructive argv.
- [ ] Execute real isolated HTTP service deploy/check/failure/rollback; preserve receipts.
- [ ] Independent tester/reviewer validate before DONE.

## TASK-V3-019: Linux setup

Files owned: scripts/setup.sh, tests/platform/test_linux_setup.py, docs/platform-v3/linux-setup.md. Existing write_local_config.py only if necessary, coordinated with primary.

- [ ] RED: no Git identity, wrong Python version, repeat installation and MCP health failure behavior.
- [ ] Implement bash launcher reusing config generator and validator; no sudo/global config edits/data deletion.
- [ ] Run on actual WSL/Linux and record interpreter/health, not platform-selector-only tests.
- [ ] Independent tester/reviewer validate before DONE.

## TASK-V3-020: Integration and user delivery

Files owned by primary: cli.py/web.py/static, documentation indexes/README.md/README.en.md and platform-orchestration Skill. Dependency: 016/017/018/019 public interfaces.

- [ ] Wire service/approval/deploy CLI commands; show real work and actual controls, no anonymous command execution.
- [ ] Update both README guides with install/start/configure/control/recover examples and honest execution domains.
- [ ] Execute real Codex-backed bounded project task, independent module verification and five-stack existing app regressions.
- [ ] Run full regression/independent review, commit with requirement/task references and push authorized branch; verify remote CI.

## Coordination ledger

Preflight: tasks 016/017/018 expose independent modules consumed by 020; shared CLI belongs solely to 020. Task019 uses existing config generator, no conflict with execution endpoints. All tasks agree with source preservation and real evidence constraints.

Ruling: user has delegated ordinary design decisions; do not pause for routine design approval. AGENTS.md explicitly asks independent parallel work, so nonoverlapping subsystem implementation may proceed concurrently; shared integration remains serial. No approval or terminal test result is implied by this ruling.

Current status: design and plan recorded; implementations NOT_EXECUTED.

Historical planning status above is retained. Current implementation, failure/retry and test facts are recorded in [completion-execution-delivery.md](completion-execution-delivery.md), [CR-V3-004](CR-V3-004-safe-model-execution.md), and the independent test/review reports. The original Codex-backend plan is superseded by the explicitly documented safe proposal transport decision; unchecked planning boxes are not execution evidence.
