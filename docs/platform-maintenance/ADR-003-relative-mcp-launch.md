# ADR-003: 使用参数化绝对路径启动平台 MCP

- Record Type: PLATFORM_MAINTENANCE
- Status: ACCEPTED_FOR_IMPLEMENTATION
- Decision Date: 2026-08-22
- Revised Date: 2026-08-25
- Linked BUG: [BUG-001](BUG-001-platform-self-check-false-positive.md)
- Linked Task: [TASK-001](TASK-001-platform-readiness-repair.md)
- Design Source: [平台就绪性修复设计](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md)
- Implementation Status: IMPLEMENTED
- Evidence Status: VERIFIED
- Restart Evidence Status: NOT_EXECUTED

## Revision History

- 2026-08-22：初始决策使用项目根相对路径启动 MCP，以追求安装目录可移植性。
- 2026-08-25：决策修订。真实 Codex 运行时会按自身工作目录解析相对 `cwd`，不保证等于仓库根，导致核心 MCP 在任意启动目录下无法可靠拉起。改为由安装/校验脚本基于仓库根参数化生成绝对路径，不再手写死路径。

## Context

平台 MCP 配置需要在当前安装目录下可靠启动，同时仍限制 validator 只能启动位于仓库根或仓库 `.venv` 下的受信任命令和脚本。绝对路径必须由仓库根派生生成，避免换目录或换机后残留手写死路径。

## Decision

`.codex/config.toml` 的 MCP `command`、`args` 和 `cwd` 使用基于仓库根的绝对路径，并由 `scripts/write_local_config.py`（在 `scripts/setup.ps1` 中调用）从仓库根参数化生成，而不是手写固定字符串。配置保留 20 秒启动超时和 60 秒工具超时，增加受文档化环境变量名称的转发，并将平台核心 MCP 标记为 `required = true`。密钥不得写入 TOML、仓库文件、测试输出或日志。

## Alternatives Considered

| Alternative | Disposition | Rationale |
|---|---|---|
| 参数化生成绝对路径（基于仓库根） | Selected | 在当前安装目录下可靠启动，且由脚本派生，避免手写死路径漂移。 |
| 项目根相对路径 | Not selected（修订后） | Codex 运行时按自身工作目录解析相对 `cwd`，不保证等于仓库根，核心 MCP 无法可靠拉起。 |
| 手写固定绝对安装路径 | Not selected | 换目录或换机后成为不可移植的死路径，且无生成来源可追溯。 |
| 不限制解析后的启动目标 | Not selected | 无法满足受信任路径和进程启动边界。 |

## Consequences and Risks

- 配置解析、绝对路径解析和路径边界需要由运行时健康检查覆盖。
- 绝对路径必须始终由 `scripts/write_local_config.py` 从仓库根生成；直接手改路径会破坏可追溯性，需视为漂移。
- `env_vars`、`required`、`cwd` 和受信任路径的验证已有执行证据；新会话 Codex 工具可见性仍为 `NOT_EXECUTED`。
- 本任务不执行外部系统访问。

## Evidence

- Decision basis: 已批准设计第 6.2、7.2 和 12 节；2026-08-25 修订由运行时启动可靠性驱动。
- Implementation evidence: repair commit `ce9ca0e`; see [TASK-001](TASK-001-platform-readiness-repair.md). 2026-08-25 revision adds parameterized generation and absolute launch paths.
- Test evidence: [EVD-T8-TEST-20260822](test-evidence-2026-08-22.md) records P2 config contracts and a correct-layout external junction rejected as `MCP_COMMAND_UNTRUSTED`.
- Independent review evidence: [EVD-T8-REVIEW-20260822](review-evidence-2026-08-22.md) records the P2 re-review and the remaining command-junction fixture P3.
- Pending: [TC-002](TC-002-codex-restart-validation.md) is `NOT_EXECUTED`; no external Redmine/RAGFlow/GitLab call was executed.