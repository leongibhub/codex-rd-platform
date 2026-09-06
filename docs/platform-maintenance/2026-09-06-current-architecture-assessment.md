# Current Architecture Assessment — 现状审计

- Record ID: ASMT-20260906-01
- Document State: DRAFT
- 范围：本次用户请求的 Phase 1；包含后续架构方向建议，不是获批的 V2 详细设计。
- 基线日期：2026-09-06（Asia/Shanghai）。
- 基线：`a2c766cd9aa411f0798fa4e1adb6f759f0ba849c`，分支 `codex/app-factory-skill`。
- 初始工作区：干净；本次不修改运行代码、配置、旧证据或 Gate 状态。
- 当前生命周期：平台模板维护/架构审计，非活跃产品研发；`lifecycle_mode=template`，项目 Gate 尚未评估。
- 人工架构批准、平台升级实施、应用级 Self-Test、发布与验收：本次均未执行。

## 结论

当前平台是 **Codex 宿主驱动的多角色研发操作规范、文档契约、只读上下文 MCP 和可运行的基础设施自检程序**。它不是空项目，也不是已经具有持久化调度能力的研发平台。

最值得保留的是证据诚实、职责分离、Git 追踪、模板/活跃项目隔离、MCP 路径限制及负向测试。最大的缺口是：规则主要由主对话解释执行，尚未成为可恢复、可查询、可干预的运行系统。增加模型能力有助于分析和实现，不能替代运行状态、测试执行和证据关联机制。

不能按文件数量给出“已完成百分之多少”；必须分别评价：规则是否定义、程序是否实现、是否真实执行、是否完成应用级验收。

## 1. 审计范围、方法与证据边界

主审负责仓库基线、跨层关系、MCP 本地调用和汇总；三个独立审计 Agent 分别负责协作架构、运行代码与测试、文档与治理。不是主审同时充当全部专业审查者。

| 实际审计任务 / 角色 | 已完成输出 | 证据位置 |
| --- | --- | --- |
| audit_collaboration / architect | 角色、Skill、Prompt、宿主边界审计；本报告事实复核 | 本会话独立 Agent 返回；事实和修订结论转录在本报告第 2、4、7、12 节 |
| audit_runtime_tests / tester | 源码与测试审计、94 项回归、配置问题复现 | 本报告第 4.1、12 节，含实际命令/exit/count/time |
| audit_governance / documentation_manager | 生命周期文档、历史证据、Gate/RTM 审计 | 本报告第 2.3、4.1、8 节 |

以上是本轮实际协作分工和结果转录，不是平台已具备持久化 Agent Board 的证明。

| 范围 | 当前基线数量 | 审计内容 |
| --- | ---: | --- |
| Git 跟踪文件 | 192 | 目录和文件清单全量盘点，按下列责任域分工阅读 |
| `.codex/` | 10 | 9 个角色定义及宿主/MCP 配置 |
| `.agents/skills/` | 13 | 所有仓库 Skill 的完整内容 |
| `docs/` | 143 | 生命周期、维护、历史设计计划及原始证据 |
| `scripts/` | 5 | 安装后配置、校验、MCP 健康检查 |
| `tests/` | 8 | 6 个测试模块及包文件 |
| `tools/` | 3 | company-context 服务、依赖声明、环境变量示例 |
| `tasks/`、`templates/`、`knowledge/` | 5 | 任务/Gate/CR/BUG 模板、知识目录说明 |
| 根文件 | 5 | AGENTS、README、manifest、安装器、gitignore |

统计口径是审计起始提交，不含本报告。`frontend/` 没有 Git 跟踪文件；没有发现可用 Dashboard 源码。`.git` 内部对象、虚拟环境依赖、缓存、其他 worktree 和私人知识目录不属于本仓库自有代码阅读范围；不读取凭据文件或把其他项目的成果算入本平台。

关键基线来源：`AGENTS.md`；`platform-manifest.json:1–46`；`docs/00-project-initiation/context-baseline.md:3–9`；`git status --short`；`git log`；`git ls-files`。最近提交主要是 MCP 启动路径参数化、自检边界修复、验证器整理和证据记录，未体现新调度运行系统。

本次使用 context-discovery、architecture-design、code-review、documentation-governance 的审计与证据规则；上下文基线记录在本维护报告，不把模板项目的空白基线改成虚假的活跃产品。

### 1.1 当前验证记录

以下结论只覆盖实际执行范围；最终结果见本报告末尾的执行补充。

