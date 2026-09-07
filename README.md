# Codex R&D Platform

> 中文（默认） · [English](README.en.md)

这是一个供 **Codex 宿主协作** 使用的本地研发控制面：它将项目、任务、质量检查、版本化生命周期工件、测试执行、缺陷、Gate 候选评估和多技术栈验证存入 SQLite；源代码和文档事实仍在 Git 工作区中。

它不是自动调用模型的云服务、多租户系统或生产发布平台。当前源码已包含受信任宿主启动的常驻 `worker-service`、SSH Ed25519 审批适配器、受控部署执行器和 Linux 原生安装脚本；它们不暴露匿名远程命令接口。已确认的安全 probe 证明 Codex auto-review 可读写 workspace 外路径，因此生产 Codex backend 现已 fail-closed 禁用；控制库与 workspace 分目录只是运维卫生，**不是**隔离边界。当前默认提案路径是 no-tools Responses HTTPS：模型不直接拥有文件/命令工具，宿主才会受控 CAS 落盘和登记 DRAFT。Runtime 校验、记录和展示事实。执行端、严格阶段编排及集成已通过本轮独立源码复审；这不代表真实人类审批、生产部署/回滚、客户验收或 live Responses 已执行。请先阅读 [V3 运行说明](docs/platform-v3/README.md) 与 [V3 执行端交付记录](docs/platform-v3/completion-execution-delivery.md)。

## 当前范围与版本

- V3 使用 GitHub 分支 `codex/platform-v3-lifecycle`，`2d77904` 仅是历史续作起点，不是当前版本；经验证的源码提交及对应 CI 见[后续交付记录](docs/platform-v3/completion-delivery.md)和 [CI 执行记录](docs/platform-v3/ci-execution.md)。它**尚未合并到 `main`**，默认分支 clone 不含本轮 V3 内容。
- V2 提供项目/任务、四阶段质量 Run（implementation、unit、integration、review）、看板和受控本地命令执行；V3 加入版本化工件、追踪、测试模型/Case/Execution、工作租约、Gate assessment、release/rollback 事实、分页读取和五技术栈 Harness。
- 已有本地源码验证、独立测试和审查记录，但它们是工程范围证据，不是正式产品验收或生产发布。见 [追踪索引](docs/platform-v3/traceability.md)、[最终本地验证 JSON](docs/platform-v3/evidence/final-local-validation.json) 与 [能力状态](docs/platform-v3/capability-status.md)。
- 顶层 `platform-manifest.json` 仍为 `lifecycle_mode: template`。模板校验通过、任务 `DONE`、Harness `PASS` 或 Case 报告 `PASS` 都不等于任何 G0–G11 `PASS`、人工验收或发布建议。

## 架构和职责

```text
Git 工作区 ──源码、文档、manifest、审查变更──> Git / GitHub
     │
Codex / 受信任宿主 ──真实派发、命令、进程取消──> Agent / 终端 / 浏览器
     │                                                     │
     └──受控 Runtime 命令、运行证据、生命周期事实──────────┘
                              │
                       SQLite (.rd-platform/state.db)
                              │
                 loopback 看板 127.0.0.1（观察和有限 V2 控制）
```

开发者实现、tester 独立测试、reviewer 独立审查、release manager 留存真实发布证据。看板里的 Agent 名称不是已启动模型；`ACTIVE` 也不是后台仍在运行的证明。

## 获取正确源码

首次使用 GitHub 时必须明确选择特性分支：

```powershell
git clone --branch codex/platform-v3-lifecycle --single-branch https://github.com/leongibhub/codex-rd-platform.git
Set-Location codex-rd-platform
git rev-parse --short HEAD       # 记录此命令的实际输出；已验证源码提交/对应 CI 见后续交付记录
git status --short
```

已有 clone 时，先将该分支加入 `origin` 的 fetch refspec。Windows PowerShell 可用：

```powershell
git remote set-branches --add origin codex/platform-v3-lifecycle
git fetch origin
git show-ref --verify --quiet refs/heads/codex/platform-v3-lifecycle
if ($LASTEXITCODE -eq 0) {
  git switch codex/platform-v3-lifecycle
  git merge --ff-only origin/codex/platform-v3-lifecycle
} else {
  git switch --track -c codex/platform-v3-lifecycle origin/codex/platform-v3-lifecycle
}
git status --short
```

Linux/macOS 的 POSIX shell 使用同一 Git 逻辑：

```bash
git remote set-branches --add origin codex/platform-v3-lifecycle
git fetch origin
if git show-ref --verify --quiet refs/heads/codex/platform-v3-lifecycle; then
  git switch codex/platform-v3-lifecycle
  git merge --ff-only origin/codex/platform-v3-lifecycle
else
  git switch --track -c codex/platform-v3-lifecycle origin/codex/platform-v3-lifecycle
fi
git status --short
```

合并发生前不要把 `main` 当作本文描述的 V3 基线。已有分支路径只允许快进；若 `merge --ff-only` 因本地提交或修改失败，先保留/审阅工作后再自行处理，绝不以强制切换覆盖。改动请使用自己的分支/worktree，先检查 Git 状态和近期历史，并保留其他协作者的未提交修改。

## 安装和自检

### Windows（已提供的一键路径）

前置条件：Git、PowerShell、Python 3.11+，以及仓库中的 `git user.name`、`git user.email`。若当前 clone 未配置，请在**本仓库**设置经批准的身份；不要写入 global 配置，也不要把真实身份复制到文档：

```powershell
git config --local user.name "YOUR_APPROVED_DISPLAY_NAME"
git config --local user.email "your-approved-address@example.invalid"
git config --local --get user.name
git config --local --get user.email
```

