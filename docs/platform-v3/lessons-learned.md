# V3 五技术栈 Skill 实测经验与待验收边界

> 下方五栈首轮记录保留为历史。后续已实际完成 Windows/Linux 原生 CI、容量基准和 Python 逐需求 G0–G8；当前状态以 [后续交付记录](completion-delivery.md)、[CI 闭环](ci-execution.md) 和 [真实安装验证](install-real-validation.md) 为准，不把历史 NOT_EXECUTED 当作当前总状态。

## 后续工程验证新增经验

- **安装测试必须覆盖真实仓库结构。** 原安装器的隔离小夹具通过后，实际仓库中的公开 `knowledge/local/README.md` 仍触发拒绝。安全负向用例之外，必须对固定的真实提交执行正常安装，不能仅凭 marker-only setup 判断可安装。
- **白名单同时约束路径和内容。** 已审过的公共说明可以有精确例外，但同名私有内容、目录中的其他文件及大小写变体不能继承例外。PowerShell 的默认 `-eq` 不区分大小写，精确路径契约需要显式大小写敏感比较和真实负向用例。
- **文档命令必须在真实起始状态执行。** single-branch clone 的 fetch 配置不同于开发者工作区；仅取得对象和远端引用不保证能建立跟踪分支。README 必须实测首次克隆、仅 main 克隆、已有本地分支且远端已前进的三种路径。
- **干净 CI 会揭示缓存掩盖的问题。** 本机 Java 8 已存在的 classes 目录、Windows PATH 中的 GNU DLL、原机器绝对 MCP 路径，以及 Python 编码器深度差异都不能靠静态 workflow 检查证明兼容性。实际矩阵失败应产生修复和新执行，而不是降级运行时或跳过断言。
- **不同层级的通过不能互相代替。** 本轮已观察到“fixture PASS、完整安装 FAIL”和“本机 PASS、hosted CI FAIL”；这些不是矛盾，而是测试范围不同。报告必须说明源提交、执行环境和未覆盖条件。

- 文档状态：`DRAFT`
- 记录时间：`2026-09-06T17:46:40+08:00`
- 范围：`platform-orchestration` 在 C++、Python、Web、Java、微信五个合成小样例上的已观察过程；不把它扩展为生产 Agent 自治结论。
- 本轮材料正准备受控 Git 提交；在提交 SHA/交付记录出现前，本页只描述工作区中的已观察事实，不称其为已发布版本。

## 核心经验

1. **Skill 需要宿主执行，不能代替宿主。** 五个项目均由实际 Codex 宿主角色创建/领取任务并将命令结果登记在 Runtime；Skill 规定 Analyze→Plan→Dispatch→Verify、角色隔离和证据纪律，不会常驻运行、轮询任务或自动派发新的 Agent。要构建后台 daemon，需要额外的调度进程、身份、租约恢复、取消语义和部署证据，当前 V3 不提供也不宣称提供。
2. **同一方法可跨栈，验证器不能跨证据边界。** Harness 的 argv、路径限制、产物目录和状态词可以复用；Python/Node/JDK/WSL/微信 IDE 的实际执行器不同。Node 不替代浏览器，也不替代微信 IDE/真机；Windows 上的 `stack-probe.cxx=NOT_AVAILABLE` 不否定已记录的 WSL C++ 实测。
3. **先保留失败，再修复。** Python 和 C++ 初次独立黑盒失败来自 QA fixture，Harness 有 BUG-V3-001 首次安全失败，应用审查有修复前发现。后续通过只能新增重测证据，不能删除或改写首次 FAIL。
4. **开发者修复与独立复审是两件事。** Python Decimal/pycache、Web storage、Java 可执行名、微信累计溢出，以及 runtime review 的 4 P1/6 P2 均经历修复和独立复验；初始 FAIL/NOT APPROVED 历史仍保留。它仍不替代微信原生、非 Windows Java、生产部署或人工验收。
5. **版本迁移必须产生新执行。** 五个真实项目的 legacy model v1 已显式 adopt 为 source-bound v2，原始来源保持 `NOT_AVAILABLE`；关联 Case v2 均由新环境/执行 evidence 重新运行并 PASS，未把 v1 PASS 借给 v2。见[五应用真实生命周期追踪验证](live-lifecycle-validation.md)。