- 当前会话工具清单中，company_context 的 8 个工具均可见。
- 主审实际调用 `read_local_doc(path="D:\\codex-rd-platform\\knowledge\\local\\README.md", max_lines=20)`，返回 5 行、正确路径和行号，`isError=false`。
- 这证明当前会话的本地 MCP 阅读链路可用，不证明 Redmine/RAGFlow/GitLab 外部业务调用成功。
- 没有执行关闭/重开 Codex 的受控流程，不能据此关闭历史 `TC-002`。
- 不执行真实系统压力、安全破坏、生产部署、安装器或旧项目数据采集。

## 2. 当前架构如何工作

```text
用户目标
  → Codex 主对话读取 AGENTS / 项目文档
  → 按角色 Prompt 派发子 Agent
  → Agent 读取 Skill、代码、Markdown 或 company-context
  → 调用宿主提供的文件/命令/测试工具
  → 主对话汇总结果，更新任务、RTM、证据文档
  → 人工或主对话判断下一步

独立的基础设施自检：manifest / TOML / 文件 / Gate / RTM 检查
                          + MCP stdio 启动与 tools/list
```

这里的 Orchestrator 是主对话承担的职责，仓库没有独立的持久化 Orchestrator 服务。宿主能实际派发 Agent，不等于仓库拥有跨会话调度、可靠交接和状态恢复能力。

### 2.1 Agent、Skill、Prompt

9 个角色为 researcher、product_manager、requirement_analyst、architect、developer、tester、reviewer、documentation_manager、release_manager。角色文件定义职责、模型配置、文件系统沙箱和交付要求；researcher/reviewer 使用只读模式，其他角色主要是 workspace-write。这不构成每角色 Tool/MCP 权限隔离。

13 个 Skill 覆盖立项、发现、研究、竞品、需求、设计、拆任务、开发、测试、审查、文档、发布与结项。当前大多是简短检查清单，不是带状态转移、执行器和异常处理的 Workflow。

指令来源包括当前用户指令、`AGENTS.md`、角色 TOML 中的指令和被触发的 Skill。任务模板、历史计划是可供读取的上下文，不意味着宿主自动把它们注入 Prompt；未见独立 Prompt 行为回归集。宿主并发配置是 8（`.codex/config.toml:2`），不是任务依赖、资源、冲突文件或成本预算感知的调度器。

### 2.2 MCP 和 Harness

仓库配置两个 MCP server：company_context 和 openaiDeveloperDocs。前者有仓库实现，后者是外部文档端点配置。本次没有验证后者的服务健康。

company_context 提供：本地搜索/阅读、Redmine 搜索/读 issue、GitLab 项目信息/issue 搜索、RAGFlow 检索、组合上下文。它们是语义上的只读上下文能力，不是创建任务、触发 CI、部署或控制 Agent 的接口。

已有防护包括批准根目录、路径解析与逃逸限制、单文件大小上限、读取行数限制、网络超时、错误信息收敛，以及真实 stdio 启动检测。全局可用插件、用户安装的其他 Skill 和宿主工具不自动等于平台已集成、已测试或可移植的能力。

### 2.3 文档、Context 与 Gate

`docs/00`–`docs/10` 共 102 份 Markdown。文档审计按“只有标题、空表、待填写字段或通用提示，未包含具体项目内容”的口径，将约 95 份归为骨架/模板。另有实质性治理规则和 BUG-001 平台维护证据。这对模板仓库本身是合理定位，不能当作已生成完整产品资料；该近似分类不是缺陷计数。

G0–G11、独立测试/评审和 19 列 RTM 已有正式规则。template 模式没有 active Gate Register 是正确行为，不是缺陷；不得给模板判产品 Gate PASS。

Context 的真实能力是 Git/Markdown 加受限文件读取和外部检索。没有项目级不可变上下文包、依赖版本、决策影响传播、产物过期检测或可查询知识图谱。聊天转述仍承担大量协调信息。

## 3. 能力现状矩阵

| 能力 | 当前已具备 | 距用户目标的主要差距 |
| --- | --- | --- |
| 需求工程 | 角色、Skill、SRS/验收模板 | 无初始需求模型、推断确认边界、问题优先队列和需求冻结执行机制 |
| 多 Agent | 9 角色、宿主派发、职责分离规则 | 无持久 Task/Run、可靠交接、依赖调度及恢复 |
| 可观察性 | 宿主对话进度/会话历史、任务文档 | 无统一实时 Board、事件状态投影和控制反馈 |
| 开发测试 | 开发/测试/评审角色，真实平台测试 | 无应用模块 Code→Test→Review→Fix 自动闭环 |
| 黑盒 QA | 测试角色和基础用例模板 | 无风险驱动测试模型、完整结构化用例及自动化转换管线 |
| 文档治理 | 完整目录、RTM/Gate 契约和证据规则 | 无随事件更新、依赖失效检查和按项目裁剪的产物系统 |
| 追踪 | ID、19 列 RTM、部分引用校验 | 无任意 Bug/Case 到需求版本、代码、执行和发布的关系查询 |
| Human Control | 用户在对话中审批、打断、改需求 | 无可确认执行的 Pause/Resume/Retry/Reassign/Rollback 控制协议 |
| Context | Git、文档、8 个 MCP 工具 | 无隔离项目快照、最小任务上下文包和新旧产物一致性管理 |
| 发布/运维 | 发布角色和文档模板 | 无构建部署执行器、环境就绪验证、回滚验证与发布结果采集 |
| 知识复用 | Lessons Learned/知识目录 | 无经验证模式的索引、检索、适用性和回归机制 |
| 平台 Self-Test | 平台基础设施测试和历史证据 | 无小应用从 Idea 到 Close 的完整实际运行证据 |

