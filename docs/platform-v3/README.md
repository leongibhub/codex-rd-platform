# 平台 V3：本地运行、操作与恢复说明

最终源码提交、远端核验、实测结果和使用入口见[交付记录](delivery-record.md)，逐项实现追踪见[追踪索引](traceability.md)。下文的观察时间保留原始检查口径。

- 文档状态：`DRAFT`
- 变更：`CR-V3-001`；设计基线：[V3 设计](../superpowers/specs/2026-09-06-platform-v3-design.md)
- 本页不作 Gate、发布、生产部署或人工验收决定。顶层 `platform-manifest.json` 当前仍为 `lifecycle_mode: template`；V3 Runtime 中的活动记录不把模板项目的任何 G0–G11 变为 `PASS`。
- 本说明基于本轮尚未标记发布版本的工作区快照；交付正在准备受控 Git 提交与交付记录，本文不虚构 commit SHA、版本标签或已完成发布。

## 这是什么，不是什么

V3 是运行在本机、以 SQLite 和 Git 工作区保存事实的研发控制面。它在 V2 的任务质量 Run 之外增加版本化生命周期、工件、追踪、测试执行、缺陷、Gate 候选评估、发布记录和多技术栈 Harness。其模型/Agent 是外部宿主（例如 Codex）显式派发的：宿主读取 Skill、创建或领取工作、执行命令并登记结果；Runtime 负责持久化、校验和展示，**不会**自行启动模型，也不是无人值守后台 daemon。

因此，浏览器看板的刷新或 `READY/ACTIVE` 任务状态不代表后台 Agent 正在运行；`pause` 也不会杀掉宿主已启动的外部进程。需要取消实际进程时，操作员必须通过宿主/终端取消，并将真实结果记录为证据。

当前工作边界、证据和待验收项见：[能力状态矩阵](capability-status.md)、[发布就绪性](release-readiness.md)、[五样例经验](lessons-learned.md)。应用的独立测试和审查原始记录分别是 [独立应用测试](independent-app-tests.md)、[独立应用审查](app-review.md)、[独立平台测试](independent-platform-tests.md)。

## 前置条件与可观察工具状态

在 `2026-09-06T17:19:02+08:00` 执行 `rd_platform stack-probe` 的结果是：仓库 `.venv` Python、Node、Java/JDK 8 为 `AVAILABLE`；Windows 原生 `cxx` 为 `NOT_AVAILABLE`。C++ 样例的已记录路径是 WSL Ubuntu 22.04 `g++ 11.4`，不是 Windows C++ 工具链。微信开发者工具/真机当前为 `NOT_AVAILABLE`，不能以 Node fake `wx` 取代。Web 样例在 Codex 内置浏览器已有一次实际创建、XSS 文本渲染、刷新、编辑、搜索、删除观察；存储拒绝故障注入仍只有 Node 范围证据，详见 [browser-validation](browser-validation.md)。

建议从仓库根目录使用受控 Python：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-probe
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform snapshot
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle --project-id PROJECT_ID --limit 200
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle-collection --project-id PROJECT_ID artifacts --limit 200
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform lifecycle-report --project-id PROJECT_ID
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform serve
```

看板仅监听 `127.0.0.1:8020`；打开 `http://127.0.0.1:8020/`。它读取已持久化的本地事实，浏览器不提供任意命令执行、人工批准、测试结果或发布操作入口。

若要隔离一次演练或测试，不要复用默认库：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db .rd-platform\v3-trial.db snapshot
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db .rd-platform\v3-trial.db serve --port 8021
```

## 典型操作

1. 宿主先读 `platform-orchestration` Skill、当前 Git 状态和 Runtime 快照，确认真实责任角色；Skill 是工作方法约束，不是服务启动器。
2. 可信宿主用 `command` 调用 `lifecycle.initialize`、`artifact.create`、`trace.link`、`test_model.create` 等已实现的受控命令，并把正文保留在 Git 工作区。写入前须有实际项目 ID、工作区根目录和版本来源；不要把 Markdown 文字当作数据库已登记事实。
3. `lifecycle --project-id ... --after-sequence N --limit 200` 分页读取事件和摘要；用 `lifecycle-collection --project-id ... <collection> --after-cursor ... --limit 200` 读取工件、case、execution 等一个集合的后续页。cursor 与项目/集合绑定且不可自行构造。`lifecycle-report` 是当前版本已声明 Case 的正式汇总，和 V2 `report` 的 MODULE_QUALITY 分母不同；前者 `PASS` 或 `complete_snapshot=true` 都不等于 Gate 或 release 建议。

五个真实样例已完成 legacy Test Model 的显式 adopt、Test Case v2 修订与新的独立实际重测；v1 的原始来源仍记录为 `NOT_AVAILABLE`，不会被后来的维护者覆盖。完整执行链及其 `recommend_release=false`、G0/G7 无决定边界见 [五应用真实生命周期追踪验证](live-lifecycle-validation.md)。
4. 真正执行的模块质量命令只能经可信 CLI 的 `run` 记录；argv 用 `--` 分隔，执行器不使用 shell。例如：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform run --task-id TASK_ID --agent-id TESTER_ID --phase unit --cwd . --timeout 60 -- .\.venv\Scripts\python.exe -m unittest tests.runtime.test_stack_harness -v
```

