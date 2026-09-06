---
name: platform-orchestration
description: Develop or continue an application in this repository using its durable runtime and visible Agent board, from rough requirements through independently verified module delivery. Not for read-only audits or general software questions.
---

# Observable application development

Use the installed `rd_platform` CLI from this repository to make actual work visible. Read `docs/platform-v2/README.md` for commands and limitations, and `docs/superpowers/specs/2026-09-06-platform-v2-runtime-design.md` for Runtime payloads if needed. Do not make up tool names or assume a background model service is connected.

## Understand before asking

Read existing code, decisions and requirements before changing them. For a rough idea, produce a first model yourself: goal, users, workflow, data, permissions, failure cases, dependencies and acceptance criteria. Separate supplied facts from your inferences and unknowns. The CLI `discover` output is a baseline checklist, not a substitute for your reasoning.

Ask a small batch of the highest-impact questions, each with context, a recommendation, rationale and affected design. Use reversible defaults for ordinary implementation choices. Explicitly confirm decisions that materially change user intent, data access, cost or deployment scope. Persist the confirmed specification; do not treat generated DRAFT output as human approval.

## Record real work

1. Read `snapshot` before creating anything. Reuse the existing project/task IDs; do not restart finished work.
2. Register the actual host worker identities and roles. Create dependency-linked module tasks with Requirement IDs, reason and input references.
3. Before a worker acts, call `run.start` for its actual phase. Hand it the approved version, allowed files, acceptance criteria and run ID. Only claim a real host assignment after the host has accepted it.
4. Use actual host delegation tools for professional work. Keep development, independent testing and review identities distinct. A name alone is not proof of independence: retain host assignment and output evidence.
5. Update heartbeats at meaningful checkpoints; finish with actual output/evidence. A shell exit code proves process outcome, not full product acceptance. Include test counts and report paths. Never convert a missing test to PASS.
6. A failed run opens a defect; determine product/script/environment/spec responsibility, repair that cause, and retry within the task budget. Every new attempt repeats required checks. Do not close defects manually to make the board green.

## Controls and handoff

The board and CLI use the same state. Read controls before dispatching the next worker. Pause/modify invalidates active run results but does not terminate an external host process: use the actual host cancellation tool and report its outcome separately. Do not write late results into a new attempt.

The runtime enforces module quality phases, not full G0–G11 governance. Maintain applicable project Gate evidence separately. Produce requirements/design/test/report/release material continuously and link it to actual versions. Export `report` to distinguish executed, failed, blocked and unexecuted checks.

Before delivery run independent tests and review, show the user the application and unresolved limits, then commit/push only to the authorized target. Local module DONE does not authorize deployment, risk acceptance or human sign-off. Save lessons in the project repository; do not modify global personal memory without a separate request.
