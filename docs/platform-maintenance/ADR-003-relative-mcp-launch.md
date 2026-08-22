# ADR-003: 使用相对路径启动平台 MCP

- Record Type: PLATFORM_MAINTENANCE
- Status: ACCEPTED_FOR_IMPLEMENTATION
- Decision Date: 2026-08-22
- Linked BUG: [BUG-001](BUG-001-platform-self-check-false-positive.md)
- Linked Task: [TASK-001](TASK-001-platform-readiness-repair.md)
- Design Source: [平台就绪性修复设计](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md)
- Implementation / Test Status: NOT EXECUTED

## Context

平台 MCP 配置需要在不同安装目录中可移植，同时仍限制 validator 只能启动位于仓库根或仓库 `.venv` 下的受信任命令和脚本。

## Decision

`.codex/config.toml` 的 MCP `command`、`args` 和 `cwd` 使用项目根相对路径。配置保留 20 秒启动超时和 60 秒工具超时，增加受文档化环境变量名称的转发，并将平台核心 MCP 标记为 `required = true`。密钥不得写入 TOML、仓库文件、测试输出或日志。

## Alternatives Considered

| Alternative | Disposition | Rationale |
|---|---|---|
| 固定绝对安装路径 | Not selected | 破坏项目目录可移植性。 |
| 不限制解析后的启动目标 | Not selected | 无法满足受信任路径和进程启动边界。 |

## Consequences and Risks

- 配置解析、相对路径解析和路径边界需要由运行时健康检查覆盖。
- `env_vars`、`required` 和 `cwd` 的实际运行效果尚待后续实现与验证。
- 本任务不执行 MCP 启动或外部系统访问。

## Evidence

- Decision basis: 已批准设计第 6.2、7.2 和 12 节。
- Implementation evidence: NOT EXECUTED.
- Test evidence: NOT EXECUTED.
- Independent review evidence: NOT EXECUTED.
