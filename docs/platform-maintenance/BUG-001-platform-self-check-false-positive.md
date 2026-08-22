# BUG-001: 平台自检误报通过

- Record Type: PLATFORM_MAINTENANCE
- Status: OPEN
- Severity: BLOCKER
- Maintenance Scope: 平台骨架就绪性修复；不启动产品项目。
- Affected Baseline: `7b7198f` (`chore(platform): initialize Codex R&D operating system`)
- Linked Task: [TASK-001](TASK-001-platform-readiness-repair.md)
- Linked Design: [平台就绪性修复设计](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md)
- Repair / Regression Test Execution Status: NOT EXECUTED

## Observed Behavior

已批准设计记录了以下平台就绪性问题：

1. `tools/mcp/company-context/server.py` 使用 MCP SDK v1 的 `FastMCP` 导入路径；设计所述运行环境安装 MCP 2.0.0 时，服务启动出现 `ModuleNotFoundError`。
2. `scripts/validate_platform.py` 只检查文件存在和少量 TOML 字段；即使 MCP 服务不能启动、manifest 不一致或 Gate/RTM 契约不完整，仍可能输出成功状态，形成假阳性。
3. 修复前 Git 原仓库未被当前用户信任且没有提交基线，不能作为工程事实源；`7b7198f` 是本维护记录引用的原始基线提交。

下列命令已由控制器在本任务工作树中复现并提供脱敏输出；它们是故障观察证据，不是修复、回归或独立验证结果。后续修复检查仍为 `NOT EXECUTED`。

## Observed Reproduction Evidence

- Observation Date: 2026-08-22
- Observation Scope: 修复前平台基线行为；不代表 BUG-001 已修复或已验证。

| Evidence ID | Exact Command | Exit Code | Concise Sanitized Output | Observation Status |
|---|---|---:|---|---|
| EVD-BUG-001-05 | `D:\codex-rd-platform\.venv\Scripts\python.exe scripts\validate_platform.py` | 0 | `PLATFORM VALIDATION: PASS`; `Agents: 9`; `Skills: 13`; `Docs/Templates: 108` | OBSERVED |
| EVD-BUG-001-06 | `D:\codex-rd-platform\.venv\Scripts\python.exe tools\mcp\company-context\server.py` | 1 | `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` at `server.py` line 10 | OBSERVED |

EVD-BUG-001-05 demonstrates the false-green condition: the validator exited 0 while EVD-BUG-001-06 demonstrates that the configured MCP server could not import and start. No credentials, tokens, cookies, authorization values, or external-service output were included.

## Expected Behavior

平台自检必须在真实 MCP stdio 健康检查和静态治理契约检查完成后，才报告模板模式就绪状态。Git 必须有可解析的基线；模板模式不得产生任何产品项目 Gate 结论。

## Evidence

| Evidence ID | Source | Recorded Fact | Execution Status |
|---|---|---|---|
| EVD-BUG-001-01 | [平台就绪性修复设计](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md) | 设计第 1 节记录 `ModuleNotFoundError`、validator 假阳性和 Git 基线问题。 | NOT EXECUTED |
| EVD-BUG-001-02 | Git commit `7b7198f` | 原始平台骨架基线提交。 | NOT EXECUTED |
| EVD-BUG-001-03 | `tools/mcp/company-context/server.py` at `7b7198f` | 包含 `from mcp.server.fastmcp import FastMCP`。 | NOT EXECUTED |
| EVD-BUG-001-04 | `scripts/validate_platform.py` at `7b7198f` | 仅执行文件、TOML 和 Skill 数量检查并打印验证结果。 | NOT EXECUTED |
| EVD-BUG-001-05 | 控制器故障复现输出（2026-08-22） | 参见上方“Observed Reproduction Evidence”的 validator 命令与输出。 | OBSERVED |
| EVD-BUG-001-06 | 控制器故障复现输出（2026-08-22） | 参见上方“Observed Reproduction Evidence”的 server 命令与输出。 | OBSERVED |

## Impact

平台可能将不可启动的公司上下文 MCP 和不完整的治理契约表示为可用，后续项目工作无法以该自检结果作为可信前置条件。

## Root Cause

PENDING：根因分析和验证由 TASK-001 后续实现、独立测试与审查记录提供；本任务不宣称根因已确认。

## Planned Correction

按 [TASK-001](TASK-001-platform-readiness-repair.md) 实施 MCP SDK v2 原生迁移、真实 stdio 健康检查、Git/manifest/Gate/RTM 契约验证和 Windows setup fail-closed 行为。

## Regression and Closure Evidence

- Automated regression execution: NOT EXECUTED
- Independent tester result: NOT EXECUTED
- Independent reviewer result: NOT EXECUTED
- Codex restart tool-visibility verification: NOT EXECUTED
- Closure basis: NOT AVAILABLE

BUG-001 在上述证据实际产生并满足设计中的关闭条件前保持 `OPEN`。
