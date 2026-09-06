# TASK-V3-008 独立评审 / Independent Review

评审结论：**APPROVED FOR G0–G8**。在本次“既有 Python 费用 CLI 的本机、合成数据、逐需求生命周期核对”范围内，没有未解决的 P0/P1/P2。该结论不是 G9 人工验收、生产发布、部署成功或客户认可。

Review conclusion: **APPROVED FOR G0–G8**. No unresolved P0/P1/P2 finding remains within the scoped local, synthetic-data, requirement-by-requirement verification of the existing Python expense CLI. This is not G9 human acceptance, production-release authorization, deployment evidence, or customer approval.

## 1. 身份、范围与不可变输入 / Identity, scope, immutable inputs

- Reviewer：真实宿主 actor `/root/v3_python_gate_review`，角色 `reviewer`；不同于 harness developer `/root/v3_skill_forward` 和实际 Tester `/root/v3_qa_platform`。
- 项目：`project-337a2843b20e407981e60c2a28c605e4`；主 Runtime 任务：`task-a21f85188f1b439096f4351c54cea0cf`，attempt 3。
- 实际观察截止：`2026-09-06T11:01:23.7327516Z`。
- 评审对象：`docs/platform-v3/python-lifecycle/` 全部基线与执行报告、`scripts/validate_python_lifecycle.py`、`examples/multistack/python_expenses/`、测试以及隔离库 `.rd-platform/python-lifecycle/actual/state.db`。
- 既有应用 Git 基线：commit `6665bc5a5c4c441b523f9249dd860b7695daec72`；当前 `expense_analyzer.py` blob `a355686929a2128263d705e381e76d3be00c11f4` 与该提交一致。本次没有修改应用源码。

| 评审输入 | 当前版本/摘要 |
| --- | --- |
| `expense_analyzer.py` | SHA-256 `e5b1fd29183b182d3288feba8168d7babb5112972d67493291f8d1694151193f` |
| `manifest.json` | SHA-256 `34456a238a3e9ba1cfe495d4b3f2c7b958f597c6956afa94be58629e0c12fe90` |
| 应用开发者单元测试 | SHA-256 `53016b1113237a79e928f2b92308a577856c6b4e8719d94e4b2d61ac76f5249d` |
| `CODE-PLC-HARNESS` | v4；SHA-256 `74e7e8e45eff52ec959dbb5924da39501bb1f717fe76f7067a7c290934753f8a` |
| `DOC-PLC-TEST-REPORT` | v2；Tester 创建；SHA-256 `3e7335ef45355cf1408319f59b4b66c640f85f54f66100f2ee5a9389c87e243d` |
| `DOC-PLC-REVIEW-SCOPE` | v1；SHA-256 `ffd76c6a290c9f64c0273ceab3e8df038f64f525e3e6b7c1221b36c23a88cf54` |

## 2. 具体发现与处置 / Concrete findings and disposition

### 已解决 P2：REV-V3-PLC-001 — 报告生成后的崩溃窗口不可恢复

旧实现若在 test report/EVD 已持久化后、`work.finish` 或本地完成索引保存前崩溃，恢复会重新生成带新时间戳的不可变报告并失败。Reviewer 实际复现了“1 条 execution 已 FINISHED、报告存在、索引未完成、重试抛出 immutable document different content”，并在主 Runtime attempt 1 记录失败 `run-3147240a692c41daa21941925143c7f6`。

v4 将恢复与重新执行分离：验证已持久报告、当前 case/execution/环境/source 绑定，复用原字节；DONE work 仅补完成索引，不重新 claim 或重复运行。当前回归覆盖两个相邻崩溃窗口、报告篡改、新 case 版本和执行不重放。独立 attempt 3 unit 及本 Reviewer 重放均通过。结论：**RESOLVED**。

### 已解决 P2：BUG-V3-008 / REV-V3-PLC-002 — 旧报告 schema 兼容与当前证据 freshness

attempt 2 integration `run-d3ece0fdd6604ca584805c2c23a3cdd9` 实际退出 2：当前报告新增 `observed_result/freshness/freshness_reason` 派生字段，使未改变的历史 37 条结果无法恢复。进一步审查发现，仅忽略新字段仍会漏掉 path-backed execution EVD 被替换后的失效状态，因为原始 `lifecycle_snapshot` 保存历史观察但不重验文件摘要。

