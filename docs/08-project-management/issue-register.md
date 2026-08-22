# Issue Register

| Issue ID | Type | Summary | Impact | Owner | Status | Evidence |
|---|---|---|---|---|---|---|
| BUG-001 | Platform defect | 平台自检可能在 company_context MCP 启动失败及治理契约不完整时误报通过。 | 自动化、独立 retest 和 P2 re-review 已有 VERIFIED 证据；Codex 重启工具可见性仍缺失。 | NOT ASSIGNED | RESOLVED_PENDING_RESTART | [BUG-001 维护记录](../platform-maintenance/BUG-001-platform-self-check-false-positive.md); repair `ce9ca0e`; [test evidence](../platform-maintenance/test-evidence-2026-08-22.md); [initial review](../platform-maintenance/evidence/2026-08-22/20-independent-review-initial.md); [recheck](../platform-maintenance/evidence/2026-08-22/21-independent-review-recheck.md); [TC-002](../platform-maintenance/TC-002-codex-restart-validation.md) `NOT_EXECUTED` |
