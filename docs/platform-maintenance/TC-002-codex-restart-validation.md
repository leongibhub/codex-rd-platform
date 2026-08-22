# TC-002: Codex 重启后 MCP 工具可见性验证

- Record Type: PLATFORM_MAINTENANCE
- Test Case ID: TC-002
- Linked BUG: [BUG-001](BUG-001-platform-self-check-false-positive.md)
- Linked Task: [TASK-001](TASK-001-platform-readiness-repair.md)
- Execution Status: NOT_EXECUTED
- Result: NOT_EXECUTED

## Objective

在新的 Codex 会话中观察 `company_context` MCP 是否加载，并确认可见工具集精确为 8 项。当前会话和证据记录均不替代重启后的可见性观察。

## Preconditions

1. 已保留本仓库的实现、独立测试和复审证据；它们不证明新 Codex 会话已加载 MCP。
2. 不执行 Redmine、RAGFlow 或 GitLab 工具调用，也不暴露或推断凭据值。

## Procedure

1. 关闭 Codex 并重新打开工作区 `D:\codex-rd-platform`。
2. 在新会话中确认 `company_context` MCP 已加载；记录可见 UI 或终端证据的时间、工作区和会话观察方式。
3. 列出该服务器可用工具，不调用外部系统。
4. 核对工具名称、唯一性和总数必须精确为下列 8 项：

   - `get_gitlab_project`
   - `get_project_context`
   - `get_redmine_issue`
   - `ragflow_search`
   - `read_local_doc`
   - `search_gitlab_issues`
   - `search_local_docs`
   - `search_redmine`

5. 将可观察的原始输出或截图位置、时间、结果和任何错误更新至新的证据记录；未观察到时保持 `NOT_EXECUTED`，不要把本用例预填为通过。

## Completion Rule

只有新会话中的实际可见性证据可更新本用例。自动化 stdio 健康检查、静态验证或当前会话状态均不是本用例的执行证据。