v4 仅规范化三个已知派生注释：缺省 `observed_result` 按旧 `result` 解释；只接受无失效理由的 `NOT_CHECKED/CURRENT/NOT_APPLICABLE` 兼容表示；身份、版本、需求、结果、execution/EVD 引用与未知字段仍精确比较。恢复和可更新 JSON 导出调用正式 `lifecycle_report_from_runtime`，要求有实际 PASS/FAIL 的 execution 当前 freshness 为 `CURRENT`；`STALE/BLOCKED`、结果变化或引用漂移会拒绝旧 PASS。回归包含 legacy schema RED→GREEN、EVD 文件摘要漂移拒绝及绑定字段不可忽略。结论：**RESOLVED**。

### 未解决发现统计 / Unresolved finding count

| 严重度 | 未解决 | 评审判断 |
| --- | ---: | --- |
| P0 blocker | 0 | 无 |
| P1 critical | 0 | 无 |
| P2 major | 0 | 两项历史 P2 均有真实失败记录、修复和独立重测 |
| P3 minor | 0 | 没有发现范围内代码缺陷；下述边界是明确排除项，不伪装成已验证能力 |

## 3. 需求、测试与证据完整性 / Requirements, tests, and evidence integrity

正式隔离库中有 37 个唯一、当前 v1 用例和 37 个唯一 execution；全部 `FINISHED/PASS`，执行者均为 `/root/v3_qa_platform`，没有新增或活动 execution。Reviewer 重新调用正式 freshness 投影，得到 `CURRENT=37`、`observed_result=PASS 37`、`PASS=37 / FAIL=0 / BLOCKED=0 / NOT_EXECUTED=0`、`complete_snapshot=true`、结论 PASS。所有 7 条 RTM 状态均为 `COMPLETE`，隔离项目缺陷数为 0。

| Requirement | 当前 PASS/总数 | 关键分区 |
| --- | ---: | --- |
| REQ-MATRIX-PY-01 | 8/8 | UTF-8/BOM、列顺序、缺/多/重复表头、缺/多字段、非法 UTF-8 |
| REQ-MATRIX-PY-02 | 4/4 | 排序、跨类别、零值、长 Decimal 精确加法 |
| REQ-MATRIX-PY-03 | 15/15 | 空输入、日期、类别、金额、负值、NaN/sNaN/±Infinity |
| REQ-MATRIX-PY-04 | 23/23 | 数据/路径错误退出 1、参数错误退出 2、stdout/stderr 合同 |
| NFR-MATRIX-PY-001 | 3/3 | 精确值与 JSON 字符串 |
| NFR-MATRIX-PY-002 | 9/9 | 1000/1001 位、指数 ±1000/±1001、100000/100001 行 |
| NFR-MATRIX-PY-003 | 2/2 | 成功/失败输入不变；每例另核对应用 source 摘要 |

关键证据链：

- 实际 Tester 报告修订为 `DOC-PLC-TEST-REPORT v2`，创建者为真实 Tester；`EVD-PLC-G7-DOC-V2` 与 `EVD-PLC-CONCLUSION-V2` 分别取代 v1 记录，不删除历史。
- 37 个结果文件的 locator SHA-256、case/execution 版本、Requirement 与 EVD 引用均经 Tester 和 Reviewer 当前投影复核；没有 `STALE` 或缺失引用。
- 应用开发者 suite 由 Reviewer 独立重跑 14/14 PASS；六种表头排列使用真实多字节 UTF-8 中文再次黑盒运行 6/6 PASS。
- harness v4 独立 QA unit：`run-59085c8d26fa44c09cb1dbc83004b744`，16/16 PASS，exit 0，49.922070 s。
- harness v4 独立 QA integration：`run-648d2d22ec674c44b8d7b1382bb6ec3c`，同一真实 Tester 的恢复调用 exit 0，5.982997 s，37 execution 数量保持不变。
- Reviewer 独立重放 harness 契约：16/16 PASS，50.159 s；包括报告篡改拒绝、legacy schema、证据摘要漂移、新 case 版本与两个恢复窗口。

## 4. 源码、架构、安全和失效处理 / Code, architecture, security, and failure handling

### 既有费用 CLI

