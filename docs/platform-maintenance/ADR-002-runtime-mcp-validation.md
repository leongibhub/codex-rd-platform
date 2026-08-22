# ADR-002: 平台自检使用真实 MCP stdio 健康检查

- Record Type: PLATFORM_MAINTENANCE
- Status: ACCEPTED_FOR_IMPLEMENTATION
- Decision Date: 2026-08-22
- Linked BUG: [BUG-001](BUG-001-platform-self-check-false-positive.md)
- Linked Task: [TASK-001](TASK-001-platform-readiness-repair.md)
- Design Source: [平台就绪性修复设计](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md)
- Implementation / Test Status: NOT EXECUTED

## Context

现有 validator 仅做文件和少量配置检查，不能证明 MCP 进程可以启动或满足工具契约，因此可能产生假阳性。

## Decision

默认平台自检在静态契约检查之外，解析受信任的 `.codex/config.toml` 中 `command`、`args` 和 `cwd`，确认目标位置受限于仓库预期路径后，通过 MCP v2 客户端完成：

1. 启动实际 stdio 子进程；
2. 完成协议协商；
3. 调用 `tools/list`；
4. 核对 8 个工具的名称、唯一性、描述和对象型输入 schema；
5. 在 15 秒总预算内结束并回收进程树。

健康检查不调用外部工具，也不依赖外部凭据。`--static-only` 仅供诊断，必须表明运行时检查为 `NOT EXECUTED`。

## Alternatives Considered

| Alternative | Disposition | Rationale |
|---|---|---|
| 仅保留静态文件和 TOML 检查 | Not selected | 不能发现实际 MCP 启动、协议或工具集故障。 |

## Consequences and Risks

- 验证器需要稳定错误分类、超时处理和子进程清理。
- stdio 启动和工具契约结果仍待后续执行证据确认。
- 外部 Redmine、RAGFlow、GitLab 工具调用不属于健康检查范围。

## Evidence

- Decision basis: 已批准设计第 7.2 和第 7.3 节。
- Implementation evidence: NOT EXECUTED.
- Test evidence: NOT EXECUTED.
- Independent review evidence: NOT EXECUTED.
