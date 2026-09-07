# Orchestration status independent verification

- Scope: `REQ-V3-008`, `REQ-V3-021`, `TASK-V3-022`, and `CR-V3-005` read-only status surface.
- Tester: `/root/completion_qa`, independent from implementation.
- Environment: temporary local SQLite databases and repository directories; public CLI and loopback HTTP only. No project Gate, production deployment, external model call, or human approval was used.

## Independent cases and evidence

| Case | Risk / observable check | Result |
| --- | --- | --- |
| TC-V3-022-IND-01 | `orchestrate-status` on an existing strict bootstrap preserves the exact SQLite hash, returns `execution_authorized:false`, reports G0 `ALLOWED`, and reports every later work order `WAITING_PREREQUISITE`. A missing DB is rejected without being created. | PASS — integration `run-0c62748dc55145178d2a536741aaa4b3`, 2.598508 s. |
| TC-V3-022-IND-02 | `/api/orchestration` refuses repeated `limit`, unknown raw-query fields, and an invalid `Host`. | PASS — same integration; each returned HTTP 400 with an error payload. |
| TC-V3-022-IND-03 | A legacy lifecycle instance without strict bootstrap policy retains direct role-matched work claim behavior. | PASS — same integration; public `command work.claim` returned the legacy work ID. |

The registered unit command was `python -m unittest -v tests.runtime.test_orchestration_policy tests.runtime.test_policy_cli`: `run-1fcb48334b93413cb3229cb97e430426`, 7/7 PASS in 3.765 s. It is recorded as the task unit phase but is not substituted for the independent cases above.

Fixture history: the first black-box observation asserted `strict_policy == "orchestration-v1"`; the actual public projection correctly returned boolean `true`, while the requirement promises policy presence rather than that internal label. The test expectation was narrowed to presence/true, then the complete independent command was rerun and registered. This is a tester-fixture error, not a product defect.

## Decision boundary

This scoped result supports only the public status CLI/HTTP contract above. It does not establish rendered board accessibility, a Gate decision, lifecycle completion, human acceptance, release, or production operation.
