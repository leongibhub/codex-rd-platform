# V3 能力状态矩阵

此表保留上轮观察快照；下方“CR-V3-002 当前事实优先级”覆盖与旧快照冲突的状态。完整报告/导出、证据新鲜度、Case runner、容量、长稳、Python 需求级流程和 CI 的后续事实见 [后续交付记录](completion-delivery.md)。

- 文档状态：`DRAFT`；观察快照：`2026-09-06T17:46:40+08:00`
- 事实输入：当前未提交 V3 源码、Runtime `snapshot`/`stack-probe`、五个 manifest、应用记录及独立报告。
- 口径：**源代码**是当前工作区观察（`OBSERVED`）；**实际执行**只列有命令/Runtime 运行记录的结果。`NOT_EXECUTED`、`NOT_AVAILABLE` 不等于失败，更不等于通过。此页不是 RTM，不改由主协调者维护的中央 RTM。

为避免把一个用户目标拆成实现细节，下表把 10 个平台目标和 13 个应用用户目标聚合为 **23 项**。`实现` 仅说明当前源码/受控文档是否观察到能力；`真实执行` 不把开发者自测、独立测试、review、原生工具或人工验收混为一类。

| # | 用户目标（聚合需求） | 实现状态 | 真实执行状态 | 当前限制 / 待验收 |
| --- | --- | --- | --- | --- |
| 01 | 独立 V3 生命周期实例（REQ-V3-001） | OBSERVED：`lifecycle.py`、CLI `lifecycle` 和看板读取入口存在 | OBSERVED：独立 core 8 项 PASS、final runtime 回归 128 PASS | 当前 Runtime 活动记录不是模板项目 Gate 决定 |
| 02 | 版本化工件与证据（REQ-V3-002） | OBSERVED：`lc_` 生命周期域及工件/证据命令已在当前源码出现 | OBSERVED：model source/adoption/version 独立 3 项 PASS；五应用 legacy model adopt 至 v2 并保留 v1 `NOT_AVAILABLE` 来源 | Markdown 不能代替结构化工件登记 |
| 03 | 可计算的端到端追踪（REQ-V3-003） | OBSERVED：trace 关系、失效及快照投影代码存在 | OBSERVED：collection query 独立 3 项 PASS；正式报告区分当前版本与历史 FAIL | 中央 RTM 仍由主协调者维护 |
| 04 | 证据驱动 Gate 评估与人工决策分离（REQ-V3-004） | OBSERVED：设计/源码区分 `assess` 与 `decide` | OBSERVED：approval P1 修复并复审；五应用仍仅 G0 `IN_REVIEW`/candidate `BLOCKED`、无决定 | 默认 authenticated approval provider 为 NOT_AVAILABLE |
| 05 | 先测试模型、后结构化用例（REQ-V3-005） | OBSERVED：测试模型/用例域和五样例风险模型存在 | OBSERVED：source-bound model/version 独立 3 项 PASS；五应用 Case v2 均以新执行重测 PASS | 开发者测试模型不是执行结果 |
| 06 | 用例执行、失败缺陷与影响回归（REQ-V3-006） | OBSERVED：测试执行/缺陷域存在 | OBSERVED：critical closure P1 修复后独立 core 验证 PASS | V2 quality Run 不能冒充 Test Case Execution |
| 07 | 受策略约束的发布与真实部署记录（REQ-V3-007） | OBSERVED：release/create/ready/deployment 设计与当前源码接口 | OBSERVED：report adverse-release P2 修复并通过适配器独立测试；无真实 G10、部署、回滚或验收 | 见[发布就绪性](release-readiness.md) |
| 08 | 可解释的生命周期看板（REQ-V3-008） | OBSERVED：页面有生命周期摘要、Gate、trace、测试、缺陷、发布区 | OBSERVED：adapter 独立 4 项、集合分页 3 项及浏览器阅读 RED/GREEN | 看板不会派发 Agent 或执行任意命令 |
| 09 | 暂停、恢复、重试、变更、回滚可审计（REQ-V3-009） | OBSERVED：V2 控制和 V3 lifecycle control 源码存在 | OBSERVED：rollback/invalidation P2 修复并经 runtime review 验证 | pause 不终止外部宿主进程 |
| 10 | 同一 Skill 覆盖五个技术栈（REQ-V3-010） | OBSERVED：五个 manifest、源码、应用文档与 Harness 存在 | OBSERVED：五应用 DONE；Harness 独立 11 PASS、1 NOT_EXECUTED；Skill-forward 9 current PASS + GREEN | 不是五个“全生产自治”应用 |
| 11 | C++ 库存增减且拒绝负库存 | OBSERVED：C++17 CLI 与持久化代码存在 | OBSERVED：开发者 5 项、独立黑盒 2 项及 Runtime review PASS（attempt 2） | 仅 WSL g++ 11.4；非并发单写者 |
| 12 | C++ SKU 查询与稳定列表 | OBSERVED：`get/list` 代码与 manifest 存在 | OBSERVED：独立黑盒覆盖跨进程、排序和缺失 SKU | Windows 原生编译器为 NOT_AVAILABLE |
| 13 | C++ 重启恢复及坏输入不写 | OBSERVED：全量加载验证、临时替换实现被审查记录引用 | OBSERVED：独立黑盒包含坏数据/过量扣减字节保持；Runtime task `DONE` | 这不建立任何生产 durability 结论 |
| 14 | Python 读取 UTF-8 CSV（含 BOM/列重排） | OBSERVED：标准库 CLI、严格 CSV/日期校验存在 | OBSERVED：独立黑盒 attempt 2 PASS；首次 QA fixture FAIL 保留 | 无发布、部署或人工验收 |
| 15 | Python Decimal 分类与总额精确输出 | OBSERVED：输入位数/指数/行数边界和受控上下文实现存在 | OBSERVED：开发者修复后 14 项、独立 attempt 2 回归 PASS | 不接受超出已写边界的金额/指数 |
| 16 | Python 无效输入明确非零、无成功 JSON | OBSERVED：CLI 错误路径与测试模型存在 | OBSERVED：独立 attempt 2 负向/资源回归 PASS；首次 FAIL 仍保留 | 无 release、部署或人工验收 |
| 17 | Web 离线便签新增/编辑/删除与恢复 | OBSERVED：原生 ESM、localStorage 安全适配器和 UI 存在 | OBSERVED：Node/独立业务模块 PASS；内置浏览器实际 create/reload/edit/delete PASS | 存储拒绝故障注入未在浏览器执行 |
| 18 | Web 搜索、长度校验与文本安全渲染 | OBSERVED：搜索/校验和 `textContent` 渲染路径存在 | OBSERVED：Node 验证；内置浏览器 XSS 文本渲染、搜索 PASS | 单浏览器观察不等于跨浏览器覆盖 |
| 19 | Web 存储不可用时可降级 | OBSERVED：修复后 guarded storage adapter 存在 | OBSERVED：独立 Node 回归 PASS；独立浏览器复测 NOT_EXECUTED | 当前源码复审已通过；浏览器证据仍缺失 |
| 20 | Java 预约、重叠拒绝与相邻允许 | OBSERVED：Java 8 CLI/store 和 manifest 存在 | OBSERVED：JDK 8 开发者及独立黑盒均有 PASS 记录 | 单写者、无时区/并发/外部服务 |
| 21 | Java 取消/列表/跨进程文件恢复 | OBSERVED：命令与持久化实现存在 | OBSERVED：独立黑盒 2 项 PASS；当前源码复审确认可执行名修复 | 非 Windows 主机未真实运行 |
| 22 | 微信原生工程结构 | OBSERVED：`app.json`、Page、WXML/WXSS、无伪造 AppID | NOT_AVAILABLE：微信开发者工具/真机缺失 | 不宣称导入、原生 `wx`、真机或发布成功 |
| 23 | 微信记账、精确合计、删除与本地恢复 | OBSERVED：整数分领域、页面 adapter、fake `wx` 测试存在 | OBSERVED：Node 开发者 8 项、独立 fake-`wx` attempt 2 3 项 PASS | fake `wx` 不是原生验证；当前源码复审不替代原生测试 |