## 五个样例的实际经验

| 样例 | 已观察到的 Skill/角色闭环 | 实测证据 | 不可跨越的边界 |
| --- | --- | --- | --- |
| C++ `cpp_inventory` | 开发者 `/root/v3_cpp`、独立 Tester `/root/v3_qa_apps` 与 Reviewer 分离；规格、风险模型、manifest 和 WSL driver 已提交到工作区 | 开发者 build/unit/integration、独立黑盒 attempt 2、Runtime review 均 PASS；质量任务 DONE | Windows 原生 C++ 未安装；路径为 WSL Ubuntu 22.04 `g++ 11.4`；单写者、非生产 |
| Python `python_expenses` | 开发者、独立 Tester、Reviewer 分离；需求先于实现，保留 QA fixture 首次失败 | 开发者修复后 manifest build/unit 14 tests PASS；独立 attempt 2、legacy model adopt 后的 Case v2 真实 execution、当前源码复审均通过 | 聚合 lifecycle Case 不覆盖全部需求/NFR；无发布/验收 |
| Web `web_notes` | 领域模块/浏览器 UI 分离；Reviewer 发现 storage accessor 后开发者加 guarded adapter | Node/独立业务模块 attempt 2、当前源码复审、内置浏览器 CRUD/XSS/persistence 操作均 PASS | 存储拒绝故障注入未做浏览器级测试；静态服务不是部署 |
| Java `java_booking` | 先记录 JDK 8 缺失，再使用真实 `C:\Program Files\Java\jdk-1.8`；Reviewer 发现可执行名可移植性问题 | JDK 8 build、store 与子进程测试；独立黑盒 PASS，当前源码复审通过 | Java 8 在非 Windows 主机没有真实运行；无时区/并发设计 |
| 微信 `wechat_expenses` | 原生工程骨架与可注入 fake `wx` adapter 分离；P1 累计溢出修复先建立 RED | Node 开发者 8 tests PASS、独立 fake-`wx` attempt 2 3 tests PASS，当前源码复审通过 | 微信 IDE、AppID、真机、原生 `wx`、发布均为 NOT_AVAILABLE/NOT_EXECUTED；不可称原生通过 |

## 对后续执行的工作准则

- 每次运行前记录固定 Git SHA、manifest SHA、工具版本、命令 argv、目录和执行者；结果应由 Runtime Run 或 V3 Test Execution 保存，文本报告只索引这些事实。
- 一个失败若归为 `TEST_SCRIPT`/`ENVIRONMENT`，仍保留原命令与输出，并验证产品没有因“适配坏 fixture”而放宽需求。
- 每个修复最少需：开发者回归、独立影响重测、独立 review 复核。若涉及浏览器、原生 IDE、目标 OS 或部署，额外取得该环境的实际证据。
- `AVAILABLE` 工具仅说明本机可调用；`PASS` 只适用于实际命令和范围；人工验收、生产部署、客户价值及 Gate 决定需要不同的真实证据。

## 待验收清单

| 项目 | Evidence Status | 所需动作 |
| --- | --- | --- |
| V3 生命周期核心的独立 API/迁移/恢复/安全回归 | OBSERVED：最终 scoped review APPROVED，core/query/model/adapter 独立测试均 PASS | 容量基准与真实项目完整 Gate/acceptance 仍需另做 |
| Harness symlink/junction 分支 | NOT_EXECUTED | 在具备创建链接权限的环境执行；当前 11 PASS 不能覆盖这一项 |
| Runtime 历史 defects 的保留与关闭 | OBSERVED | 继续保留初始 FAIL、reclassification 与当前 closure/retest 记录，不重写历史 |
| Web 跨浏览器与浏览器级存储拒绝 | NOT_EXECUTED | 在非当前内置浏览器和受限存储上下文执行，保留可观察证据 |
| Java 非 Windows 实际子进程 | NOT_AVAILABLE | 在 Linux/macOS JDK 8/兼容环境执行或明确维持限制 |
| 微信原生导入、真实存储、真机/发布 | NOT_AVAILABLE | 提供微信开发者工具及必要授权后由独立测试执行；不要求虚构 AppID |
| 发布、生产部署、回滚和人类验收 | NOT_EXECUTED | 仅在授权目标环境中由真实操作员完成并保存证据 |
