---
name: platform-orchestration
description: Use when building or continuing an application with this repository's observable multi-agent lifecycle platform, including rough ideas and interrupted projects. Not for read-only audits or general software questions.
---

# Observable application development

Use the installed `rd_platform` CLI from this repository to make actual work visible. Read `docs/platform-v3/README.md` for current commands and limitations; read `docs/platform-v3/lifecycle-implementation.md` when using versioned artifacts, Gates or work leases. V2 module payloads remain documented in `docs/platform-v2/README.md`. Do not make up tool names or assume a background model service is connected.

## Understand before asking

Read existing code, decisions and requirements before changing them. For a rough idea, produce a first model yourself: goal, users, workflow, data, permissions, failure cases, dependencies and acceptance criteria. Separate supplied facts from your inferences and unknowns. The CLI `discover` output is a baseline checklist, not a substitute for your reasoning.

Ask a small batch of the highest-impact questions, each with context, a recommendation, rationale and affected design. Use reversible defaults for ordinary implementation choices. Explicitly confirm decisions that materially change user intent, data access, cost or deployment scope. Persist the confirmed specification; do not treat generated DRAFT output as human approval.

If the user delegates ordinary decisions (for example, “不用问我”), record assumptions and proceed within that scope. This removes repeated routine questions, not external authorization boundaries. Record an initial requirement model and a risk-based test model before implementing; select test points before cases. Each case identifies its Requirement, inputs, steps, observable expected result and execution method.

## Record real work

1. Read `snapshot` before creating anything. Reuse the existing project/task IDs; do not restart finished work.
2. Register the actual host worker identities and roles. Create dependency-linked module tasks with Requirement IDs, reason and input references.
3. For module development, call `run.start` for the actual phase before a worker acts. For verification-only work on existing code without a prior V2 implementation record, use V3 `work` and `test_execution` directly; a V2 module cannot start at unit. Keep the known source baseline and do not invent a developer to satisfy a missing phase. Hand over the version, allowed files, acceptance criteria and actual run/work ID. Only claim a host assignment after the host has accepted it.
4. Use actual host delegation tools for professional work. Keep development, independent testing and review identities distinct. A name alone is not proof of independence: retain host assignment and output evidence.
5. Update heartbeats at meaningful checkpoints; finish with actual output/evidence. A shell exit code proves process outcome, not full product acceptance. Include test counts and report paths. Never convert a missing test to PASS.
6. A failed run opens a defect. Reproduce using the actual input bytes and public interface before assigning product/script/environment/spec responsibility. A malformed test fixture is repaired by its test owner, not by weakening product validation. Preserve the original failure, repair its cause, then retry the full required phases within the task budget. A result recorded after execution must identify that late registration. Do not close defects manually to make the board green.

## Stack execution

Run `stack-probe` before choosing tools; read `docs/platform-v3/stack-harness.md` for manifest v1 and output rules. Choose available tools suited to the application rather than requiring one fixed framework. Keep build outputs under `{build}` for every phase (including Python test imports). `stack-run` executes trusted local argv; it is not a sandbox for arbitrary programs. Use `stack-package` only after source and secret exclusions are checked.

Developer tests, independent tests, browser operation, native runtime, load/stability runs and production deployment are separate evidence. A fake `wx` adapter cannot prove WeChat native execution; a compiler selector test cannot prove another OS was tested. Missing toolchains remain `NOT_AVAILABLE`, unrun checks `NOT_EXECUTED`. Read `docs/platform-v3/independent-app-tests.md` for the five-stack validation boundaries, not as approval for a new project.

## Controls and handoff

The board and CLI use the same state. Read controls before dispatching the next worker. Pause/modify invalidates active run results but does not terminate an external host process: use the actual host cancellation tool and report its outcome separately. Do not write late results into a new attempt.

V2 tasks enforce module quality phases. Initialize a V3 lifecycle only for an actual active project. Register versioned artifacts and typed trace links; create a test model before structured cases, and attach real execution evidence to exact subject versions. `lifecycle` reads G0–G11 evaluations, gaps and work orders; module DONE is not a Gate PASS. Assess before deciding a Gate, and invalidate impacted downstream evidence on material changes. Human approval uses the trusted operator channel only after an explicit, applicable human decision. Never generate approval evidence from an Agent identity.

Human approval is unavailable unless the host installs an authenticated approval provider; an operator name is not authentication. Use `lifecycle-report` for versioned test-case results and formal conclusions; `report` remains the separate V2 module-quality report. A new project needs its own acceptance evidence even when a prior example passed.

Produce requirements/design/test/report/release material continuously and link it to actual versions. Keep the repository template Gate register unpopulated; export active project facts separately. Read both `report` and `lifecycle` to distinguish module checks from lifecycle facts. When the host session ends, work leases and durable state support resumption but do not start a background model by themselves.

Before delivery run independent tests and review, show the user the application and unresolved limits, then commit/push only to the authorized target. Local module DONE does not authorize deployment, risk acceptance or human sign-off. Save lessons in the project repository; do not modify global personal memory without a separate request.