## 4. 最主要的 10 个问题

下表是目标能力差距及其风险，使用 T0（首批）/T1（后续）表示升级顺序，不是仓库 code-review 的 P0/P1 缺陷严重度。具体已确认代码问题和契约冲突另列；模板未实现未来目标并不违反其当前 template 契约。

| 编号 / 优先级 | 问题及证据 | 影响 | 建议处理 |
| --- | --- | --- | --- |
| F01 / T0 | Orchestrator 仅在对话规则中；`tasks/TASK-000-template.md:1–32` 没有可执行任务契约，源文件清单无调度器 | 仓库无法保证会话中断后可靠续跑，交接/重试靠主对话协调 | 建持久 Task、Run、依赖和合法状态迁移内核 |
| F02 / T0 | `.codex/config.toml:2` 只有并发配置；无事件协议和 Dashboard 源码 | 缺少谁在做什么、为什么、是否卡住的统一可查视图 | 先建事件与心跳，再做 Board、时间线和控制回执 |
| F03 / T0 | requirement_analyst 与 requirement-analysis 规定“列需求/歧义”，无发现模型与问题策略 | 风险：把分析负担转给用户，反复确认或错误冻结 | 先生成事实/推断/风险/业务流，再问少量关键设计问题 |
| F04 / T0 | tester/reviewer 与 AGENTS 有独立性规则，但无模块质量门禁执行器 | 风险：Developer 自报完成被当成已经验收，失败只落文档 | 独立执行身份、测试产物和 Review 成为 DONE 的强前置条件 |
| F05 / T0 | QA 用例/报告主要是骨架，无 Test Model 或运行适配器 | 尚无风险建模到自动执行、定位、修复、回归的实现 | Test Model→Case→Automation→Run→Defect，逐环验证 |
| F06 / T0 | RTM 是 Markdown，`platform_validation.py:557–615` 把验证 PASS 与 REL 强耦合；类型引用校验主要见 `:619–648` | 难表达“需求已测过、尚未发布”；缺少基线/执行级查询及影响传播 | 保留约束意图，改为版本化关系模型，分离验证/发布/审批事实 |
| F07 / T1 | `get_project_context` 组合即时检索；`knowledge/local/README.md` 仅目录政策 | 同任务不同 Agent 可能读取不同版本，旧设计/测试误用于新需求 | Git 基线 + 最小上下文清单 + 内容哈希 + 失效规则 |
| F08 / T1 | 角色与模板存在状态词汇冲突，102 份生命周期文件大多骨架 | 格式完备易被误认为证据完备；多个文本状态源可能漂移 | 状态 schema 单源、文档投影、裁剪理由和持续一致性检查 |
| F09 / T1 | release/closure 是角色和模板，未见 CI、部署/恢复执行器或环境控制 | 缺少应用部署/回滚证据；长测与重启的恢复未由平台保障 | 安全执行适配器、运行预算、检查点、产物清单及环境证据 |
| F10 / T1 | 基础设施测试未覆盖真实应用全流程；扩展路径还存在配置/安装风险 | 局部自检 PASS 无法保证“一句话到应用”，扩展 MCP 可破坏配置 | 加配置边界回归、适配器契约、平台级故障演练和真实小应用 Self-Test |

### 4.1 具体技术债与可复查位置