- `argparse` 固定一个路径参数；参数错误保持退出 2。`main` 用 `utf-8-sig` 与 `newline=""` 打开输入，业务/文件/编码/CSV 错误统一写 stderr 并退出 1，成功只输出一次 JSON。
- `_validate_header` 精确核对三列且允许排列；每行显式拒绝缺/多字段。日期同时验证固定格式与真实日历日期，类别 trim 后不得为空。
- `_parse_amount` 使用 `Decimal`，拒绝空、非法、非有限、负值及超出有效位/指数限制；聚合精度按最大 adjusted exponent、最小 exponent 与行数 carry 计算，避免默认 Decimal context 舍入。
- 成功 JSON 的金额为字符串，类别排序；输入全部验证后才生成输出，不泄露部分成功对象。
- `MAX_ROWS=100000` 在追加后立即检查；100001 行拒绝。输入内容与应用文件由 harness 前后 SHA-256 核对。

### 生命周期 harness

- 子进程使用 argv 数组且 `shell=False`，固定工作目录和隔离 build/cache；不执行外来 shell 文本，也不将应用目录作为输出目录。
- prepare/execute/finalize 经公开 Runtime facade 写入事实；developer、tester、reviewer 身份相互独立。finalize 只能消费已有 review EVD 与有效 Gate 决定，不能生成 reviewer、人类批准或默认 PASS。
- 报告恢复同时验证不可变历史绑定与正式当前 freshness；报告缺失、作者不符、hash 改变、source/case/execution/environment/EVD 漂移均 fail closed。
- 恢复不会将旧 case 版本当作当前 PASS，不会重领 DONE work，不会静默处理 ACTIVE execution；已知冲突需要显式处理。

架构描述与当前源码一致：本地单进程、标准库、文件输入、stdout/stderr/退出码输出，无服务端、数据库或外部账户集成。`DES-PLC-001` 的组件、数据、错误、安全和部署边界没有发现偏差。

## 5. 明确残余边界 / Explicit residual boundaries

下列能力没有需求承诺，也没有被本评审推断为完成：恶意程序沙箱或网络隔离监测、并发/压力、长期稳定性、性能 SLA、文件字节上限、类别字符串长度上限、真实账单或多币种语义、依赖安装、生产部署、客户验收。对超长单字段的内存放大风险由本地可信输入与已声明非目标约束；若未来扩大到不可信上传服务，必须新增输入字节/字段长度限制和资源测试。该边界不影响当前 G0–G8 的有界本机验证结论，但必须在 G9/G10 范围决定时重新评估。

## 6. Gate 审查判断 / Gate review judgement

| Gate | Reviewer 判断 | 依据摘要 |
| --- | --- | --- |
| G0 | PASS candidate | 章程、理由、目标、范围、职责、计划、初始风险均明确且来源可核查 |
| G1 | PASS candidate | 固定既有工具无需市场/竞品选择；适用性理由、技术来源、可行性均明确，不虚构外部研究 |
| G2 | PASS candidate | 愿景、用户、旅程、优先级、可测产品验收和非目标齐全 |
| G3 | PASS candidate | 4 REQ + 3 NFR、接口/数据/安全、可测标准、独立需求审查及 7/7 COMPLETE RTM |
| G4 | PASS candidate | HLD/组件/API/数据/部署/安全/失败处理、3 个 ADR 与独立架构审查符合当前源码 |
| G5 | PASS candidate | 实现/测试计划、任务依赖、任务到需求追踪、风险分区与恢复策略完整 |
| G6 | PASS candidate | 既有实现 Git 基线、单元测试、文档、commit/source 追踪、本地验证及 v4 修复证据完整 |
| G7 | PASS candidate | 37 个可执行用例、环境、当前 VERIFIED EVD、缺陷摘要、回归与最终测试结论完整 |
| G8 | PASS candidate | 本报告覆盖 code review、architecture conformance、security/regression risks、classified findings；无未解决 P0/P1/P2 |

Reviewer 将按 G0→G8 逐项读取 Runtime assessment，仅在 candidate 为 PASS、input digest 当前且 decision evidence 精确绑定本报告和当前对象版本时登记实际 PASS。G9/G10/G11 保持 `NOT_EVALUATED`；没有 human approval provider，不建议发布。