将占位符替换为你的经批准、可审计身份；这些值只写入当前 `.git/config`，不会修改系统或全局 Git 设置。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --help
& .\.venv\Scripts\python.exe -X utf8 scripts\validate_platform.py
```

`setup.ps1` 创建或复用 `.venv`，安装 `tools/mcp/company-context/requirements.txt` 的受限依赖，运行 `pip check`，创建 `knowledge\local`，生成当前工作区 MCP 绝对路径，并运行平台校验。它默认不升级 pip，也不写用户级环境变量。仅在准备好依赖时使用 `-SkipDependencyInstall`；仅 `-PersistLocalRoot` 会持久化 `COMPANY_LOCAL_ROOTS`。

常规且**首选**的安装路径仍是上面的 `git clone --branch ... --single-branch`、本仓库 `git config --local`，再运行 `setup.ps1`。这样 target 自己拥有可审计 Git 身份和分支历史；不要将源工作区的本地 Git 配置复制到其他位置。

#### 可选：Windows 固定提交高级交付 helper

仅当不能使用 GitHub clone、且交付者能核对固定提交时，才使用根目录 `install-to-D.ps1`。它不是日常同步、增量更新或备份工具：它在 target 新建 Git 仓库，从源 `HEAD^{commit}` 作 depth-1 fetch 并 detached checkout，**不配置 remote**，然后才运行 target 的 `setup.ps1`。因此它不递归复制源 `.git`、忽略/未跟踪文件、`.venv`、`.rd-platform`、worktree、cache、`.env` 或本地知识；唯一严格例外是已提交的公开占位文件 `knowledge/local/README.md`，且必须同时匹配 blob `f361c8f3bd3b7bb62af25fb46bb48c0965c2e263`。它不是本地数据迁移。

前提和拒绝条件：

- target 必须是新目录或已有的**空**普通目录；helper 拒绝 `-Force`、非空目录、源目录本身或其子目录，以及源/目标祖先路径中的 reparse point。它从不合并、覆盖或删除已有 target。
- fresh target 不继承源 `.git/config`。`setup.ps1` 仍需在 target 进程中看到 `git user.name` 和 `git user.email`；优先改用首选 clone 路径并执行上面的本仓 `--local` 配置。若组织允许且只能用该 helper，可为**当前 PowerShell 进程**提供经批准的身份（不写 global/system 配置）：

```powershell
$env:GIT_CONFIG_COUNT = "2"
$env:GIT_CONFIG_KEY_0 = "user.name"
$env:GIT_CONFIG_VALUE_0 = "YOUR_APPROVED_DISPLAY_NAME"
$env:GIT_CONFIG_KEY_1 = "user.email"
$env:GIT_CONFIG_VALUE_1 = "your-approved-address@example.invalid"
.\install-to-D.ps1 -Destination "D:\your-empty-target"
```

将占位符改为经批准、可审计的身份；这些环境变量只影响从该 PowerShell 启动的 Git 子进程，并不将身份写进源或 target 的 Git 配置。若安装初始化、fetch、checkout 或 setup 失败，helper 不会打印成功信息、不会自动清理或复用目录；若该 target 由本次调用新建，它会留下 `.install-failed` 供诊断。保留错误和 target 后，由操作者审阅，再选择新的空目录或显式清理后重试。

该 revision-3 helper 的独立审查记录为 unit 12/12、integration 10/10 和 reviewer 22/22 PASS；真实隔离安装从提交 `527dae1b7f75d6b526682d1c5a6407c1b3fc6a53` 执行完整 setup、依赖与 MCP 检查，记录的是 `PASS (TEMPLATE MODE)`、`Evaluated Gates: NONE`。详见[独立安装交付审查](docs/platform-v3/install-transfer-review.md)和[真实隔离安装验证](docs/platform-v3/install-real-validation.md)。此前递归复制实现是保留的历史 BUG-INSTALL-001；`c3eb271` 的实际 public-stub 拒绝失败是 BUG-INSTALL-002。两者都不应作为本 helper 的行为或发布/人工验收结论。

### Linux（已捆绑原生 setup；手动路径供审计）

首选在目标 Linux Git checkout 内运行已捆绑的 `scripts/setup.sh`；它检查 Git 身份和 Python 3.11+，创建或复用本仓 `--copies` venv，安装受限依赖、运行 `pip check`、生成本地 MCP 配置并执行 validator。脚本不使用 sudo、不改全局 Git/Python、也不删除已有数据。GitHub Actions Ubuntu job `101496781967` 已观察到 native setup 和 repeat-install 成功，但这不是所有 Linux 主机或发布/验收的结论。

```bash
./scripts/setup.sh
```

下面是等价的手动审计路径；使用 `--copies` 将解释器保留在仓库内，满足 MCP 的真实路径来源检查。不要用指向仓库外解释器的软链接绕过检查。

```bash
python3 --version                     # 必须为 3.11 或更高
python3 -m venv --copies .venv
. .venv/bin/activate
python -m pip install -r tools/mcp/company-context/requirements.txt
python -m pip check
mkdir -p knowledge/local
export COMPANY_LOCAL_ROOTS="${COMPANY_LOCAL_ROOTS:-$PWD/knowledge/local}"
python scripts/write_local_config.py "$PWD"
python -X utf8 scripts/validate_platform.py
python -X utf8 -m rd_platform --help
python -X utf8 -m rd_platform stack-probe
```

`validate_platform.py` 会真实启动 MCP 并检查工具集；只有它报告的健康检查才是本机结果。不要直接复用别的工作区的 `.codex/config.toml`。远程 MCP 服务仍需真实网络与账户；在线 Linux/Windows 验证的具体提交和结果见 [CI 执行记录](docs/platform-v3/ci-execution.md)。

## 在 Codex 中开始或续作

### Agent 与 Skill：9 个角色、14 个技能、1 个统一入口

不是“把几个 Agent 打包成一个 Skill”。当前有 **9 个专业 Agent 定义、14 个仓库级 Skill**，主 Codex 会话负责 Orchestrator 调度。Agent 定义“谁执行”，Skill 规定“怎么做”，Runtime 记录真实任务与证据。清单见 [platform-manifest.json](platform-manifest.json)；下表是常用分工，不是硬绑定，也不代表同时启动 9 个模型。

| 角色及定义 | 主要职责 | 常用 Skill |
| --- | --- | --- |
| 主 Codex 会话（无第 10 个专业 Agent 文件） | 分析、调度、依赖、交接、用户决策 | `platform-orchestration`、`context-discovery`、`project-initiation`、`task-breakdown` |
| [researcher](.codex/agents/researcher.toml) | 市场、竞品、技术与证据研究 | `market-research`、`competitor-analysis`、`context-discovery` |
| [product_manager](.codex/agents/product-manager.toml) | 用户、场景、产品目标、PRD | `project-initiation`；产品专业约束在 Agent 定义中，没有单独 product Skill |
| [requirement_analyst](.codex/agents/requirement-analyst.toml) | 需求、验收标准、RTM | `requirement-analysis` |
| [architect](.codex/agents/architect.toml) | 架构、接口、数据、安全、ADR | `architecture-design`、`task-breakdown` |
| [developer](.codex/agents/developer.toml) | 模块实现与单元测试 | `implementation` |
| [tester](.codex/agents/tester.toml) | 独立测试模型、执行、缺陷与回归 | `testing` |
| [reviewer](.codex/agents/reviewer.toml) | 独立代码与架构审查 | `code-review` |
| [documentation_manager](.codex/agents/documentation-manager.toml) | 文档、追踪、证据、归档 | `documentation-governance`、`project-closure` |
| [release_manager](.codex/agents/release-manager.toml) | 发布准备、部署/回滚材料、交付 | `release` |

14 个 Skill 的文件均为 `.agents/skills/<名称>/SKILL.md`。完整应用开发的统一入口是 [platform-orchestration](.agents/skills/platform-orchestration/SKILL.md)，其余技能按任务选择。Skill 不包含模型或完整 Runtime；**只复制这一个 SKILL.md 到全局目录不能安装整个平台**。

### 第一次调用：在聊天框输入，不是在终端运行

1. 按上文获取 `codex/platform-v3-lifecycle` 分支，并完成对应系统的 setup 和自检。仓库已带 Skills/Agent 文件，setup 不把它们安装到用户全局目录。
2. 在 Codex 打开这个平台仓库根目录并新建项目内任务。让宿主列出实际可用 Skills 和专业 Agent，确认 `platform-orchestration` 及所需角色已加载；文件存在不代表当前会话已加载。
3. 在 **Codex 聊天输入框**粘贴下面的例子。`$platform-orchestration` 是 Skill 提示，不是 PowerShell/Bash 命令；也可直接说“使用 platform-orchestration”。

```text
$platform-orchestration
帮我做一个 Python 个人记账 Web 应用，放在 D:/projects/my-expenses。
先分析用户、流程、数据、风险和验收标准，只问影响产品方向的关键问题。
说明假设，普通工程细节由你判断；明确需求后分模块开发、独立测试和审查。
将真实 Agent 工作登记到看板，最后给我启动方法、测试报告和未完成项。
```

路径是示例，请替换。推荐保持平台为 Codex 工作区，明确指定单独的应用目录；不要把业务代码混进平台源码或覆盖已有内容。宿主须有目标目录访问权限。若 Skill 未发现，重新打开正确的平台项目并核对清单；也可明确要求读取上述完整 `SKILL.md` 及其引用文档，不能假装安装/加载成功。

4. 首轮应看到初始需求模型、事实/假设和少量关键问题；需求明确后，应有真实任务、Agent 交接、设计、代码、测试模型/用例/执行结果、独立审查及交付说明。缺少环境的检查必须标注未执行。
5. 按下一节打开看板，选择该应用项目。结束聊天不意味着后台继续开发；下次用续作提示恢复原项目记录。

其他可复制的聊天提示：

```text
使用 platform-orchestration，继续 D:/projects/my-expenses，恢复已有项目与任务，不重新生成完成内容。
暂停当前开发；确认实际宿主 Agent/进程已停止，并列出仍然未知的执行结果。
使用 requirement-analysis，只分析这个应用的需求和验收标准，本轮不开发。
使用 testing，先为已实现模块建立测试模型，再执行适用测试并报告真实结果。
```

单独调用专业 Skill 仅限定本次工作方法，不自动执行全生命周期。实际并发、角色可用性和启动由宿主决定，开发者不能作为自己唯一的 tester/reviewer。

在 Codex 打开仓库，先读规则和当前事实再开发。

新项目短提示词：

> 使用 `platform-orchestration`：为“<业务目标>”启动本地项目。先读取 `AGENTS.md`、当前 Git 状态和 Runtime snapshot，明确需求与验收边界；将真实宿主 Agent 工作登记到看板，关键业务分歧再问我。

续作短提示词：

> 使用 `platform-orchestration`：续作 `<仓库或目录>` 的“<目标>”。先读取源码、Git、Runtime `lifecycle`/`report` 和项目文档；不重建已完成内容，按缺失证据和未完成 Gate 前置条件推进。

Skill 是工作方法约束而不是服务启动器。它要求宿主先做快照、采用真实开发/测试/审查角色并关联实际结果。Codex 宿主 delegation 与 Runtime 不同，后者不会无人值守地启动云端 Agent。

可先生成无模型的待确认需求草案：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform discover "开发一个内部测试管理系统"
```