1. `scripts/write_local_config.py:27–29`：对所有 `command`、`args`、`cwd` 行全局替换，未限定 company_context 节。新增第二个 stdio MCP 时，其启动配置也会被覆盖。当前单一 stdio 配置未触发，但它是明确的扩展风险。修复应按 TOML section 精确更新并验证其他 section 不变；本次不修改。
2. `install-to-D.ps1:9–26`：硬检查 D 盘；递归复制仅排除安装器，可能把 `.git`、`.venv`、`.worktrees` 一并复制；`-Force` 合并覆盖，缺少自身/子目录目标约束。未运行安装器；建议包清单、目标规范化、预检和可恢复升级。
3. `.codex/agents/documentation-manager.toml:43` 把 `BLOCKED` 列为缺失证据取值，且使用 `NOT AVAILABLE` 等空格形式，与 `AGENTS.md` 及 Gate 管理的证据域冲突。应统一为受控 schema，而非继续复制枚举文本。
4. 一些模板仍有局部 Gate `Status: BLOCKED`，如 `project-charter.md:36–40`、`PRD.md:23–24`。在 template 中是占位风险，不能当作有效项目 Gate；复制到 active 后会与中央 Register 冲突。
5. `scripts/platform_validation.py:585–595` 要求验证 PASS 必有 REL；`:607–614` 将任意非空 CR 与已验证的测试证据绑定。未来需允许“CR 待批/影响分析中”“测试通过但未发布”，把 CR 批准证据与测试执行证据分列。不能用生成空 REL 或虚构测试规避。
6. `_typed_links_are_valid` 对多数 BG/DES/TASK/TC/BUG/REL 主要检查 ID 形式，EVD 解析会搜索文档元数据。它不是完整引用完整性、内容质量或执行真实性证明；文档声明一个 EVD 不足以证明运行成功。
7. `server.py:168–182` 的 Redmine 搜索说明称搜索 subject/description，实际请求只设置 subject 过滤。应修正文案或实现并按部署版本测试。外部连接的全链路目前未验证。
8. 本地知识搜索 `server.py:81–117` 按目录遍历、逐文件文字匹配；缺少索引、目录总预算、结果规模统一约束。外部响应也应有脱敏、大小和租户/项目范围策略。路径白名单已经存在，不能误报成完全无访问控制。
9. 依赖为版本范围而非锁定环境；平台主要按 Windows 布局验证。可移植性和依赖升级回归未由完整部署矩阵证明。
10. 历史设计计划的未勾选条目与维护任务已实施状态并存，应明确“计划基线”与“执行记录”，不能把旧计划当作实时进度。

另外，角色文件没有显式的 per-role Skill/Tool/MCP allowlist；tester 的 workspace-write 不是“只可写测试目录”。这是独立性与最小权限未强制落地的证据，不等于当前 MCP 含写接口。后续应把产品源码、测试/证据目录和外部操作权限分别约束。角色 Prompt、Skill、模型与 effort 版本需进入每次 Run 快照；模型可配置不代表所有角色均已实测可用。

## 5. 哪些应保留、哪些重构、哪些确实缺失

**保留并复用：** Git 和稳定 ID；开发/测试/评审分离；人类批准和证据禁止伪造；template/active 隔离；现有 Gate/RTM 的有效规则；MCP 的只读上下文接口、路径约束、启动健康检查；既有负向测试和历史 ADR/审查证据；文档分类框架。

**重构边界：** 将主对话协调转为“模型做判断建议、确定性内核执行约束”；任务模板升级为结构化契约；Markdown 状态表转为可追溯的生成视图；Skill 从检查清单增加输入/输出/异常/验证契约；MCP 从连接函数扩展为有范围与审计的适配器；测试与发布模板接到实际执行证据。不是删除旧文件后重新生成。

**在当前仓库未发现实现：** 持久调度器、项目/任务/Run 状态数据库、统一事件流、Agent Dashboard、控制命令回执、租约/心跳/崩溃恢复、需求发现交互引擎、结构化测试模型、通用测试运行与结果归一化、自动缺陷闭环、项目级追踪查询、自动构建部署回滚管线、模式知识复用引擎。这些能力可能部分由宿主人工操作实现，不算平台自动能力。

**未取得验证证据：** 完整应用级 Self-Test、受控 Codex 重启、真实外部 API 合约/连通。本项与“模块未实现”分开记录。

## 6. 建议的新一代总体架构（供后续评审，非实施批准）

建议先采用 **本地优先的模块化单体控制面 + 可替换执行适配器**。当前没有证据支持立即上微服务、复杂消息集群或分布式多租户控制平面。若以后明确远程多用户/多执行机需求，再扩展部署形态。

```text
自然语言 / CLI / Dashboard
             ↓
需求发现与决策交互 ←→ 人类批准与变更
             ↓
Orchestrator：规划、选角色、解释原因、提出动作
             ↓
运行内核：状态机、依赖、权限、质量门禁、预算、幂等和恢复
        ↙              ↓                 ↘
Agent 执行适配器    测试/构建适配器      外部系统/MCP 适配器
        ↘              ↓                 ↙
事件 + Run + 产物 + 执行证据 + 追踪关系
             ↓
Dashboard / RTM / 报告 / 文档投影 / 后续调度
```

