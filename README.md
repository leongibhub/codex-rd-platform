# Codex R&D Platform

> 中文（默认） · [English](README.en.md)

这是一个供 **Codex 宿主协作** 使用的本地研发控制面：它将项目、任务、质量检查、版本化生命周期工件、测试执行、缺陷、Gate 候选评估和多技术栈验证存入 SQLite；源代码和文档事实仍在 Git 工作区中。

它不是自动调用模型的云服务、持续运行的后台 daemon、多租户系统或生产发布平台。Codex（或另一受信任宿主）实际派发 Agent、运行和取消外部进程；Runtime 只校验、记录和展示已经发生的工作。请先阅读 [V3 运行说明](docs/platform-v3/README.md) 与 [V3 交付记录](docs/platform-v3/delivery-record.md)。

## 当前范围与版本

- V3 使用 GitHub 分支 `codex/platform-v3-lifecycle`，本轮续作基线为 `2d77904`；当前交付提交及真实 CI 结果见[后续交付记录](docs/platform-v3/completion-delivery.md)。它**尚未合并到 `main`**，默认分支 clone 不含本轮 V3 内容。
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
git rev-parse --short HEAD       # 本说明检查时为 2d77904
git status --short
```

已有 clone 时：

```powershell
git fetch origin codex/platform-v3-lifecycle
git switch --track origin/codex/platform-v3-lifecycle
git status --short
```

合并发生前不要把 `main` 当作本文描述的 V3 基线。改动请使用自己的分支/worktree，先检查 Git 状态和近期历史，并保留其他协作者的未提交修改。

## 安装和自检

### Windows（已提供的一键路径）

前置条件：Git、PowerShell、Python 3.11+，以及仓库中的 `git user.name`、`git user.email`。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --help
& .\.venv\Scripts\python.exe -X utf8 scripts\validate_platform.py
```

`setup.ps1` 创建或复用 `.venv`，安装 `tools/mcp/company-context/requirements.txt` 的受限依赖，运行 `pip check`，创建 `knowledge\local`，生成当前工作区 MCP 绝对路径，并运行平台校验。它默认不升级 pip，也不写用户级环境变量。仅在准备好依赖时使用 `-SkipDependencyInstall`；仅 `-PersistLocalRoot` 会持久化 `COMPANY_LOCAL_ROOTS`。

需要复制到另一个**空**目录时，可从源仓库运行 `./install-to-D.ps1`。默认目标是 `D:\codex-rd-platform`；非空目标会被拒绝，`-Force` 会合并/覆盖文件，操作者必须确认目标，且不得选源目录或其子目录。

### Linux（可验证的手动 venv 路径）

仓库目前**没有 Linux 等价的一键 setup 脚本，也没有已验证的 Linux MCP 配置生成器**；`scripts/write_local_config.py` 会生成 Windows `.venv\Scripts\python.exe` 路径。下面只覆盖 Runtime/CLI/Harness 依赖，不能据此声称 MCP 已配置：

```bash
python3 --version                     # 必须为 3.11 或更高
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r tools/mcp/company-context/requirements.txt
python -m pip check
python -X utf8 -m rd_platform --help
python -X utf8 -m rd_platform stack-probe
```

如需 Linux `company_context` MCP，本地管理员必须先审阅并建立客户端支持的 launcher，确保解释器、`server.py` 和 `cwd` 都在仓库内，再单独执行 MCP health check。不要直接套用 Windows `.codex/config.toml`，也不要把尚未交付的 Linux 配置写成已验证。

## 在 Codex 中开始或续作

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

`test-run` 只从该精确 Case 版本的 `automation.argv` 读取 argv，并以真实 tester 身份启动；它会重新校验项目、Case 版本、Test Model、需求和受试代码的锁定引用。Case 必须是 `BASELINED` 或 `APPROVED`，且自动化定义应类似：

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
| 8 小时 soak | 已启动，运行目录为 `.rd-platform/benchmark-soak-8h-20260906-1`；当前只有同一 run 的 checkpoint，没有 terminal JSON，因此没有完成/PASS 结论。宿主的 30 分钟 heartbeat 仅用于完成/失败通知，不替代 benchmark 结果。 |
| GitHub Actions CI | Windows/Linux workflow 与本机契约检查已实现；GitHub 在线执行仍需 push 后读取实际 Actions 记录，在此之前是 `NOT_EXECUTED`，不等于 CI 通过。见 [CI 验证契约](docs/platform-v3/ci-validation.md)。 |
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

| 边界 | 当前状态 | 声称完成前必须具备 |
| --- | --- | --- |
| 自动云端 Agent / daemon | 未实现 | 服务设计、认证、队列、监控、部署和实际运行证据；当前仅 Codex 宿主显式派发。 |
| 正式 G0–G11 / 人工验收 | 未决定 | active 项目中央 Gate Register、完整 BG→PRD→REQ→DES→TASK→CODE→TC→BUG→REL 追踪、真实证据和有权决定。 |
| 审批 provider | `NOT_AVAILABLE` | 已认证 provider、真实身份/授权和可验证 human approval；默认拒绝登记。 |
| 生产部署、发布、回滚 | `NOT_EXECUTED` | 授权环境、`REL-*`、安装/回滚步骤、已知问题、真实操作者和环境证据；Git push 不替代。 |
| 微信原生 | `NOT_AVAILABLE` | 开发者工具、授权项目、真实导入/运行/存储验证，必要时真机和发布权限；Node fake-wx 不替代。 |
| 生产/用户流写入性能、跨浏览器/跨 OS、完整安全矩阵 | `NOT_EXECUTED` | 各自的受控环境、负载/时长/指标、原始输出和独立复核；不可用 synthetic SQLite 读取 benchmark 外推。 |
| Linux MCP 一键安装 | 未交付 | 跨平台 launcher、配置生成和 Linux health 证据。 |

不要将 loopback 看板暴露到网络。Harness 有路径/argv 约束但不是恶意代码沙箱；不可信代码应在独立受控环境运行。命令、日志和证据均不得打印秘密。

## 延伸阅读

- [V3 本地运行、操作与恢复](docs/platform-v3/README.md)
- [能力矩阵与已知边界](docs/platform-v3/capability-status.md)
- [发布就绪性](docs/platform-v3/release-readiness.md)
- [独立平台测试](docs/platform-v3/independent-platform-tests.md) 与 [Runtime 审查](docs/platform-v3/runtime-review.md)
- [五栈样例经验](docs/platform-v3/lessons-learned.md)
- [V2 Runtime 使用说明](docs/platform-v2/README.md)