`discover` 结果标为 `baseline_no_model`；`freeze` 只根据确认答案生成 DRAFT SRS/RTM。两者都不能替代需求访谈、评审或人工批准。

## 运行台、看板与 CLI

默认状态库为当前目录 `.rd-platform/state.db`。启动本地看板：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform serve
# 打开 http://127.0.0.1:8020/
```

看板只监听 `127.0.0.1`，读取持久化的项目、任务、Agent、Run、事件和 V3 生命周期摘要。V3 页面实际显示项目状态、当前 Gate、已决定 Gate 数（明确提示“不代表全部通过”）、工件数、追踪缺口、未关闭缺陷与分页明细。展开证据时自动刷新暂停以避免折叠内容，可手动刷新；因分页，完整记录须使用 CLI cursor。

浏览器不是任意命令、Run 完成、人工批准、Gate 决定、发布或部署接口；这些只可由受信任 CLI/宿主在真实证据存在后处理。

常用只读命令（替换真实 `PROJECT_ID`，不得伪造 cursor）：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform snapshot
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform snapshot --project-id PROJECT_ID
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle --project-id PROJECT_ID --limit 200
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle-collection --project-id PROJECT_ID artifacts --limit 200
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle-report --project-id PROJECT_ID
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform project-export --project-id PROJECT_ID --output-dir NEW_DIRECTORY
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform report --project-id PROJECT_ID
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-probe
```