### 6.1 Source of Truth：按事实域划分，避免双写

- Git：版本化需求、设计、代码、测试定义、政策、ADR；保持工程记录系统地位。
- 运行存储：任务、Run、事件、控制请求及回执、租约和状态；本地事务数据库是候选，不是本次拍板的技术选型。
- 产物存储：报告/日志/包/截图等，记录哈希、大小、来源、环境、commit 和 Run；发布证据清单纳入 Git。
- Dashboard/Markdown RTM：上述事实的可重建视图，不再各自任意修改状态。
- 人工审批：绑定需求/设计具体版本、审批对象、时间、来源；文档写着 APPROVED 不能替代批准证据。

### 6.2 必需领域模型

| 模型 | 必需字段/规则 |
| --- | --- |
| Project | 生命周期 schema 版本、当前阶段、基线、权限/预算、适用 Gate 政策 |
| Requirement | REQ/NFR ID、来源、事实/推断/已确认、验收标准、范围、版本和依赖 |
| Task | 理由、REQ/DES、依赖、输入引用/哈希、输出契约、负责人、允许路径/工具、验收检查 |
| Run | 执行身份、attempt、基线、开始/结束、心跳、结果、证据、失败分类；一次重试新 Run |
| Event | project/task/run/agent、时间、序号、相关事件/命令、状态前后、脱敏载荷 |
| Artifact | 类型、版本、内容哈希、生成者 Run、验证状态、关联需求、是否已过期 |
| Decision/Control | 用户请求、作用范围、影响分析、批准基线、执行状态和回执 |
| Test/Defect | 测试模型/用例/自动化/执行分层；缺陷分类、主责、修复、复测/回归引用 |

Agent、Task、Run、Workflow、Gate 是不同状态域。Agent 可显示 IDLE/ANALYZING/PLANNING/WORKING/TESTING/REVIEWING/BLOCKED/WAITING_FOR_USER/DONE/FAILED，具体枚举在 Phase 3 统一；Run 成功不自动等于 Task DONE。失联显示未知/心跳过期，不伪装持续工作。

进度优先显示“完成 3/5 项验收检查”或“2/4 个子任务”，无法测量时显示未知，不生成主观百分比。Board 展示：Agent 身份/职责、任务原因、输入、当前动作、输出、阻塞、需要协助者、后继、上次心跳、项目阶段；时间线展示交接、退回、审批和失败因果。不能只渲染聊天日志。

### 6.3 Prompt → Context → Harness → Loop

- Prompt：角色职责和判断准则，不承载实时项目事实。
- Context：由任务生成最小、版本固定的上下文包，含已批准规格、相关接口、限制和必要证据。
- Harness：提供实际可用的工具、MCP、文件范围、测试命令、预算及副作用限制；缺失能力明确呈现。
- Loop：Analyze→Plan→Execute→Verify→Review→Improve，由持久 Run/事件连接，不依赖单次对话。

先验证真实宿主能提供哪些 Agent 生命周期事件、派发/取消控制和恢复能力；不足的用适配器明确降级。不能假设宿主有未验证的 SDK，也不能承诺工具不可见时仍能知道全部内部进度。可观察的是动作、输入输出、决策摘要和运行事实，不要求暴露模型内部思维链。

### 6.4 需求发现与用户交互

收到一句想法，先生成 Initial Requirement Model：目标、角色、场景、主业务流、输入输出、数据/权限/外部依赖、异常边界、隐含 NFR、范围、风险和未知项。每条分别标记来源事实、AI 推断、待确认或已确认。

问题按“错误代价 × 架构影响 × 不确定性”排序，每轮只问少量关键问题；说明已有判断、推荐、理由及影响。普通实现细节用可撤销默认值，重大权限/数据/部署/外部依赖选择不能假定用户批准。

确认后产生版本化 SRS、验收标准和 RTM。修改需求只使受影响设计/任务/测试过期并重新调度，不重启全部项目。通过粗粒度需求场景集测评遗漏、关键问题质量、澄清轮次和冻结后返工；不用“问了多少问题”衡量质量。

### 6.5 质量与测试闭环

每个模块先确定验收与测试接口；开发和独立测试设计可以并行，执行须等待对应可运行版本。

```text
模块代码 + Developer 单测
  → 独立 Unit 验证 Run
  → 独立 Integration 验证 Run
  → 独立 Review Run
  → 内核核验相同基线与证据 → 模块 DONE

失败 → 归因/Defect → 主责修复 → Review → Retest → Regression → 满足关闭条件
```

