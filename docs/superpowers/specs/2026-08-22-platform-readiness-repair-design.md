# 平台就绪性修复设计

- 文档状态：IN_REVIEW
- 维护类型：平台缺陷修复，不启动产品项目
- 关联缺陷：BUG-001 平台自检误报通过
- 关联任务：TASK-001 平台就绪性修复
- 设计日期：2026-08-22

## 1. 背景与问题

平台骨架包含 9 个自定义 Agent、13 个仓库 Skill、G0–G11 生命周期规则和 101 份 Markdown 文档，但当前存在四类阻塞问题：

1. Git 原仓库不受当前用户信任、没有提交基线，无法作为工程事实源。
2. `company_context` 使用 MCP Python SDK v1 的 `FastMCP` 导入路径，而环境安装了 MCP 2.0.0，服务启动失败。
3. `validate_platform.py` 只检查文件存在和少量 TOML 字段，MCP 启动失败、manifest 不一致、Gate 与 RTM 不完整时仍报告 PASS。
4. Gate 状态与证据规则分散，G3–G6、G8–G9 没有统一决策记录；RTM 缺少验收、变更和独立验证字段。

本修复只提升平台骨架的可运行性、可审计性和自检可信度。所有产品目标、需求、测试结果、批准和 Gate 结论继续保持未建立或未执行状态。

## 2. 目标

1. 普通 Git 命令可用，并保留修复前基线与独立修复分支。
2. `company_context` 在 MCP Python SDK 2.x 下通过 stdio 启动并精确暴露 8 个工具。
3. 默认平台自检必须执行静态契约检查、Git 基线检查和真实 MCP stdio 健康检查。
4. 平台模板模式与活动项目模式严格区分，模板默认文本不得成为项目证据。
5. 建立唯一 Gate 状态来源和完整 RTM 数据契约，为后续 G0–G11 试运行提供机器可检查的基础。
6. 所有新增行为均先有失败测试，再实施最小修复，并由独立 tester 与 reviewer 验证。

## 3. 非目标

- 不创建产品愿景、PRD、REQ/NFR 或项目 Gate 结论。
- 不调用 Redmine、RAGFlow 或 GitLab，也不要求外部系统凭据。
- 不宣称任何测试、发布、部署或客户验收已经完成。
- 不实现通用 MCP v1/v2 双版本兼容层。
- 不重构与本次故障无关的外部 HTTP 业务逻辑。

## 4. 方案选择

### 4.1 采用：原生迁移到 MCP SDK v2

`server.py` 使用：

```python
from mcp.server import MCPServer

mcp = MCPServer(name="company-context", version="0.2.0")
```

现有 `@mcp.tool()` 和 `mcp.run(transport="stdio")` 接口保持不变。依赖约束调整为：

```text
mcp>=2.0.0,<3.0.0
requests>=2.31.0,<3.0.0
```

选择原因：MCP 2.x 是当前稳定主版本，官方迁移说明明确将 `FastMCP` 重命名为 `MCPServer`；主版本上界可防止未来再次无意跨越破坏性版本。

### 4.2 不采用：同时兼容 MCP v1/v2

兼容导入可以短期工作，但会扩大测试矩阵并长期保留维护分支。本平台尚未发布需要兼容 v1 的稳定 API，因此不增加该复杂度。

### 4.3 不采用：回退 MCP v1

固定 `<2` 可快速恢复旧代码，但会继续依赖维护版本，并推迟不可避免的迁移。

## 5. Git 与隔离策略

1. 将仓库加入当前用户 Git `safe.directory`。
2. 仅在仓库本地配置用户批准的 Git 作者信息。
3. 初始分支规范为 `main`，先提交未经修复的平台原始基线。
4. 在 `.worktrees/platform-readiness` 创建 `codex/fix-BUG-001-platform-readiness` 分支。
5. 修复提交必须包含 `BUG-001`、`TASK-001` 和测试引用。
6. 独立测试与审查通过后，使用非快进合并回 `main`；不直接在 `main` 开发。

## 6. MCP 与 Codex 配置

### 6.1 服务契约

`company_context` 必须通过 stdio 暴露且仅暴露以下工具：

```text
get_gitlab_project
get_project_context
get_redmine_issue
ragflow_search
read_local_doc
search_gitlab_issues
search_local_docs
search_redmine
```

外部环境变量缺失时，服务仍应启动；相关工具返回结构化“未配置”错误，不发起网络请求。