## 当前运行事实的差异与处理

最终快照显示 Harness、lifecycle core、CLI/board adapter、collection query、test-model versioning 及五应用任务均 `DONE`（各 4/4 quality checks）；历史 FAIL 和 defect 记录保留。五个真实 lifecycle 项目已从 REQ/CODE_CHANGE 延伸至当前 Test Model v2、Case v2、Environment Evidence、独立 PASS Execution 与 `lifecycle-report`；其 legacy v1 来源保持 `NOT_AVAILABLE`。每个仍为 `G0 / IN_REVIEW`，G7 assessment candidate `BLOCKED`，且**没有** Gate Status/decision。聚合 v2 Case 的 report `PASS/complete_snapshot=true/recommend_release=false` 仅表示其声明范围内当前版本执行完整，不能汇总为完整需求/NFR、G7、正式关闭或发布。详见[五应用真实生命周期追踪验证](live-lifecycle-validation.md)。

跨文档可追溯主链为：`CR-V3-001` → `DES-V3-001` → `REQ-V3-001..010/REQ-MATRIX-*` → `TASK-V3-001..004` → 当前工作区变更与 Runtime Run → 应用测试/审查报告 → 未来 `REL-*`。平台 lifecycle/harness/adapter 的独立验证与复审已经取得证据；链路仍为 `PARTIAL`，因为五个真实项目目前只登记聚合 Case v2，尚未覆盖完整项目设计/任务/所有需求与 NFR，且 G9/G10、真实部署、人工验收、微信原生等仍无相应证据。容量基准不再属于“无证据”项，其范围化实测在下节说明。

