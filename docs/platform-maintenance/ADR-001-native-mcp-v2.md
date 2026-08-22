# ADR-001: 原生迁移 company_context 至 MCP SDK v2

- Record Type: PLATFORM_MAINTENANCE
- Status: ACCEPTED_FOR_IMPLEMENTATION
- Decision Date: 2026-08-22
- Linked BUG: [BUG-001](BUG-001-platform-self-check-false-positive.md)
- Linked Task: [TASK-001](TASK-001-platform-readiness-repair.md)
- Design Source: [平台就绪性修复设计](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md)
- Implementation Status: IMPLEMENTED
- Evidence Status: VERIFIED
- Restart Evidence Status: NOT_EXECUTED

## Context

已批准设计指出，当前服务使用 MCP SDK v1 的 `FastMCP` 导入路径，而目标环境安装 MCP 2.0.0，导致启动失败。平台尚未发布需要保持 MCP v1 稳定 API 的接口。

## Decision

后续实现使用 MCP SDK v2 的 `MCPServer` 原生接口：

```python
from mcp.server import MCPServer

mcp = MCPServer(name="company-context", version="0.2.0")
```

依赖约束将采用 `mcp>=2.0.0,<3.0.0` 和 `requests>=2.31.0,<3.0.0`。既有工具行为保持在设计定义的 8 个工具范围内。

## Alternatives Considered

| Alternative | Disposition | Rationale |
|---|---|---|
| 同时兼容 MCP v1/v2 | Not selected | 扩大测试矩阵并保留长期维护分支。 |
| 回退 MCP v1 | Not selected | 继续依赖旧主版本并推迟迁移。 |

## Consequences and Risks

- 需要以失败测试、MCP 导入/实例化和 stdio 集成测试证明迁移正确性。
- 已记录 MCP v2 stdio、精确工具集和 `pip check` 的执行证据；新会话 Codex 工具可见性仍未执行。
- 实现或验证失败时保留原始基线，不以降级依赖掩盖失败。

## Evidence

- Decision basis: 已批准设计第 4.1 至 4.3 节。
- Implementation evidence: repair commit `ce9ca0e`; see [TASK-001](TASK-001-platform-readiness-repair.md).
- Test evidence: [TC-001](TC-001-platform-automated-validation.md) and [EVD-T8-TEST-20260822](test-evidence-2026-08-22.md) record `ce9ca0e` full-suite, pip, validator and actual stdio evidence.
- Independent review evidence: [EVD-T8-REVIEW-20260822](review-evidence-2026-08-22.md) records initial `NEEDS_FIXES` and P2 closure in directed re-review.
- Pending: [TC-002](TC-002-codex-restart-validation.md) remains `NOT_EXECUTED`; external Redmine/RAGFlow/GitLab calls are `NOT_EXECUTED`.