`run` 的实现、unit、integration、review 是 V2 任务质量阶段；它们不是 V3 单个 Test Case Execution，也不自动构成产品 Gate 或验收。

## 五类应用的可重放命令

Harness 只接受仓库受控 `manifest.json` 的 argv 数组，构建产物在 `.rd-platform/build/<id>`。它是可信本地执行边界，**不是**执行未知代码的安全沙箱。

```powershell
# C++：Windows 通过 Python 驱动 WSL g++；若 WSL/g++ 不可用，结果应记录为不可用或失败。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\cpp_inventory\manifest.json --phase build --phase unit --phase integration

# Python：仅 manifest 已声明的 build/unit；没有 integration 命令即 NOT_EXECUTED。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\python_expenses\manifest.json

# Web：Node 仅验证业务模块；实际浏览器流程需另行独立执行。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\web_notes\manifest.json --phase unit
Push-Location examples\multistack\web_notes; python -m http.server 8080 --bind 127.0.0.1; Pop-Location

# Java：使用探测到的 JDK 8 javac/java。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\java_booking\manifest.json --phase build --phase unit --phase integration

# 微信：Node 领域/页面替身；这不做原生导入或发布。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-run examples\multistack\wechat_expenses\manifest.json --phase unit --phase integration

# 生成本地交付归档与摘要；生成不等于发布。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\python_expenses\manifest.json
```

`stack-run` 对工具缺失输出 `NOT_AVAILABLE`，未声明命令输出 `NOT_EXECUTED`，两者都不是 `PASS`。Web 已有一次内置浏览器 XSS/持久化用户流证据，但其他浏览器和浏览器级存储拒绝仍须分别取得执行证据；微信 IDE 导入/真机/发布，以及 Java 在非 Windows 主机的真实执行也仍待取得。

## 备份、恢复与回滚

1. 停止看板、可信 CLI 和其他 SQLite 写入者；保留当前 `.rd-platform/state.db` 的可恢复副本，再复制数据库。不要把本机状态库、运行输出、凭据或生成交付物提交到 Git。
2. 同时记录代码提交 SHA、工件文件 SHA-256 和外部证据 locator。恢复后用 `snapshot`、`lifecycle` 以及适用的工件摘要核验；恢复不能把未执行测试或人工批准补成事实。
3. 代码回退使用经过审查的 Git revert/已知版本部署。V3 迁移只增表；回退到 V2 代码不会删除 `lc_` 表。数据库内容回退只能从备份恢复，禁止用自动脚本 DROP 表。
4. 对已经记录的发布，使用 `release.rollback` 记录实际操作、操作者、原因和证据。命令退出码为 0 不可自动推导生产回滚、部署成功或客户验收；截至本页快照，尚无此类真实证据。

## 操作安全边界

- HTTP 是 loopback 控制面，V3 写入限定可信 CLI/宿主；不要将其暴露到网络。
- `repository_root`、content path 与 manifest 工作区路径必须在项目根内；Harness 拒绝 shell 文本、未知占位符和可见路径逃逸，但不替代恶意代码 VM/容器隔离。
- 证据和命令输出不得含 token、cookie、password、authorization 或私钥；仅保存脱敏文本、摘要或外部 secret reference。
- Gate 先 `gate.assess` 后由有权人 `gate.decide`。需要人工批准的 Gate 只能引用真实 `human_approval` 证据；模型、Agent 或文档作者不能代签。
- 当前默认没有已认证 approval provider，人工批准登记为 `NOT_AVAILABLE`；不能用本机任意 Python 调用、测试 fixture 或普通 host 字符串生成 `VERIFIED` approval。