`report` 是 V2 `MODULE_QUALITY` 报告；`lifecycle-report` 从 Runtime 的一致读取视图分页收集**全部**版本化生命周期集合，再生成当前版本已声明 Test Case 报告，不能把第一个 500 条页面当作全量。二者范围/分母不同。`lifecycle-report` 不改变 Gate；仅有 `complete_snapshot=true` 或 Case 全 PASS 不足以推荐发布，还需满足 Gate、追踪、缺陷和发布证据等条件。

### 全量报告、项目导出与版本绑定的自动化 Case

`project-export` 生成活动项目的只读文档索引包。`NEW_DIRECTORY` 的父目录必须已存在且可信，目标目录本身必须是新的；命令拒绝覆盖、链接/穿越路径和已有输出。导出保存一致读取时的工件/版本/追踪/Gate/证据索引、正式 JSON/Markdown 测试报告、集合计数和项目记录 fingerprint，并以 `export-manifest.json` 的 `COMPLETE` 与逐文件 SHA-256 作为写完标记。它不修改源数据库或 Gate，且故意不复制源码、内联工件正文、原始命令输出或秘密；它是**文档投影，不是可执行备份、Git 归档或批准包**。

对已版本化的功能/一般自动化用例，使用下列公共 CLI；命令行不接收或覆盖测试命令：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db PATH test-run --project-id ID --case-id TC-ID --case-version N --executor-id REAL_TESTER --timeout 60
```

`test-run` 只从该精确 Case 版本的 `automation.argv` 读取 argv，并以受信任宿主声明、已登记为 tester 的 `executor-id` 启动；它会重新校验项目、Case 版本、Test Model、需求和受试代码的锁定引用。该 ID 仅校验 Runtime 中的角色，不是身份认证，也不会模拟另一个 OS 用户；独立性仍须由真实宿主派发与证据证明。Case 必须是 `BASELINED` 或 `APPROVED`，且自动化定义应类似：

```json
{
  "automation": {
    "status": "AUTOMATED",
    "method": "argv",
    "tool": "python",
    "entrypoint": "tests/assertions.py",
    "argv": ["{python}", "tests/assertions.py"],
    "cwd": ".",
    "subject_refs": [{"type": "CODE_CHANGE", "id": "CODE-xxx", "version": 1}]
  }
}
```

每个 `CODE_CHANGE` 必须是 `BASELINED`/`APPROVED`、以仓库内 `path` 和 SHA-256 固定的文件工件，不能用 inline 内容替代。runner 仅支持其已声明的 `{python}`/`{root}` 占位符、相对 `cwd` 和 argv；它不是任意代码沙箱。`PERFORMANCE`、`STRESS`、`STABILITY` Case 被此通用 runner 拒绝，必须使用记录实际指标的专用 metrics adapter，不能用 exit 0 伪造 NFR 指标。

受信任 CLI 可记录真实 V2 质量 Run。先创建真实任务、登记角色，并让 developer 先完成 implementation；tester/reviewer 不得自证：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform run --task-id TASK_ID --agent-id TESTER_ID --phase unit --cwd . --timeout 60 -- .\.venv\Scripts\python.exe -m unittest tests.runtime.test_stack_harness -v
```

`run` 用 `--` 后 argv 执行，不使用 shell，并记录启动、退出码、输出摘要、超时和结束状态。退出码 0 仅表示命令成功，不能推导测试充分、Gate 通过或产品验收。

### 暂停、恢复与宿主进程边界

- Runtime `pause` 使活动 Run 失效并停止后续 Runtime 调度，**不会**终止 Codex、终端、WSL、浏览器或远端系统已启动的进程。
- 取消外部工作要由宿主/终端真实执行，再记录真实结果；不能将“已暂停”写为“进程已终止”。
- `resume` 只恢复可恢复暂停；FAILED 任务必须 retry。`modify` 创建新 revision 并使下游结果过期；`reject`/`skip` 从不等于 PASS。
- 关闭看板只停止 HTTP 前台进程，不会停止其他写入者或外部 Agent。

使用独立库演练，避免混入正式记录：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db .rd-platform\trial.db snapshot
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db .rd-platform\trial.db serve --port 8021
```

## 五类应用：构建与测试

Harness 只接受受控 `manifest.json` 的 argv，构建产物在 `.rd-platform/build/<id>`。它是受信任本地执行适配器，不是隔离未知或恶意代码的沙箱。

```powershell
# C++：Python 驱动 WSL Ubuntu g++；Windows 原生 C++ 不是当前已验证路径。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\cpp_inventory\manifest.json --phase build --phase unit --phase integration

# Python：manifest 仅声明 build/unit；未声明 integration 应为 NOT_EXECUTED。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\python_expenses\manifest.json

# Web：Node 单测；真实浏览器用户流另行独立观察。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\web_notes\manifest.json --phase unit
Push-Location examples\multistack\web_notes; python -m http.server 8080 --bind 127.0.0.1; Pop-Location

# Java：需要实际可用 javac/java；已有记录使用 JDK 8。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\java_booking\manifest.json --phase build --phase unit --phase integration

# 微信：仅 Node 领域模块和 fake-wx 页面 adapter，不是原生小程序执行。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\wechat_expenses\manifest.json --phase unit --phase integration
```

`stack-probe` 探测本机工具。缺少工具为 `NOT_AVAILABLE`，未声明阶段为 `NOT_EXECUTED`，均不是 PASS。现有证据中 C++ 使用 WSL、Web 有一次真实浏览器用户流；微信开发者工具、真机、真实 `wx` 存储和发布仍无证据。详见 [Harness](docs/platform-v3/stack-harness.md)、[浏览器验证](docs/platform-v3/browser-validation.md) 和 [真实生命周期验证](docs/platform-v3/live-lifecycle-validation.md)。

生成本地交付归档（不是发布）：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\cpp_inventory\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\python_expenses\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\web_notes\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\java_booking\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\wechat_expenses\manifest.json
```

记录 ZIP/source/file SHA-256、Git SHA、命令、环境和操作者；归档成功不构成 `REL-*`、部署成功或客户签收。