黑盒 QA 只接收产品规格、公开接口/UI、环境和用户角色，不以源代码为测试预期来源。功能树→风险→对象/类型→测试点→矩阵→用例；不先凑用例数量。

用例至少含用户指定的 Case/Requirement ID、类型、模块、优先级、风险、前提、可复现数据、步骤、预期、自动化方法/工具/状态、实际结果及验证结果，并增加环境/版本、自动化引用和清理步骤。未执行不能填 PASS/FAIL，结果必须区分 NOT_EXECUTED、BLOCKED、PASS、FAIL；人工检查项说明原因和证据方式。

按技术栈选择 pytest、Playwright、API/负载/安全等适配器，而不是固定所有工具。执行前验证目标授权、测试环境、数据可回收性、资源预算、时长和停止条件；安全/压力测试不得默认为生产系统。8/24/72 小时稳定性测试按实际运行时长记录，不能以短测模拟后宣称完成。

失败先分类产品、脚本、环境、配置、需求或性能问题；修复交给对应主责，不把全部 FAIL 当产品 Bug。报告从运行证据生成：范围/版本/环境/时间、分类型结果、总数/执行数/通过/失败/阻塞/未执行、明确分母的通过率、缺陷风险、PASS/CONDITIONAL PASS/FAIL 和发布建议。报告结论与 Gate 状态是不同域；有未完成必测项不能报告无条件 PASS，风险接受必须有真实授权。

### 6.6 人工控制和恢复

Pause/Resume/Retry/Reject/Approve/Modify/Reassign/Skip/Rollback 都是带作用范围、授权和回执的命令。暂停需区分请求已接受、等待安全点、已暂停；不得把停止对话误报为远端命令已停止。

重试有上限、退避和幂等键；副作用先检查结果再重试。要求冲突/预算耗尽时提供已验证备选而非无限循环。变更使旧基线结果不可用于新 Gate；取消的旧 Run 晚到结果不能覆盖新任务。Rollback 是受控环境/版本恢复或补偿，不是删除 Git/审批/事件历史。跳过不等于通过。

### 6.7 文档与知识

按项目规模裁剪文档包，把需求、设计、测试、发布与交付视图从版本化事实持续生成；叙述性分析仍需专业 Agent 撰写并检查。合并/省略记录理由，不能省略适用的安全、验收或回滚内容。每个变更事件触发相应 RTM/文档过期检查。

Lessons Learned 记录适用条件、证据、失败例、版本和置信度，进入项目知识索引前脱敏并验证；不能把一次未经验证的建议自动提升为长期规则，也不自动写入用户个人全局记忆。

## 7. Agent / Skill / Workflow / Tool / MCP 重新划分

| 层 | 应承担什么 | 不应承担什么 |
| --- | --- | --- |
| Agent | 需要独立判断/隔离上下文的专业责任：需求产品、架构、实现、独立 QA、独立 Review、文档治理、交付 | 不按每个动作创建常驻角色；不以自报 DONE 代替验证 |
| Skill | 方法复用：需求发现、UX、前后端/数据库实践、单测、黑盒模型、性能、安全、部署等 | 不冒充调度器、持久状态或执行证据 |
| Workflow | 依赖、并行、重试、质量门禁、变更与缺陷流转 | 不仅是一段提示词中的箭头 |
| Tool/Command | 确定性操作：读写文件、执行测试、构建、解析报告、查询状态 | 不自行判断业务批准或完成度 |
| MCP | 向 Agent 暴露外部系统和受控平台能力，保持鉴权/范围/审计 | 不替代业务状态机；不是每个 Python 函数都需包装 MCP |

保留现有 9 个角色的有用职责，不要求 9 个同时运行。Orchestrator 负责协调而非代写所有专业工作。需求/产品可在同一发现任务中协作；Research 按需调用。Backend/Frontend/Database/UX 优先是任务能力标签和 Skill，确有并行隔离需求再派独立实例。

Unit/Integration/Black-box/Performance/Security 是不同验证职责与执行策略，不必永久创建五类常驻 Agent；按风险独立派发。Developer 的修改不能由同一执行身份独自验收；黑盒 QA 与代码审查使用不同上下文边界。DevOps 执行能力与 Release 放行判断分离；Document Agent 不制造批准或给自己签验收。

## 8. Gate 与目录演进建议

保留现有 G0–G11 历史，不在本次改编号。用户提出的 G0–G8 是新的里程碑视图，应引入版本化政策和映射，不直接覆盖旧记录：

