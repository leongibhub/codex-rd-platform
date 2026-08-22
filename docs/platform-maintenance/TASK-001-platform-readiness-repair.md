# TASK-001: 平台就绪性修复

- Record Type: PLATFORM_MAINTENANCE
- Execution Status: NOT EXECUTED
- Linked BUG: [BUG-001](BUG-001-platform-self-check-false-positive.md)
- Design Source: [平台就绪性修复设计](../superpowers/specs/2026-08-22-platform-readiness-repair-design.md)
- Implementation Plan: [平台就绪性修复实施计划](../superpowers/plans/2026-08-22-platform-readiness-repair.md)
- Baseline: `7b7198f`
- Worktree / Branch: `.worktrees/platform-readiness` / `codex/fix-BUG-001-platform-readiness`
- Scope Boundary: 平台维护；不启动产品项目，不创建产品目标、需求或项目 Gate 结论。

## Goal

修复 Git 基线、MCP SDK v2 兼容、平台自检、Gate/RTM 治理和 Windows setup 可靠性，使平台能够可信地报告模板模式就绪状态。

## Planned Tasks

| Plan Task | Planned Work | Initial Execution Status |
|---|---|---|
| Task 1 | 建立平台维护追踪记录。 | NOT EXECUTED |
| Task 2 | 用 TDD 建立 manifest 契约。 | NOT EXECUTED |
| Task 3 | 用 TDD 迁移 MCP v2 并封闭本地路径。 | NOT EXECUTED |
| Task 4 | 用 TDD 建立真实 stdio 健康检查和 Codex 配置。 | NOT EXECUTED |
| Task 5 | 用 TDD 补齐 Gate 与 RTM 治理契约。 | NOT EXECUTED |
| Task 6 | 用 TDD 重构完整平台 validator。 | NOT EXECUTED |
| Task 7 | 用测试强化 Windows setup。 | NOT EXECUTED |
| Task 8 | 全量验证、证据固化与独立 Gate。 | NOT EXECUTED |

## Acceptance Conditions

以下条件来自已批准设计；本记录不将其表述为已达到的结果。

1. 普通 Git 命令可用，`main` 有原始基线，修复在独立分支完成。
2. 完整自动化测试全部通过，无未预期警告或遗留 MCP 子进程。
3. `validate_platform.py` 在实际 MCP stdio 健康检查后返回退出码 0，报告模板模式，且不报告任何项目 Gate 通过。
4. 故意破坏 manifest、MCP 导入、工具列表、Gate 模板或 RTM 表头时，validator 返回退出码 1 和明确错误分类。
5. `search_local_docs` 不能读取批准根外文件。
6. Gate 模板覆盖 G0–G11，RTM 覆盖验收、CR、独立验证、缺陷处置和 Release。
7. setup 重复执行不静默写入用户级密钥或 Git 配置，失败时不输出成功。
8. tester 与 reviewer 均无未解决 P0/P1 发现。
9. 新 Codex 会话中可见 8 个 `company_context` 工具；未配置的 Redmine、RAGFlow、GitLab 项明确记录为 `NOT EXECUTED`。

## Required Evidence and Current State

| Evidence Area | Required Evidence | Current State |
|---|---|---|
| Unit and contract tests | 失败测试、最小修复后的自动化结果。 | NOT EXECUTED |
| MCP runtime | stdio 启动、协议协商和严格 8 工具列表证据。 | NOT EXECUTED |
| Validator | 完整 validator 成功路径和故障注入结果。 | NOT EXECUTED |
| Setup | Windows PowerShell 前置检查和重复执行证据。 | NOT EXECUTED |
| Independent test | tester 的独立验证记录。 | NOT EXECUTED |
| Independent review | reviewer 的缺陷、风险和一致性结论。 | NOT EXECUTED |
| Codex restart | 新会话运行时工具可见性观察。 | NOT EXECUTED |

## Traceability

`BUG-001` → `TASK-001` → `ADR-001` / `ADR-002` / `ADR-003` → 后续变更提交与测试证据（均待执行）。

## Constraints

- 每个后续提交必须引用 `BUG-001`、`TASK-001` 和实际测试命令。
- 不记录密钥、Token、Cookie 或 Authorization 值。
- 在真实测试、独立审查和重启验证有证据之前，不改变 BUG-001 状态。