## MCP、秘密与已有仓库接入

Windows `setup.ps1` 会重写 `.codex/config.toml` 中 `company_context` 的绝对路径，并只转发以下**变量名**：

```text
COMPANY_LOCAL_ROOTS
REDMINE_BASE_URL, REDMINE_API_KEY, REDMINE_PROJECT
RAGFLOW_BASE_URL, RAGFLOW_API_KEY, RAGFLOW_DATASET_ID
GITLAB_BASE_URL, GITLAB_TOKEN, GITLAB_PROJECT_ID
```

`tools/mcp/company-context/.env.example` 只提供变量清单。真实 URL、token、cookie、password、授权头和私钥必须保存在操作系统安全环境变量或批准的秘密管理器，绝不写入 README、样例 env、任务证据、终端截图或 Git。配置后重开终端/Codex，再运行 `scripts/validate_platform.py` 获取当前机器 health 结果。MCP 仅读取批准的 `COMPANY_LOCAL_ROOTS` 下本地文档；Redmine/RAGFlow/GitLab 的可用性取决于真实网络、权限和服务契约，未配置时应如实报告不可用。

接入已有仓库：

1. 从独立分支/worktree 开始，读取其 `AGENTS.md`、需求/设计/测试资料、Git 状态、近期提交和证据；不要批量重写历史。
2. 使用独立 `.rd-platform/<项目>.db`，以路径、版本和摘要登记既有工件，逐步补充真实 REQ/DES/TASK/CODE/TC/BUG/REL 链接。
3. 原始测试模型来源缺失时保留 `NOT_AVAILABLE`，显式 adopt 新版本并重跑适用 Case；不得把 v2 结果覆盖成 v1 历史。
4. 对已有代码的 verification-only 工作，用 V3 work 与 `test_execution` 记录独立实测；不要为满足 V2 implementation→unit 顺序而补造历史 implementation PASS。
5. `lifecycle.initialize` 的 active Runtime 记录只初始化该项目事实模型。正式 Gate 仍需项目自己的中央 Gate Register、完整工件、可解析证据和有权决定；不会改变本仓库顶层模板状态。

## 报告、备份、恢复与真实状态

- `snapshot` 为当前 Runtime 状态；`lifecycle` 为版本化快照；`lifecycle-collection` 以 cursor 读完整集合；`report`/`lifecycle-report` 范围不同。
- Evidence Status 只能是 `PENDING`、`NOT_AVAILABLE`、`NOT_EXECUTED`、`INFERRED`、`OBSERVED`、`VERIFIED`。`BLOCKED` 仅用于允许的 Gate 或验证结果域。
- Gate 先 assessment，再由有权人以真实、可解析证据决定。人工批准、已执行测试、部署、回滚、客户验收和 defect closure 都不能从文档、fixture、模型输出或 exit 0 推导。
- 五样例已完成 legacy model v2 adopt、Case v2 和独立重测；其报告仍为 `recommend_release=false`，G0/G7 无正式决定。见 [live lifecycle validation](docs/platform-v3/live-lifecycle-validation.md)。
- Python 费用工具的逐 REQ/NFR 本机生命周期项目已有 37/37 当前 Case 的真实 PASS、7/7 RTM `COMPLETE`；经独立评审后 G0–G8 为 `DECIDED PASS CURRENT`。其 finalization 状态为 `G0_G8_COMPLETE_G9_PENDING`，G9–G11 仍为 `NOT_EVALUATED`，没有 human acceptance，且不建议发布。见 [Python 生命周期核对](docs/platform-v3/python-lifecycle/README.md)、[独立评审](docs/platform-v3/python-lifecycle/independent-review.md) 与 [完成交付记录](docs/platform-v3/completion-delivery.md)。

### 已实现功能与已观察证据

