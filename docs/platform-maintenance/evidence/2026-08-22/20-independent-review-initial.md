# 独立审查受控转录：初始审查

- Record Type: PLATFORM_MAINTENANCE_EVIDENCE
- Evidence ID: EVD-T8-REVIEW-INITIAL-20260822
- Recorder role: documentation manager
- Source role: independent reviewer
- Review target SHA: `2d3ae0a90fdf73d6e2f0494d7c02f18c5b0c2543`
- Branch: `codex/fix-BUG-001-platform-readiness`
- Source basis: independent reviewer final response retained by the Task 8 review loop; this is a controlled transcription, not a signature, approval, or new review.

## Scope and Verdict

The reviewer assessed BUG-001 / TASK-001 design conformance, manifest/runtime identity checks, MCP command containment and configuration invariants, Gate/RTM semantics, setup process behavior, test evidence and regression risks.

- Verdict: `NEEDS_FIXES`.
- Finding count: P0=0, P1=0, P2=5, P3=5.
- Impact: the five P2 findings blocked a clean independent-review conclusion for the target SHA. No project Gate, release, acceptance, deployment or human approval was issued.

## Findings

| Severity | Finding | Impact | Reviewer recommendation |
|---|---|---|---|
| P2 | Manifest/runtime duplicate identifiers can false-green because set comparison discards duplicates. | A duplicate manifest or runtime declaration can evade the intended exact-contract check. | Preserve the public set helpers if needed, but validate raw manifest and runtime declarations for uniqueness before set comparison and add regression coverage. |
| P2 | Canonical MCP containment does not prove rejection of a correctly laid-out external `.venv\\Scripts\\python.exe` junction target. | A command path that appears in-root can resolve outside the trusted repository boundary. | Resolve strictly from the canonical root, require canonical in-root command/server files and root cwd, and probe the actual configured layout. |
| P2 | `enabled`, `startup_timeout_sec` and `tool_timeout_sec` are not enforced as exact configuration invariants. | A configuration can silently violate runtime expectations while passing validation. | Require `enabled=true`, integer startup timeout `20`, and integer tool timeout `60`; add negative contracts. |
| P2 | Gate decision status/evidence semantics permit contradictory or unevidenced state combinations. | Active Gate records can imply unsupported decisions. | Require `DECIDED` for `PASS`/`FAIL`, externally resolvable evidence for every `DECIDED` row, and preserve only future `BLOCKED` plus `NOT_EVALUATED` placeholders. |
| P2 | `setup.ps1` does not restore caller cwd on every path. | A caller can be left in the repository/clone directory, compromising cleanup and caller behavior. | Enclose setup location change in `Push-Location` / `try` / `finally` / `Pop-Location` and exercise success and validator-failure paths in one PowerShell process. |
| P3 | The validator does not validate declared `requests` dependency bounds. | Installed consistency is checked, but validation does not enforce the declared bound. | Evaluate a separate hardening task and regression test. |
| P3 | Unicode text immediately after an ASCII placeholder, for example `PENDING状态`, may false-reject. | Legitimate prose can be rejected by placeholder parsing. | Define the intended Unicode boundary rule before changing behavior. |
| P3 | `runtime_executed` can be set after import before callable-resolution precision is established. | Internal status can overstate the exact runtime phase reached. | Decide the state semantics and add targeted callable-resolution coverage if needed. |
| P3 | A mutation helper writes before entering `try`. | A failure-path rollback/cleanup gap remains. | Review and test that helper in a separately scoped change. |
| P3 | Tester report cleanup/CLIXML explanation is stale or insufficiently bounded. | Historical setup cleanup and deserialization diagnostics can be overstated. | Preserve raw logs, distinguish historical facts from later controller cleanup, and avoid claiming an exclusive CLIXML cause without reproducible wrapper evidence. |

## Evidence and Boundary

- The initial independent tester command evidence is in [EVD-T8-TEST-20260822](../../test-evidence-2026-08-22.md).
- This transcription records all initial review findings and recommendations. It does not state that any finding was closed at this target.
- Codex restart/session visibility and Redmine/RAGFlow/GitLab external calls were not executed by this review.
