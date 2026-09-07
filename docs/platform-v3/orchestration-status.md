# Explain why a stage can or cannot advance

REQ-V3-008 / REQ-V3-021; TASK-V3-022; [CR-V3-005](CR-V3-005-host-stage-policy.md).

After `orchestrate-start`, inspect the existing project rather than starting it again:

```powershell
.\.venv\Scripts\python.exe -m rd_platform --db D:/your-control/state.db orchestrate-status --project-id PROJECT_ID --limit 200
```

```bash
.venv/bin/python -m rd_platform --db /your-control/state.db orchestrate-status --project-id PROJECT_ID --limit 200
```

Replace the example database and project ID with the actual bootstrap output. A missing database is rejected without creating a new one. The read-only projection runs in a consistent read transaction. It reports the effective current Gate, strict-policy presence, total count, page truncation and each work order's role, reason, input/output references and dependencies. The default page limit is 200 (1–500); use `lifecycle-collection work_orders` for further pages.

| Stage admission | Meaning | Next action |
| --- | --- | --- |
| `ALLOWED` | Stage prerequisites are current at read time. | Host must still validate actual worker identity, lease, configuration and retry safety during claim. |
| `WAITING_PREREQUISITE` | A predecessor Gate, dependency or current input is missing/stale. | Read `reason`; obtain actual evidence and the applicable independent decision or repair the affected input. |
| `NOT_READY` | Work is not READY or the lifecycle is paused/waiting/closed/failed. | Inspect the existing work/control history; resolve the condition before an explicit resume/retry. |

The result always contains `execution_authorized: false`: reading status never starts a worker, decides a Gate, signs acceptance or deploys. In particular, `ALLOWED` is not a capability token or a claim. Conditions may change after the snapshot and are rechecked in the mutating transaction.

The loopback board presents the same projection under **阶段工作与推进条件**. Its GET endpoint is `/api/orchestration?project_id=PROJECT_ID&limit=200`; repeated, unknown or invalid query fields fail. It adds no remote command, approval, deployment or model access.

## Verification

Developer RED: the command/module were absent (one failing assertion and one import error); the new HTTP route initially returned 404. The first implementation used a nonexistent Store connection helper; the focused tests caught it and the implementation now uses the existing `transaction(write=False)` contract. Current execution counts, independent checks and review belong in the delivery reports, not inferred from this guide.

This interface explains policy; it does not replace the actual specialist analysis or supply missing human/environment facts.