### 6.2 项目配置

`.codex/config.toml` 保持安装目录可移植性，命令、参数和 `cwd` 使用项目根相对路径。配置增加：

- `env_vars`：只转发文档化的本地、Redmine、RAGFlow、GitLab 环境变量名称。
- `required = true`：平台核心 MCP 无法启动时，Codex 应显式失败。
- 启动和工具超时继续分别使用 20 秒和 60 秒。

密钥不写入 TOML、仓库文件、测试输出或日志。

### 6.3 本地知识目录

仓库增加 `knowledge/local/README.md`，使默认批准根真实存在，并说明这里只存放允许进入 Git 的非敏感知识。私密资料通过 `COMPANY_LOCAL_ROOTS` 指向仓库外目录。

### 6.4 路径安全

`search_local_docs` 与 `read_local_doc` 共用同一 approved-root 判断。每个候选文件必须 `resolve()` 后再次确认位于批准根内，阻止符号链接或重解析点越界读取。

## 7. 自检架构

### 7.1 静态检查

`validate_platform.py` 负责：

- 解析并验证 `platform-manifest.json`。
- manifest Agent ID 与 TOML `name` 精确一致。
- manifest Skill 与 `SKILL.md` frontmatter 精确一致。
- Gate 集合必须精确为 G0–G11。
- 关键文档、Gate 模板和 RTM 表头必须满足契约。
- Python 版本至少为 3.11；MCP 版本必须在 `[2.0.0, 3.0.0)`。
- Git 仓库必须存在可解析的 HEAD；工作区不干净只报告警告，严格模式才失败。

### 7.2 真实 MCP 健康检查

默认自检从 `.codex/config.toml` 解析受信任的 `command`、`args` 与 `cwd`，确认目标位于仓库预期位置后，通过 MCP v2 客户端：

1. 启动实际 stdio 子进程；
2. 完成协议协商；
3. 调用 `tools/list`；
4. 核对 8 个工具的名称、唯一性、描述和对象型输入 schema；
5. 在 15 秒总预算内结束并回收进程树。

健康检查不调用任何外部工具，不依赖外部凭据或网络。

### 7.3 输出与退出码

- 全部静态和运行时检查通过：`PLATFORM VALIDATION: PASS (TEMPLATE MODE)`，退出码 0。
- 任一必需检查失败：`PLATFORM VALIDATION: FAIL`，退出码 1。
- `--static-only` 只用于诊断，必须输出 `RUNTIME CHECK: NOT EXECUTED`，不得称为完整 PASS。

## 8. 生命周期治理模式

### 8.1 平台模板模式

`platform-manifest.json` 增加 `lifecycle_mode = "template"`。模板模式下：

- 允许没有活动项目、没有需求行和没有项目 Gate 决策。
- validator 必须明确输出“无活动项目，未评估任何 Gate”。
- 现有默认阻塞、待确认、未执行和未填写占位文本只视为模板内容，不视为证据。

### 8.2 活动项目模式

项目启动时由 G0 流程把模式改为 `active`，并创建 `docs/08-project-management/gate-register.md`。活动模式下缺少 Gate Register、项目上下文或必要 RTM 行必须失败。

### 8.3 唯一 Gate 状态来源

新增 `templates/gate-register-template.md`。活动项目中的中央 Gate Register 是 G0–G11 状态唯一事实源，其他生命周期文档只提供准则与证据详情。

每个 Gate 记录必须包含：

- Gate ID、名称和 `PASS | FAIL | BLOCKED` 状态；
- `NOT_EVALUATED | IN_REVIEW | DECIDED` 评估状态；
- 基线分支、提交或版本以及评估时间；
- 评估者角色、记录者、准则逐项结论和 Evidence ID；
- 阻塞项、关联 RISK/BUG/CR、理由、下一步、责任人和目标日期；
- 需要人工批准时的真实证据引用。

## 9. RTM 契约

RTM 一行对应一个 REQ/NFR，表头调整为：

```text
Trace ID | Scope Status | BG | PRD | REQ/NFR | Acceptance Criteria |
DES/ADR | TASK | CR | Commit/MR | TC | Test Execution/Evidence |
Verification Result | BUG | Defect Disposition | REL |
Traceability Status | Evidence Status | Last Verified
```

活动项目验证规则：