| 项目 | 当前事实与边界 |
| --- | --- |
| 全量报告、只读项目导出、Case 绑定 runner | 已实现并有本机验证记录。全量报告不截断首个页面；导出拒绝覆盖且不含源码/秘密；`test-run` 只能运行已基线的版本绑定 argv，普通命令结果不等于 Gate。见 [导出说明](docs/platform-v3/project-export.md) 与 [test-run 验证](docs/platform-v3/test-run-validation.md)。 |
| SQLite 读取容量 | 已观察到 synthetic `capacity --profile full`：100 projects、100,000 artifact versions、1,000,000 events，终端 JSON 为 PASS，129.7199 s、294,764,544 bytes、无公开读取错误。它只衡量 `Runtime.lifecycle_collection`/`Runtime.lifecycle_snapshot` 的本地 SQLite 读路径，不是生产吞吐、写入性能、SLO、Gate 或发布结论。见 [性能验证](docs/platform-v3/performance-validation.md)。 |
| 8 小时 soak | 同一 run `soak-9241634446774e1291126d1cc1c2a53b` 的 terminal 已 `PASS`/exit 0：elapsed 28800.740279s、4,952 样本、最大相邻 gap 8.191594s、0 read errors；terminal SHA-256 `00BE7586AD05A8CDD03CFC510C7C730021920BEDB8EFDC1225E4A24765A398CD`。它仅覆盖旧源码 `E482F1E2DD6A5A7AB42736AE227DB56B8B5D12F2D6C1D5FA1F3293F78BEDBC9A` 的合成 SQLite 公共读路径，不能外推写入、完整系统/安全、生产、Gate、release 或验收。见[性能验证](docs/platform-v3/performance-validation.md)。 |
| GitHub Actions CI | 冻结源码 `fbd9b36` 对应 [run 34095997725](https://github.com/leongibhub/codex-rd-platform/actions/runs/34095997725)，于 2026-09-07 07:48:30 UTC 完成 SUCCESS：Windows、Ubuntu 的 Runtime/platform 和五栈 manifest 共 4/4 jobs 成功。本机冻结回归另为 Runtime 307（2 skip）、platform 134、independent 113（1 skip），均 OK；这些不是 CI 测试计数。旧 `026263f` 的失败保留。后续文档提交不冒充已被该源码 CI 覆盖；CI 不等于 Gate、生产部署或验收。详见 [CI 执行记录](docs/platform-v3/ci-execution.md)。 |
| Python 逐需求生命周期收口 | 有界的既有 Python 费用 CLI 项目已完成 37/37 当前 Case PASS、7/7 RTM `COMPLETE` 和 G0–G8 `DECIDED PASS CURRENT`；这不是 G9 人工验收、生产部署或发布建议。G9–G11 保持 `NOT_EVALUATED`，finalization 为 `G0_G8_COMPLETE_G9_PENDING`。 |

容量/soak 使用专用基准脚本和隔离的全新输出目录；不要指向项目状态库或复用已有输出：

```powershell
# 先阅读 smoke JSON，再为 full run 预留本机 CPU/磁盘。
& .\.venv\Scripts\python.exe -X utf8 scripts\benchmark_lifecycle.py capacity --output-dir D:\perf\lifecycle-full --profile full

# 授权后启动长稳读路径观察；checkpoint 是唯一可更新文件，terminal JSON 才是完成记录。
& .\.venv\Scripts\python.exe -X utf8 scripts\benchmark_lifecycle.py soak --output-dir D:\perf\lifecycle-soak-8h --profile full --duration-seconds 28800 --interval-seconds 1
```

运行中读取 `<output-dir>/perf-<run-id>-checkpoint.json`（capacity）或 `<output-dir>/soak-<run-id>-checkpoint.json`（soak）；结束时读取同前缀 `*-terminal.json`，并核对 status、预算和 `seed_mode=synthetic_batch_sql`。长稳数据同样只覆盖公开读操作，不覆盖 Runtime 写入吞吐、生产用户流或完整系统稳定性。

备份前停止看板、CLI 和其他 SQLite 写入者，保留带时间戳的 `.rd-platform/state.db` 副本；不要将数据库、运行输出、归档或凭据提交 Git。同步保存代码 Git SHA、工件 SHA-256 和外部证据 locator；恢复后用 `snapshot`、`lifecycle` 与摘要比对，恢复不会补齐测试/批准事实。代码回退用审查过的 `git revert` 或已知版本；V3 只增表，回退 V2 代码不应删除 `lc_` 表。数据库仅能从验证过的备份恢复，当前没有通用降级或自动 DROP 表方案。真实进入 release 域后才由 release manager 用 `release.rollback` 记录操作者、原因、环境和证据；代码回退或 exit 0 不代表生产回滚成功。

### 尚未实现与尚未验证的区别

**最终愿景尚未全部完成：当前交付是宿主协作版，不是无人值守云平台。** 下表区分实现缺口和外部验证条件。旧截图的“Linux MCP 未交付”“审批 provider 不可用”不是当前源码状态；已有适配器也不能代替真实授权、部署和验收。每个新应用都需要自己的证据。

| 边界 | 当前状态 | 声称完成前必须具备 |
| --- | --- | --- |
| 无人值守云端 Agent 服务 / 多租户平台 | 未实现 | 云端服务、认证/隔离、调度队列、运维部署和实际端到端验证；本地 worker-service 不能替代。 |
| 受信任 worker-service（非云端 Agent） | `OBSERVED`：当前源码提供持久 worker、租约/心跳/取消、受控 `argv` 与 no-tools Responses 文件提案；生产 Codex backend 已 fail-closed 禁用。 | 需要受保护配置、真实工作项和可观察的宿主进程；当前无成功常驻 worker 或 live Responses 执行事实，不能声称自动完成项目。 |
| 正式 G0–G11 / 人工验收 | 未决定 | active 项目中央 Gate Register、完整 BG→PRD→REQ→DES→TASK→CODE→TC→BUG→REL 追踪、真实证据和有权决定。 |
| SSH 审批 provider | `OBSERVED`：可选 Ed25519 适配器和 challenge/register CLI 已在源码中；无配置的默认 Runtime 仍拒绝。 | 需要操作员保护的 signer/trust 配置、外部签名和真实授权；当前没有本项目人工批准或 Gate 决定。 |
| 生产部署、发布、回滚 | `NOT_EXECUTED` | 授权环境、`REL-*`、安装/回滚步骤、已知问题、真实操作者和环境证据；Git push 不替代。 |
| 微信原生 | `NOT_AVAILABLE` | 开发者工具、授权项目、真实导入/运行/存储验证，必要时真机和发布权限；Node fake-wx 不替代。 |
| 生产/用户流写入性能、跨浏览器/跨 OS、完整安全矩阵 | `NOT_EXECUTED` | 各自的受控环境、负载/时长/指标、原始输出和独立复核；不可用 synthetic SQLite 读取 benchmark 外推。 |
| Linux MCP 一键安装 | 已实现并验证：`scripts/setup.sh` 提供本仓 venv、配置生成和 validator；源码 `fbd9b36` 的 Ubuntu job `101659687365` 中 native setup 与 repeat-install 均 SUCCESS。 | 见 [CI 执行记录](docs/platform-v3/ci-execution.md)；该 Ubuntu 结果不覆盖所有 Linux 发行版、生产部署或人工验收。 |

不要将 loopback 看板暴露到网络。Harness 有路径/argv 约束但不是恶意代码沙箱；不可信代码应在独立受控环境运行。命令、日志和证据均不得打印秘密。

## 延伸阅读

- [V3 本地运行、操作与恢复](docs/platform-v3/README.md)
- [能力矩阵与已知边界](docs/platform-v3/capability-status.md)
- [发布就绪性](docs/platform-v3/release-readiness.md)
- [独立平台测试](docs/platform-v3/independent-platform-tests.md) 与 [Runtime 审查](docs/platform-v3/runtime-review.md)
- [五栈样例经验](docs/platform-v3/lessons-learned.md)
- [V2 Runtime 使用说明](docs/platform-v2/README.md)

<a id="cr-v3-003-执行端受控使用当前实现待最终复审"></a>

## CR-V3-003 执行端：受控使用

本节是新执行端的当前 CLI/JSON 契约，不是“已部署”声明。控制面和项目工作区仍应使用**不同目录**，但这只是降低误操作/备份混淆的运维措施，不能隔离同一 OS 身份下的模型。已确认 Codex auto-review 可越过 workspace 边界读写无害 sentinel，故生产 Codex backend 已 fail-closed 禁用。以下 `PROJECT_ID`、操作员、路径、Git SHA、证据 ID 与 hash 都是占位符，必须替换为本次真实值。

### 从粗略想法创建可恢复工作清单

`orchestrate-start` 以 `--request-id` 幂等：同一控制库中对相同请求重跑会返回已创建的启动事实，不会再造第二套 G0–G11 work order。它只建立 DRAFT BG、active 生命周期和 `PLANNED` 工作清单；不会创建批准、测试结果或 Gate PASS。

```powershell
$controlDb = 'D:\rd-control\state.db'                 # 不在项目 workspace 内
$workspace = 'D:\workspaces\inventory-service'        # 已存在、受信任的 Git 工作区
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb orchestrate-start `
  --name 'Inventory service' `
  --idea '给出真实业务目标及已知约束；未知项由需求工作项澄清' `
  --repository-root $workspace `
  --request-id 'bootstrap-inventory-20260906-001'
```

保存返回的 `project_id`，再以相同参数/`request-id` 演练重试。不要将控制库复制进 `$workspace\.rd-platform`；但不要把路径分离误认为模型不可访问的安全保证。

新建流程启用[严格阶段策略](docs/platform-v3/orchestration-policy.md)：前一工作生成 DRAFT 并不代表阶段通过，下一阶段领取任务前必须有前一 Gate 的当前有效 PASS。查看具体原因：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb orchestrate-status --project-id 'PROJECT_ID'
```

运行台的“阶段工作与推进条件”显示相同的职责、任务、原因、输入输出和依赖。`ALLOWED` 只表示阶段前提，不是执行授权；真实身份、租约、重试安全仍在领取时检查。具体状态解释与 Linux 命令见[编排状态指南](docs/platform-v3/orchestration-status.md)。已有通用项目不会被静默升级或重建。

### 登记实际角色并启动 Worker

Worker 配置中的每一位 `agent_id` 必须先在**同一控制库**登记，且 role 精确匹配。可接受的实际 role 为 `requirement_analyst`、`researcher`、`product_manager`、`architect`、`developer`、`tester`、`reviewer`、`documentation_manager`、`release_manager`。例如（每个 ID 应对应实际宿主责任，而不是假冒的人）：

```powershell
$roles = 'requirement_analyst','researcher','product_manager','architect','developer','tester','reviewer','documentation_manager','release_manager'
foreach ($role in $roles) {
  & .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb command agent.register ("{`"id`":`"host-$role`",`"role`":`"$role`"}") --request-id "register-$role-001"
}
```

将如下文件保存到控制库所在、权限受限而且**不提交 Git**的位置，例如 `D:\rd-control\worker-service.json`。当前安全默认是 `responses` proposal backend：HTTPS Responses 请求固定 `tools:[]`、`tool_choice:"none"`，模型只返回结构化文件提案；受控宿主校验版本绑定上下文、路径/大小和 CAS 独占创建后，才登记新 artifact 为 `DRAFT`。每个可能 create 或 update 的仓库相对路径（包括尚不存在的新文件）都必须显式列入对应 worker 的 `source_paths`；空列表不能发布提案。`OPENAI_API_KEY` 当前在本机为 `NOT_AVAILABLE`，所以不得把该示例写成已实际完成的 live Responses run。`argv` 仅用于可信宿主已批准的命令，仍不是未知代码沙箱。

```json
{
  "project_id": "PROJECT_ID",
  "repository_root": "D:\\workspaces\\inventory-service",
  "max_concurrency": 3,
  "poll_interval_seconds": 0.5,
  "workers": [
    {"agent_id":"host-requirement_analyst","role":"requirement_analyst","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/requirements.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-researcher","role":"researcher","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/research.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-product_manager","role":"product_manager","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/product.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-architect","role":"architect","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/design.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-developer","role":"developer","lease_seconds":300,"timeout_seconds":1200,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["src/app.py","docs/implementation.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-tester","role":"tester","lease_seconds":300,"timeout_seconds":1200,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["tests/system_test.py","docs/test-report.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-reviewer","role":"reviewer","lease_seconds":300,"timeout_seconds":1200,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/review.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-documentation_manager","role":"documentation_manager","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/closure.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}},
    {"agent_id":"host-release_manager","role":"release_manager","lease_seconds":300,"timeout_seconds":900,"max_output_bytes":65536,"safe_to_retry":false,"source_paths":["docs/release.md"],"backend":{"type":"responses","model":"MODEL_ID","api_key_env":"OPENAI_API_KEY","endpoint":"https://api.openai.com/v1/responses","max_output_tokens":2048}}
  ]
}
```

先运行一轮可观察调度；它至多处理当时可认领的工作项，输出 `IDLE`/`DISPATCHED`/`WAITING_USER`/`FAIL` 不是 Gate 结论：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb worker-service --config D:\rd-control\worker-service.json --once
```

省略 `--once` 才是前台常驻服务；以经批准的服务管理器或受控终端运行，并将 stdout/stderr 写到不含秘密的受保护日志。生产 Codex `auto-review` 已禁用，不能通过 `approval_mode`、`persist_session`、路径分离或额外 CLI flag 恢复它。Responses proposal 不给模型文件或命令工具；宿主在 CAS 写入、hash/路径/版本校验成功后才建 DRAFT artifact。停机、暂停或工作项失效时，应核对 `lifecycle`/`work.reap` 及实际进程状态；不能把 OS 进程终止或 `pause` 自动写成取消成功。未知副作用的过期租约只有 `safe_to_retry: true` 时才会重试。

### 外部 SSH 签名审批

下面的 JSON 是待签审批请求，不含私钥。`canonical bytes` 是 CLI 写出的 challenge 的 UTF-8 `Store.dumps` 字节，不能重新格式化、手改、重新序列化或替换请求后再使用同一个签名。

```json
{
  "project_id": "PROJECT_ID",
  "kind": "human_approval",
  "status": "VERIFIED",
  "locator": {"inline_json": {"external_record": "APPROVAL-RECORD-REFERENCE"}},
  "observed_at": "2026-09-06T12:00:00+00:00",
  "metadata": {"gate_id": "G9", "decision": "APPROVE", "statement": "Actual authorized decision text.", "artifact_refs": [{"type": "REQ", "id": "REQ-001", "version": 1}]}
}
```

`provider.json` 留在受保护目录，包含真实项目 ID、受权人和只含**公钥**的 `allowed_signers`；私钥、passphrase、token 不进入本平台或 Git：

```json
{"provider_id":"corp-approval-ssh-2026","allowed_signers":"D:\\secure\\approval\\allowed_signers","ssh_keygen":"C:\\Windows\\System32\\OpenSSH\\ssh-keygen.exe","authorizations":[{"operator":"approved-operator","projects":["PROJECT_ID"],"gates":["G9","G10","G11"]}],"challenge_ttl_seconds":300,"timeout_seconds":10,"max_output_bytes":4096}
```

```powershell
$req = 'D:\secure\approval\request.json'; $provider = 'D:\secure\approval\provider.json'; $challenge = 'D:\secure\approval\challenge.json'
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb approval-challenge --provider-config $provider --request $req --operator approved-operator --challenge $challenge
# 人在平台外、经 SSH 私钥进行签名；不要把 key/path/passphrase 写到平台配置或日志。
ssh-keygen -Y sign -f PATH_TO_PRIVATE_ED25519_KEY -n rd-platform-approval $challenge
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb approval-register --provider-config $provider --request $req --operator approved-operator --challenge $challenge --signature "$challenge.sig"
```

challenge 只表示“等待签名”。register 时会重新计算当前项目/Gate/决定/工件版本/策略 binding，拒绝过期、重放、未授权、Agent 同名身份或任一漂移；签名认证也不替代 Gate 决定和客户验收。

### 试用部署、正式部署与回滚

`deploy-run` 只运行配置中明确 argv；不会从环境名、HTTP 或模型输出拼命令。`trial` 保存 durable receipt，但永远不写 release/deployment 事实。下面是**字段完整**的 trial 形状；所有脚本必须在 `cwd` 下，所有 `source_hashes` 必须是运行前由真实文件计算的 SHA-256。receipt 目录必须是明确、可恢复的本地目录；formal 模式还要求其位于项目根内，才能将 receipt 作为 Runtime 受控引用。

```json
{"project_id":"PROJECT_ID","environment":"isolated-local","mode":"trial","operation_id":"trial-20260906-001","cwd":"D:\\workspaces\\inventory-service\\ops","source_hashes":{"deploy.ps1":"ACTUAL_SHA256","health.ps1":"ACTUAL_SHA256","rollback.ps1":"ACTUAL_SHA256","rollback-health.ps1":"ACTUAL_SHA256"},"deploy":{"argv":["powershell","-NoProfile","-File","deploy.ps1"],"timeout_seconds":300,"output_limit_bytes":65536,"idempotent":true},"health":{"argv":["powershell","-NoProfile","-File","health.ps1"],"timeout_seconds":60,"output_limit_bytes":16384},"rollback":{"argv":["powershell","-NoProfile","-File","rollback.ps1"],"timeout_seconds":300,"output_limit_bytes":65536},"rollback_health":{"argv":["powershell","-NoProfile","-File","rollback-health.ps1"],"timeout_seconds":60,"output_limit_bytes":16384},"receipt_dir":"D:\\workspaces\\inventory-service\\.rd-platform\\deployment-receipts"}
```

先用 `Get-FileHash` 更新每个脚本 hash，然后执行；相同 `operation_id` 和相同 fingerprint 才允许读取已完成 receipt，任何漂移或遗留 `STARTED` 记录都必须人工协调，不能盲目重跑：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb deploy-run --config D:\rd-control\trial-deploy.json --action deploy
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db $controlDb deploy-run --config D:\rd-control\trial-rollback.json --action rollback
```

`formal` 在上述字段外还必须有 `release_id`、非 Agent 的 `operator`、已登记 `release_manager` 的 `executor_id`、当前 `G10 PASS`、`READY` release、`environment_ref`（例如 `{"type":"EVIDENCE","id":"EVD-ENV-001","version":1}`，且证据 kind 为 `deployment_environment`）和非空 `evidence_artifact_refs`（例如 `[{"type":"DOC","id":"DOC-REL-001","version":1}]`）；Runtime 会在物理命令前后再次校验。试用成功、exit 0 或 health 成功均不满足这些条件，也不等于生产成功。健康失败会执行已声明的 rollback 与独立 `rollback_health`；两者的真实结果保留在 receipt，不能以“已尝试”改写为成功。

### Linux 原生安装

在目标 Linux checkout 内执行（不使用 sudo、不写 global Git/Python、不会删除已有数据）：

```bash
git config --local user.name 'YOUR_APPROVED_DISPLAY_NAME'
git config --local user.email 'your-approved-address@example.invalid'
./scripts/setup.sh --python-command python3.11
# 已有依赖、只需要重新生成本地 MCP 配置和 health 时：
./scripts/setup.sh --skip-dependency-install
.venv/bin/python -X utf8 -m rd_platform --help
```

脚本会先验证 Git 身份与 Python 3.11+，再创建/复用本仓 `.venv`，运行 `pip check`、`write_local_config.py` 与 `validate_platform.py`。只有实际输出 `Setup complete.` 且 validator 成功才是该机器的安装/health 证据；失败保留诊断，修复后可重跑。

当前执行端与严格编排的模块质量链已完成独立测试和复审，已登记结果见[交付记录](docs/platform-v3/completion-execution-delivery.md)。本机冻结回归为 Runtime 307 项（2 skip）、platform 134 项、independent 113 项（1 skip），均 OK；独立 tester 另实际执行了五样例的全部 11 个声明阶段及黑盒回归。它们不是项目级验收：live Responses、真实人类批准、生产部署和微信原生验证仍需真实外部条件。旧 live Codex smoke 的失败保持历史，不改写为成功。详见 [执行端设计](docs/platform-v3/completion-execution-design.md)、[worker service](docs/platform-v3/worker-service.md)、[审批提供方](docs/platform-v3/approval-provider.md)、[部署执行器](docs/platform-v3/deployment-executor.md) 和 [Linux 安装](docs/platform-v3/linux-setup.md)。