| 用户目标 Gate | 与旧体系的关系/新增条件 |
| --- | --- |
| G0 Idea | 记录目标与范围；覆盖原 G0 的必要启动事实 |
| G1 Requirement Ready | 原 G1 研究、G2 产品、G3 需求中的适用条件，加关键问题确认 |
| G2 Design Ready | 原 G4 设计条件 |
| G3 Development Ready | 原 G5 计划与测试策略 |
| G4 Code Complete | 原 G6，加模块级独立单元/集成测试与评审前置条件 |
| G5 System Test Ready | 新的可部署环境、数据、接口、健康检查与测试模型就绪门槛 |
| G6 Test Passed | 原 G7/G8 的适用测试与独立审查条件；不能漏掉原评审要求 |
| G7 Release Ready | 原 G9 验收要求及 G10 发布就绪条件；发布就绪不等于已部署成功 |
| G8 Project Closed | 原 G11，加实际交付/发布执行结果和遗留事项移交 |

每 Gate 在 Phase 3 定义 Entry、Exit、Artifacts、Quality Policy、Owner、审批角色与证据。新旧项目可选择对应 schema；迁移用 CR 记录，双版本契约测试通过后再转换，绝不把占位文本迁成 PASS。

目录以增量方式考虑：保留现有 docs/、skills/、agents/、tests/ 和 MCP；增加 `platform/domain`、`orchestration`、`context`、`adapters`、`observability`、`api`，Dashboard 放入 `frontend/`。项目运行数据放在隔离的项目运行目录并排除秘密和临时数据；项目 Context 是现有需求/设计/接口等的索引和版本引用，不复制出第二套可冲突文档。

## 9. 最优先改的 5 件事

1. **运行契约 + 最小控制内核 + Board 的一条纵向链路。** 先验证宿主适配器，真实派发一个任务，显示输入/状态/交接/回执，演练中断续跑；不先做假状态 UI。
2. **Requirement Discovery。** 用三种一句话需求验证自主建模、关键提问、确认与冻结；用户无需补写长 Prompt。
3. **模块质量闭环。** Developer、独立测试、Review 与缺陷回路接上同一代码基线；测试失败时 DONE 被拒绝。
4. **结构化追踪、产物和文档投影。** 从任一缺陷查回需求、设计、代码、测试 Run；变更后旧证据不能误放行。
5. **黑盒自动化 + 本地交付 + 小应用 Self-Test。** 真正跑完一条应用闭环，含失败修复、部署/回滚及报告，不以更多模板替代。

配置更新/安装边界等已发现技术债应进入对应模块前置修复；不以改这些小问题冒充完成架构升级。

## 10. 后续路线图与退出条件

| 阶段 | 交付与验证 | 退出条件 |
| --- | --- | --- |
| 当前 Phase 1 | 本报告、当前运行边界、独立审计证据 | 用户能据事实理解哪些已实现/未实现；不改运行架构 |
| Phase 2 Gap | 逐项目标能力、优先级、可测验收、依赖与风险 | 覆盖用户各验收目标，无伪装完成项 |
| Phase 3 Design | V2 HLD/LLD、状态/任务/事件/上下文 schema、测试模型、接口、迁移 ADR | 关键状态/失败/并发/审批场景可检查、可测试 |
| Phase 4 Review | 演示状态交互与一条完整流程，讨论方向性选择 | 用户批准明确设计基线；不以本次审计请求充当实施批准 |
| Phase 5A | 适配器能力验证、最小运行内核、事件/Board/控制 | 真实 Agent Run 可观察；拒绝非法状态、可暂停/恢复、故障续跑 |
| Phase 5B | 需求发现、任务 Context、增量开发测试/Review | 一句话需求到可测规格；失败自动回到正确责任方 |
| Phase 5C | 追踪、文档投影、黑盒测试与报告、发布适配器 | 证据与基线一致；从 Case/Bug 可追溯；部署/回滚有结果 |
| Phase 6 Self-Test | 隔离环境中的小应用全流程 | 下面各项真实完成，未执行项不冒称通过 |

建议 Self-Test 使用小型持久化任务管理应用，含两个角色、增删改查、权限边界和一个 API，避免外部商业数据源。测试既验证应用，也验证平台：

- 从粗略想法产生需求、关键决策、设计、任务和独立测试模型。
- 真实开发、单元/集成/黑盒自动化、独立审查、报告、本地构建部署。
- 注入一个受控缺陷，观察 FAIL→归因→修复→复测→回归→关闭。
- 注入一次执行中断/取消，验证 Run 状态、恢复及迟到结果处理。
- 修改一个已确认需求，检查只重做受影响链路及审批失效。
- 验证发布包、安装说明和隔离环境回滚；保留实际执行证据。
- 自动演练中的用户回答必须标记“模拟用户输入”；最终人工验收不能由模拟回答冒充。
- 以端到端记录证明 Idea→Requirement→Design→Development→UT→IT→Black-box→Automation→Report→Release→Close；未达到条件时给出实际失败或缺失证据。