- `IN_SCOPE` 需求必须关联验收标准。
- 已实施需求必须有关联设计、任务和提交。
- 已验证或已发布需求必须有实际测试执行证据、明确结果和 Release。
- 测试证据为 `PENDING`、`NOT_AVAILABLE`、`NOT_EXECUTED` 或 `INFERRED` 时不得标记 PASS。
- Closed BUG 必须有关联修复提交、回归证据和关闭依据。
- 已批准 CR 必须有批准证据，并能追踪受影响的 REQ/DES/TASK/TC。

## 10. Setup 行为

`setup.ps1` 调整为：

1. 检查普通 Git 访问、Python >= 3.11 和 Git 作者配置。
2. 创建或复用 `.venv`，安装有主版本上界的依赖。
3. 检查每个原生命令的退出码，并执行 `pip check`。
4. 创建默认 `knowledge/local` 目录。
5. 默认只设置当前进程的 `COMPANY_LOCAL_ROOTS`；只有显式 `-PersistLocalRoot` 才写用户环境变量。
6. 执行完整 validator；任何失败都不得输出 Setup complete。

## 11. 测试设计

测试使用 Python 标准库 `unittest`，避免为平台自检额外引入测试框架。

### 11.1 单元与契约测试

- manifest Agent/Skill/Gate 一致性。
- manifest 不一致时 validator 必须失败。
- Gate 模板包含 G0–G11 且状态词受控。
- RTM 表头及模板模式空表行为。
- MCP 版本范围和 Python 版本检查。
- 本地路径边界、符号链接/重解析点越界拒绝。
- 未配置外部系统时返回稳定结构化错误。

### 11.2 集成测试

- MCP v2 模块导入与实例化。
- 真实 stdio 启动、协议协商与严格 8 工具列表。
- 错误 command、cwd、server 路径、启动超时和进程清理。
- 完整 `validate_platform.py` 成功路径与故障注入失败路径。
- setup 在临时副本中连续执行两次，第二次不发生未授权持久配置或版本漂移。

### 11.3 独立验证

- tester 运行完整自动化测试、validator、安装前置检查和 Windows PowerShell 兼容性检查。
- reviewer 检查需求/设计符合性、路径安全、秘密处理、Git/RTM/Gate 一致性及测试缺口。
- 重启 Codex 后确认运行时出现 8 个 `company_context` 工具；重启前不得宣称会话级 MCP 已恢复。

## 12. 错误处理与安全

- validator 使用稳定错误分类：`DEPENDENCY_MISMATCH`、`CONFIG_INVALID`、`SPAWN_FAILED`、`INIT_TIMEOUT`、`PROTOCOL_ERROR`、`TOOLSET_MISMATCH`、`GOVERNANCE_INVALID`、`GIT_INVALID`。
- stdout 只允许 MCP 协议消息；诊断走 stderr。
- 所有输出屏蔽 token、Cookie、Authorization 和 API key 值。
- validator 只执行配置中解析后位于仓库根或仓库 `.venv` 下的 MCP 命令与脚本。
- 外部 URL、SSRF 策略、响应体限制和敏感数据生命周期登记为后续安全增强项，不在本次最小兼容修复中宣称已完成。

## 13. 回滚

1. 所有修改位于独立修复分支。
2. MCP 修复、validator、治理模板分别提交，允许逐项回退。
3. 如果 MCP v2 集成验证失败，保持 `main` 的原始基线，不合并修复分支；不得通过降级依赖掩盖失败。
4. 合并后出现问题时，通过合并提交回退到原始基线，并保留测试和缺陷证据。

## 14. 验收条件

1. 普通 `git status` 成功，`main` 有原始基线，修复在独立分支完成。
2. 完整自动化测试全部通过，无未预期警告或遗留 MCP 子进程。
3. `validate_platform.py` 在实际 MCP stdio 健康检查后返回退出码 0，并报告模板模式，不报告任何项目 Gate PASS。
4. 故意破坏 manifest、MCP 导入、工具列表、Gate 模板或 RTM 表头时，validator 返回退出码 1 和明确错误分类。
5. `search_local_docs` 不能读取批准根外文件。
6. Gate 模板覆盖 G0–G11，RTM 覆盖验收、CR、独立验证、缺陷处置和 Release。
7. setup 重复执行不静默写入用户级密钥或 Git 配置，失败时不输出成功。
8. tester 与 reviewer 均无未解决 P0/P1 发现。
9. 新 Codex 会话中可见 8 个 `company_context` 工具；Redmine、RAGFlow、GitLab 未配置项明确记录为 NOT EXECUTED。
