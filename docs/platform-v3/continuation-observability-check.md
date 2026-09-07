# Continuation observability check

Requirement: REQ-V3-008 / REQ-V3-020. Observation: 2026-09-07, local browser.

The coordinator started the real loopback server using the existing `.rd-platform/state.db` and opened `http://127.0.0.1:8020/`. No project, task, approval or test evidence was synthesized for this check. The browser test used the accessibility tree first, following the repository testing and agentic-browser-testing guidance; this is one interactive host smoke, not a deterministic model benchmark or automated CI browser suite.

## TC-V3-OBS-022

- Goal: a user can identify the actual ongoing agents and their tasks and distinguish current work from completed history.
- Steps: open the local board; inspect Agent 状态 and the corresponding task cards; compare visible IDs, roles, current phase and version with current host assignments.
- Expected: the actual retry-fence and lifecycle-policy developers appear on their respective active implementation tasks; old tasks retain their earlier results; no new project Gate PASS is implied.
- Observed at local 14:25:25: `/root/completion_deployment` was WORKING on TASK-V3-016 revision 5 (`task-745d6a14cd6b460c90b4cff20692217f`); `/root/completion_policy` was WORKING on TASK-V3-021 (`task-41d3a56afca44a0bb290196bbd3a38a2`). TASK-V3-018 revision 4 showed 2/4 checks and integration next. The timeline retained the earlier TASK-V3-016 review FAIL and subsequent new implementation. These were the real host assignments, not demonstration workers.
- Result: PASS for this read-only rendered-state check. The page was left open as a deliverable.
- Limitation: the first selected historical V2 project had no V3 lifecycle and displayed “生命周期未就绪”; this is not a failed Gate. The Agent board reports registered quality runs/leases, not arbitrary host reasoning between runs. An IDLE row alone cannot prove the corresponding host agent process has exited. No control buttons were submitted on the active project during this check.

No API/model credentials, native WeChat run, human acceptance, release or production deployment are asserted by this observation.

## TC-V3-OBS-023 — strict stage table

TASK-V3-022 added `orchestrate-status` and the read-only loopback projection. A second server on port 8021 used a new clearly labelled temporary fixture database, not the existing project. The host called real `start_project`, then opened the page and inspected the rendered stage table.

The browser DOM assertion returned `{passed:true, rows:12, forbiddenGatePass:false}`: G0 displayed `READY / ALLOWED`; all eleven later stages displayed `WAITING_PREREQUISITE` with their preceding Gate IDs. The page displayed the actual role, purpose, input references, output references and preceding work IDs. The summary identified the strict policy and explicitly distinguished stage prerequisites from execution authorization. No Gate PASS appeared. The temporary browser tab was closed afterwards. This is coordinator UI verification; independent QA and review remain separate.

## Final-source server reload

After the TASK-V3-016 r9 / TASK-V3-021 r7 source freeze, the coordinator verified the exact command line of its own port-8020 server before stopping only that process. It restarted the same repository-local Python command against the same existing database. A fresh GET returned HTTP 200 and contained the stage-board section. This is a server reload/HTTP check, not another browser interaction test; the previous rendered-state observations remain timestamped above. No project data was deleted or reset. The desktop request to show this existing board returned `queued`, not proof that a hidden app window had displayed it.