## CR-V3-002 当前事实优先级

下列事实以已推送 `62c153e`、`c3eb271`、`527dae1` 的记录、本机 Runtime/独立记录和[后续交付记录](completion-delivery.md)为准；它们不改变顶层模板 Gate，也不将模块质量状态扩大为通用产品验收。

| 范围 | 当前事实 | 仍不能推导的结论 |
| --- | --- | --- |
| 全量生命周期报告、项目导出、Case runner | `lifecycle-report` 已从一致分页读取生成全量当前 Case 报告；`project-export` 是拒绝覆盖的只读文档索引；`test-run` 只执行已基线 Case 的版本绑定 argv，并以 path/SHA-256 锁定 `CODE_CHANGE`。实现及本机独立验证已完成。 | 导出不是源码备份、Git archive、Gate 决定或批准包；通用 argv runner 不生成性能/压力/长稳指标。 |
| SQLite 公开读容量 | `capacity --profile full` 的实际终态为 100 项目、100,000 工件版本、1,000,000 事件，129.7199 秒、294,764,544 bytes、读取错误 0；它是合成批量 SQL 数据上的 `Runtime.lifecycle_collection` / `Runtime.lifecycle_snapshot` 读路径观察。 | 不是 Runtime 写入性能、生产负载、SLO、Gate、发布或客户验收。 |
| 8 小时 soak | `.rd-platform/benchmark-soak-8h-20260906-1` 当前为 `RUNNING`；同 run checkpoint 可供读取，但尚无 terminal JSON。 | 没有 terminal 结果时，不得声称 8 小时完成或 PASS；即使终态产生，也只覆盖公开读路径。 |
| Python 逐需求生命周期项目 | 有界的既有 Python 费用 CLI：37/37 CURRENT Case `PASS`、7/7 RTM `COMPLETE`，独立 Reviewer 已登记 G0–G8 `DECIDED/PASS/CURRENT`，finalization 为 `G0_G8_COMPLETE_G9_PENDING`。见 [Python 独立评审](python-lifecycle/independent-review.md)。 | G9–G11 仍 `NOT_EVALUATED`；没有 human acceptance、生产部署或发布建议。 |
| C++、Web、Java、微信四个样例 | 四个样例保留各自实现、独立测试/审查和历史生命周期事实；它们没有像 Python 项目一样完成逐需求 G0–G8 生命周期收口。微信仍只有 Node/fake-`wx`，无 IDE/真机证据。 | 不得将 Python 的 scoped Gate 决定复制为其他四个样例的 Gate PASS、生产自治或原生微信验证。 |
| 固定提交高级安装交付 | 根 `install-to-D.ps1` revision 3 固定捕获源 `HEAD^{commit}`、fresh Git init、depth-1 fetch、detached checkout 且无 remote；拒绝 `-Force`、非空/非目录 target、源或其子目录和 reparse point。仅允许精确公开占位 `knowledge/local/README.md` 与指定 blob，其他本地数据不递归复制。独立 evidence 为 unit 12/12、integration 10/10、reviewer 22/22 PASS；提交 `527dae1b7f75d6b526682d1c5a6407c1b3fc6a53` 的真实隔离安装实际完成 setup、依赖、MCP，得到 `PASS (TEMPLATE MODE)` / Gates NONE。见[独立安装交付审查](install-transfer-review.md)与[真实隔离安装验证](install-real-validation.md)。 | 首选仍是 Git clone + target 本仓 `git config --local` + setup。高级 helper 不转移源 `.git/config`，setup 必须由 target 可见的经批准 Git identity 支持；失败不会覆盖/自动清理 target，新建 target 仅留 `.install-failed` 供诊断。它不是备份、离线发布结论、生产部署、人工验收或 Gate 决定；历史 `c3eb271` 真实失败保留为 BUG-INSTALL-002。 |
| GitHub Actions | `527dae1b7f75d6b526682d1c5a6407c1b3fc6a53` 的真实 [run 34032990521](https://github.com/leongibhub/codex-rd-platform/actions/runs/34032990521) 于 `2026-09-06T12:32:02Z` 完成 SUCCESS，4/4 jobs SUCCESS；Windows runtime job `101485885964` 于 `12:32:01Z` 完成。`62c153e`、`c3eb271` 的既有成功、第一/二轮失败和修复历史保留在 [CI 执行记录](ci-execution.md)。 | 该证据仅覆盖 `527dae1` 源码 workflow，不包括后续仅文档改动；workflow 成功不覆盖 `c3eb271` 随后保留的真实安装失败，也不是 G10、生产部署或人工验收。Node/fake-`wx` 不等于微信 IDE、真机或发布。 |
| 宿主、审批和发布 | 当前仍由 Codex 宿主实际派发 Agent；没有无人值守 cloud daemon。认证 approval provider、生产部署/回滚和真实人工验收尚无相应事实。 | 不得用本机任务 `DONE`、模板 validator、CI 或测试报告代替认证审批、部署成功或客户验收。 |

## CR-V3-003 当前事实优先级（追加，不改写历史）

本节覆盖本页早先将执行端表述为“未实现/未交付/默认无 provider”的源码状态，但不覆盖历史执行、Gate 或 release 事实。观察对象是当前未提交工作区；Evidence Status 仍严格使用受控词汇。

| 范围 | 实现 / 文档事实 | 执行与结论边界 |
| --- | --- | --- |
| `REQ-V3-016` / worker service | `OBSERVED`：`worker_service.py`、`worker_backends.py`、CLI `worker-service` 和受控配置契约已在当前源码；支持 lease、heartbeat、bounded trusted argv、`--once`、常驻循环和 no-tools Responses proposal transport。 | `OBSERVED`：独立安全 probe 证实 Codex auto-review 可读写 workspace 外无害 sentinel；production Codex backend 已 fail-closed 禁用，DB 路径分离不是隔离。`NOT_EXECUTED`：当前无可发布的常驻 worker 成功、live Responses 或 Responses 安全路径执行证据；宿主无 `OPENAI_API_KEY`。旧 Codex 测试不得外推为新路径 PASS。 |
| `REQ-V3-017` / authenticated approval | `OBSERVED`：SSH Ed25519 provider、canonical challenge、外部签名验证与 `approval-challenge`/`approval-register` 已在当前源码。 | `NOT_AVAILABLE`：没有本项目受权 operator、真实外部签名、human approval 或 Gate decision。fixture keys/signatures 不是人类审批事实。 |
| `REQ-V3-018` / deployment executor | `OBSERVED`：显式 argv、source SHA-256、health、rollback/rollback-health、append-only receipt 和 trial/formal 分域已在当前源码。 | `NOT_EXECUTED`：没有授权目标的真实 production deploy/rollback、G10 或 release acceptance。trial receipt 也不是 release 事实。 |
| `REQ-V3-019` / Linux setup | `OBSERVED`：`scripts/setup.sh`、本仓 venv `--copies`、配置生成和 validator 调用已在当前源码。 | `OBSERVED`：GitHub Actions [Ubuntu job 101496781967](https://github.com/leongibhub/codex-rd-platform/actions/runs/34036999184/job/101496781967) 的实际 native setup 与 repeat-install 步骤均 SUCCESS；其 `setup.sh` blob 与当前文件一致。该证据只覆盖该 Ubuntu job/脚本版本，不推出全局 release、生产部署、人工验收或最终 CR PASS。 |
| `REQ-V3-020` / integration and delivery | `OBSERVED`：新 CLI 已出现在 `--help`，根 README 已给出中英文受控配置与恢复用法。 | `OBSERVED`：r3 首个独立 review 因 TC912 的五栈覆盖/记录矛盾而失败；同冻结快照 attempt 2 已补齐独立 tester 五栈命令级记录，并通过 review `run-192ea18554814c1a8155e6a206da993a`，Runtime 为 `DONE` 4/4。此模块级结论不能给 CR、Gate 或 release 统一 PASS。此前 217 runtime、1 skip 是中途快照，不是本轮 final verdict。 |

追踪状态为 `PARTIAL`：`CR-V3-003 → DES-V3-003 → REQ-V3-016..020 → TASK-V3-016..020 → 当前工作区变更/测试 → 待完成独立 review → 未来 release`。本仓仍为 template lifecycle mode；本节不是中央 Gate Register，绝不产生 G0–G11 决定。

## 2026-09-07 当前事实优先级（追加，不改写历史）

本节覆盖本页较早的 `RUNNING` soak、旧 CI 及“待最终 review”快照；它保留原条目作为当时事实，不将当前工作区或本机 QA 外推成批准、发布或验收。

| 范围 | 当前可核对事实 | 证据边界 / 未完成项 |
| --- | --- | --- |
| 8 小时公开读路径 soak | `OBSERVED`：同一 run `soak-9241634446774e1291126d1cc1c2a53b` terminal 为 `PASS`/exit 0，elapsed `28800.74027900002` seconds；4,952 样本，最大相邻 gap `8.19159369985573` seconds，`reads.errors=[]`；terminal SHA-256 `00BE7586AD05A8CDD03CFC510C7C730021920BEDB8EFDC1225E4A24765A398CD`。 | 仅绑定旧源码 `E482F1E2DD6A5A7AB42736AE227DB56B8B5D12F2D6C1D5FA1F3293F78BEDBC9A` 的合成 SQLite 公共读路径；不是写入、全系统/安全、生产、Gate、release 或验收结论。 |
| `026263f` hosted CI 与后续本机 QA | `OBSERVED`：[GitHub Actions run 34038680898](https://github.com/leongibhub/codex-rd-platform/actions/runs/34038680898) 为 3/4 jobs SUCCESS：Windows Runtime 273 PASS/1 skip，Windows platform 133 PASS/3 skips；独立 job 实际为 98 tests/1 error，不能虚增为 98 PASS 再加 1 FAIL。WSL readiness 修复后，本机端点 suite 30 PASS/24.700 s，root full suite 99 PASS/1 skip/114.547 s。 | 独立 job 的失败是 `wsl.exe` 存在但没有可启动 Linux distro；不能改写为成功。上述本机 QA 不替代 hosted CI；新 CI 为 `PENDING`。任一 CI/本机测试都不是 Gate、部署或验收。 |
| P1 复审与收口策略 | `OBSERVED`：历史 P1（worker fast pause→resume 重复执行、未受 host 严格条件约束的 stage claim）已由 TASK-V3-016 r9、TASK-V3-020 r3 attempt 2 和 TASK-V3-021 r7 独立复测/review；当前 module review scope P0=0、P1=0。 | 这是当前源码/隔离 fixture 的模块级结论；hosted CI、真实 API/批准/部署/验收仍各自未完成。 |

因此，`CR-V3-003/004` 的实现、范围化测试与当前模块 review 证据保持 `OBSERVED`，但 fresh CI、真实 API、人工批准、真实部署/回滚、G10 及验收仍分别保持其既有 `PENDING`、`NOT_AVAILABLE` 或 `NOT_EXECUTED` 边界。本页不产生全局 PASS。

## 2026-09-07 冻结前任务与回归事实（追加，不替换历史）

以下是对当前 Runtime 任务快照与工作区回归记录的受限观察。它覆盖
[`CR-V3-005`](CR-V3-005-host-stage-policy.md) 的新增策略任务，但不改变 template
lifecycle mode，也不产生 Gate decision。

| 范围 | 当前事实 | 结论边界 |
| --- | --- | --- |
| `TASK-V3-016` / `REQ-V3-016` | `OBSERVED`：Runtime 为 revision 9、`DONE`、4/4 checks；r8 已被 r9 取代。canonical fence 覆盖 unknown external-outcome invalidation/control 与 rollback，并将 adopted dependency resolution 延后到 atomic claim；post-claim context 使用持久 adopted refs 的有界脱敏生命周期记录。developer 64 tests PASS；独立 unit `run-901b8eb923704979bb35775a5fe7cd9c` 为 64/64 PASS/26.886856 s，独立 integration `run-a918a474aa18436887ac526af9a180ff` 为 22/22 PASS/19.173931 s（TC939）；review `run-95e3f86d8cdd4bbc9758b395059355ff` 已登记。 | `DONE` 仅为当前源码/隔离 fixture 的模块质量链；新 CI 仍 `PENDING`，不是端点总体、项目 Gate、外部执行或验收结论。 |
| `TASK-V3-018` / `REQ-V3-018` | `OBSERVED`：Runtime 为 revision 4、`DONE`、4/4 checks，限于受控本机/fixture 的正式登记原子性质量链。 | `NOT_EXECUTED`：真实部署、rollback、G10、release acceptance。 |
| `TASK-V3-020` / `REQ-V3-020` | `OBSERVED`：r3 首个 review `run-3dffaf1ab6c2462dbda92e7b08cf33b2` 为 `FAIL`，原因是 TC912 把未执行的五栈回归写为 PASS、又与 `NOT_EXECUTED` 记录冲突；未观察到产品源码回归。attempt 2 unit `run-7ecc1fb37c4a415aabcd37872ceb305b` 33/33 PASS/15.482481 s；integration `run-2f1239aa6e794fe5ae01e6539c89fb7c` 15 条实际命令 PASS/31.697916 s（非 15 个测试用例），覆盖 C++ WSL build/unit/integration、Python build/unit、Web unit、Java 8 build/unit/integration、微信 unit/integration；独立五栈 13/13、Web Node 3/3、微信 fake-`wx` Node 3/3、CLI/fixture 4/4；TC912 已更正。attempt 2 review `run-192ea18554814c1a8155e6a206da993a` 为 PASS，Runtime `DONE` 4/4。 | 这是本机/fixture/adapter 的模块质量链。微信 fake-`wx` 不构成原生微信；`Ran 0` 与 fixture RED→GREEN 不计产品 Gate。hosted CI、live Responses、真实人批、生产部署/回滚、客户验收与顶层 Gate 仍未由此产生 PASS。 |
| [`CR-V3-005`](CR-V3-005-host-stage-policy.md) / `TASK-V3-021` / `REQ-V3-021` | `OBSERVED`：Runtime 为 revision 7、`DONE`、4/4 checks；r4–r6 已被 r7 取代。r7 修复 TC semantic adoption、repair exact refs、内置 Gate FAIL/rollback recovery dependency binding；QA unit 7/7、integration 18/18、reviewer 17/17，review `run-3e3576b548ca4dea91dbbc52e813c693`。 | 当前 policy scope P0=0/P1=0；模块级证据仅限源码/隔离 fixture，不构成真实 Gate、批准或生产执行。 |
| `TASK-V3-022` / `REQ-V3-008,021` | `OBSERVED`：Runtime 为 revision 1、`DONE`、4/4 checks；[只读状态面](orchestration-status.md)解释前提但不授权执行。 | `NOT_APPLICABLE`：该只读状态任务不推进 Gate，也不代替 TASK-021 QA 或人工验收。 |
| 冻结前回归记录 | `OBSERVED`：platform 133 PASS/217.852 s；早期 full runtime 288 PASS/177.502 s/2 skips（freeze 前）；后续 full runtime 294 tests/1 FAIL（QA fixture teardown Windows `WinError 32`）；full independent 实际 109 tests/1 error/1 skip（成功 107；TC304 旧 non-safe-retry fixture）。TC304 已改为明确 negative 与显式临时 `safe_to_retry` 允许场景。本轮五应用独立 Python 13/13 PASS/12.839 s、显式 Node 两文件 6/6 PASS/141.7366 ms、`python -X utf8` Skill `quick_validate.py` PASS，JS syntax/diff check 成功。 | 修复不回写旧 FAIL；不带 UTF-8 的 GBK 工具错误保留历史。该历史记录产生时 final-freeze 回归与 hosted CI 尚 `PENDING`；后续当前冻结回归列于本节末，新 hosted CI 仍 `PENDING`。不得挑选旧绿或局部五应用结果为最终版本 PASS。 |

当前跨任务追踪为 `PARTIAL`：`CR-V3-005 → REQ-V3-021 → TASK-V3-021 r7 → policy/status
source and tests → module review`；`TASK-V3-022` 的已完成只读投影不缩短外部事实链。历史
full platform 133 tests/2 errors/210.172 s（fixture copytree race）和 contextmanager wrapper
（被装饰函数 `__wrapped__` 的 globals）错误保留为工具/fixture历史，不归因产品；TC304/deployment cleanup 后 deployment split
19 PASS、1 host-permission skip，未再现 `WinError 32`。当前冻结回归为 Runtime 307 tests/
236.304 s/OK/2 skips、platform QA 134 tests/179.961 s/OK（先前已修 fixture run 为 178.309 s）、independent full 113 tests/135.173 s/OK/1
skip（包含 TC940）。112 tests/148.845 s/OK/1 skip 是 TC940 新增前的历史冻结后快照，不能借为当前结果。这些 `OBSERVED` 结果仍不能替代
新 hosted CI、live Responses、真实人类批准、生产部署/回滚、客户验收或顶层 Gate PASS。

当前冻结源码 checkpoint 为提交 `fbd9b36d5ad429bd3528328c1ec6a06b49cc990b`（45 个变更文件）。`OBSERVED` 的提交存在只固化本页所列待验收状态；它不是全量完成、Gate、发布或外部事实。

## 最终 CI 补录：覆盖上文的新 CI 待执行快照

上述源码 `fbd9b36` 的 [run 34095997725](https://github.com/leongibhub/codex-rd-platform/actions/runs/34095997725) 于 `2026-09-07T07:48:30Z` 完成 `SUCCESS`，Windows/Ubuntu Runtime-platform 与 multistack 共 4/4 jobs 成功。此实际结果覆盖上文新 hosted CI 的 `PENDING` 描述；此前失败、当时待执行状态及其作用范围仍作为历史保留。准确 job ID、时间及计数证据边界见 [CI 执行记录](ci-execution.md)。它不改变真实 API、人工批准、微信原生、生产部署及验收仍缺少实际执行事实的状态，也不创建顶层 Gate PASS。