当前不承诺日历完成日期。先通过架构评审确定最小可运行闭环，以每阶段可演示结果推进；不会再用长期文档日程替代实际应用验证。

## 11. 本次边界与后续待决策

本次只新增审计报告，不修代码、不更新旧 Gate、不创建虚假应用需求，不启动超市项目。需要下一阶段讨论的方向性问题只有：本地单用户优先还是远程多用户、主要宿主及其真实可用运行接口、自动化执行/审批边界。普通工程细节由设计分析决定，不要求用户逐项拍板。

正式进入实施前，针对批准的升级范围建立 CR、需求/设计/任务追踪；本报告中的 F01–F10 是审计发现编号，不冒充已基线 REQ、已分派 TASK 或已确认 BUG。

## 12. 执行证据补充

- Evidence ID: EVD-ASMT-20260906-01
- Evidence Status: VERIFIED
- 验证对象：上述 HEAD 上的平台无安装回归与受限本地检查，不是产品 Gate。
- 执行者：独立 `audit_runtime_tests`（tester）；本地会话 MCP 阅读由主审执行。
- 记录形式：本次工具返回和独立 Agent 回传的命令/汇总转录；非人工签字。未另存整套原始 stdout，不虚构原始日志路径。

| 实际检查 | 结果 | 实测边界 |
| --- | --- | --- |
| company_context / governance / manifest / validator 四模块 | 82 tests，24.877 s，OK，exit 0 | 无安装回归 |
| mcp_stdio 模块 | 12 tests，9.349 s，OK，exit 0 | 本地进程/协议/工具契约 |
| 上述唯一用例合计 | 94/94 通过 | 不把重复执行计为更多测试 |
| setup_contract 模块 | 9 项 NOT_EXECUTED | 健康路径会实际运行 setup 和 pip install，因此本次排除 |
| static validator | PASS，exit 0，wall 1.604 s | TEMPLATE；项目 Gates NONE；runtime NOT_EXECUTED |
| 默认 validator | PASS，exit 0，wall 3.241 s | TEMPLATE；只启动可信本地 MCP 并执行 tools/list |
| pip check | No broken requirements，exit 0，wall 1.564 s | 当前已安装依赖一致性，不是版本/平台兼容矩阵 |
| 当前会话 MCP read_local_doc | 成功返回 5 行，isError=false | 仅批准知识目录中的 README |
| 双 stdio MCP 配置夹具 | 复现非目标 MCP 被改写，脚本 exit 0，wall 0.137 s | 函数正常退出仍产生错误配置；已记录，未修复 |
| 受控 Codex 重启、真实外部 API、应用级 Self-Test | NOT_EXECUTED | 不以本地成功替代 |

测试收集过程：最初五模块组合运行的工具输出截断，缺少完整汇总；没有把它算作 PASS。随后分为上述 82+12 两组重新执行以保留 exit/count/time。9 项安装测试未执行的代码依据是 `tests/platform/test_setup_contract.py:166–174` 及 `scripts/setup.ps1:67–70`。

实际命令（PowerShell，工作目录 `D:\codex-rd-platform`，解释器均为仓库虚拟环境，不是 PATH Python）：

```powershell
& .\.venv\Scripts\python.exe -m unittest tests.platform.test_company_context tests.platform.test_governance_contract tests.platform.test_manifest_contract tests.platform.test_validator_contract -q
& .\.venv\Scripts\python.exe -m unittest tests.platform.test_mcp_stdio -q
& .\.venv\Scripts\python.exe scripts\validate_platform.py --static-only
& .\.venv\Scripts\python.exe scripts\validate_platform.py
& .\.venv\Scripts\python.exe -m pip check
```

双 MCP 夹具仅位于临时目录，不改仓库。清理被执行环境策略拒绝，非秘密夹具留在 `C:\Users\LEON~1.WAN\AppData\Local\Temp\codex-write-local-config-audit-7c7242227dfa43bcaacfd929070d1654`；本次不绕过清理限制。该目录不是交付物，也不是生产数据。

本轮三个独立审计均完成；协作架构 Agent 另行复核本报告的事实与范围。当前没有据此给任一项目 Gate、发布或用户验收判 PASS。

报告独立复核结果：修正了指令/上下文混称、沙箱边界、目标优先级与缺陷严重度混用、错误行号及证据状态混淆；复核未发现剩余阻塞项。该结论只针对报告准确性和 Phase 1 范围，不是 V2 设计批准。第 12 节为本次审计结果转录；若后续作为正式 Gate/发布依据，应另存原始输出或重新执行生成持久原始证据。
