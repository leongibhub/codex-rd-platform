# V3 能力状态矩阵

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

跨文档可追溯主链为：`CR-V3-001` → `DES-V3-001` → `REQ-V3-001..010/REQ-MATRIX-*` → `TASK-V3-001..004` → 当前工作区变更与 Runtime Run → 应用测试/审查报告 → 未来 `REL-*`。平台 lifecycle/harness/adapter 的独立验证与复审已经取得证据；链路仍为 `PARTIAL`，因为五个真实项目目前只登记聚合 Case v2，尚未覆盖完整项目设计/任务/所有需求与 NFR，且 G9/G10、真实部署、人工验收、微信原生与容量基准均无相应证据。
