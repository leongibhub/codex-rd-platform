# 五应用真实生命周期追踪验证

执行者：/root/v3_qa_apps（Tester）
范围：将五个已经 lifecycle.initialize 的真实应用项目，从当前 REQ/CODE_CHANGE 工件追踪到新的 suite-level Test Model、Test Case、Environment Evidence 与 Test Execution。它不是 Gate、发布、部署、人工验收，且不将一条聚合用例误述为所有子需求或 NFR 覆盖。

## 前置观察

- 五个现有 REQ 与 primary CODE_CHANGE 工件均为 version 1，且各自已登记 SHA-256 与当前工作区文件一致。
- 每项已有 G0 的 Evaluation State 是 IN_REVIEW，Gate Status 为空；没有变更 G0 或创建任何 Gate PASS。
- 原独立测试报告 artifact 的文件内容在此前写入后可能已演进。本次只绑定 SHA 匹配的 REQ/CODE_CHANGE，不修订、不重置该历史 DOC artifact。

## 新建模型、用例和实际执行

| 应用 | 当前绑定 | 新模型 / 聚合用例 | 新环境和执行证据 | Execution | 实际命令结果 |
| --- | --- | --- | --- | --- | --- |
| C++ inventory | REQ-MATRIX-CPP-INVENTORY v1；CODE-MATRIX-CPP-INVENTORY v1 | TM-LIVE-MATRIX-CPP；TC-LIVE-MATRIX-CPP | EVD-LIVE-ENV-CPP；EVD-LIVE-EXEC-CPP | execution-54eb68fe5c534a08b6bc0b745cf4e957 PASS | 独立公共 CLI unittest，退出 0。 |
| Python expenses | REQ-MATRIX-PYTHON-EXPENSES v1；CODE-MATRIX-PYTHON-EXPENSES v1 | TM-LIVE-MATRIX-PY；TC-LIVE-MATRIX-PY | EVD-LIVE-ENV-PY；EVD-LIVE-EXEC-PY | execution-2b06444e58d94f61a7366be592238e47 PASS | 独立 CSV CLI unittest，退出 0。 |
| Web notes | REQ-MATRIX-WEB-NOTES v1；CODE-MATRIX-WEB-NOTES v1 | TM-LIVE-MATRIX-WEB；TC-LIVE-MATRIX-WEB | EVD-LIVE-ENV-WEB；EVD-LIVE-EXEC-WEB | execution-53dda8756de24f4a9d83799435b61c66 PASS | 独立 Node business-module suite，退出 0；不替代浏览器 E2E。 |
| Java booking | REQ-MATRIX-JAVA-BOOKING v1；CODE-MATRIX-JAVA-BOOKING v1 | TM-LIVE-MATRIX-JAVA；TC-LIVE-MATRIX-JAVA | EVD-LIVE-ENV-JAVA；EVD-LIVE-EXEC-JAVA | execution-7be5d934c70a47259afdc8fe58d83098 PASS | 独立 Java public-CLI unittest，退出 0。 |
| WeChat expenses | REQ-MATRIX-WECHAT-EXPENSES v1；CODE-MATRIX-WECHAT-EXPENSES v1 | TM-LIVE-MATRIX-WECHAT；TC-LIVE-MATRIX-WECHAT | EVD-LIVE-ENV-WECHAT；EVD-LIVE-EXEC-WECHAT | execution-00f701f21f4e4d0e9905af69c6c35953 PASS | 显式 fake wx 的 Page adapter Node suite，退出 0；非原生微信结果。 |

每个 Test Model 含一个 FUNCTIONAL 测试对象、一个 P1 风险和一个明确的 aggregate test point；每个 Test Case 包含前置条件、合成数据说明、步骤、预期结果与自动化入口。每项建立 REQ -> TEST_CASE verified_by trace；执行证据 metadata 同时锁定 TEST_CASE、REQ 与 CODE_CHANGE 当前版本。环境和执行证据均以实际 Tester /root/v3_qa_apps 登记，执行不是导入旧 PASS。

随后对每个真实 lifecycle snapshot 调用正式 lifecycle_report：每个快照显示 1 个 model、1 个 case、1 个上述 PASS execution，report conclusion 为 PASS、complete_snapshot 为 true、recommend_release 为 false。这个 conclusion 仅汇总当前登记的聚合 Case 执行，绝不等同完整需求/NFR 覆盖、G7 PASS、发布或验收。

## Test Model 版本迁移与 v2 重执行

模型版本化完成并由模型维护者 freeze 后，执行者 `/root/v3_qa_apps` 对以上五个 valid legacy v1 Test Model 分别调用 `test_model.adopt`：`expected_version=1`、目标状态 `BASELINED`，并记录“当前维护者确认来源；原始 v1 历史来源为 `NOT_AVAILABLE`”。这不是对旧定义作者、人工审批或历史来源的补写。每个模型现在均为 version 2、`CURRENT`、`BASELINED`，其 v1 不可变 artifact history 保留且 `legacy_source_status=NOT_AVAILABLE`。

adopt 后已有 Case 被系统置为 `REVIEW_REQUIRED`；随后对原有定义调用 `test_case.revise(expected_version=1)`，使每个 Case 成为 version 2、`BASELINED`、`AUTOMATED` 并绑定对应 model version 2。以下是新的、非导入的 v2 实际执行；每项均严格按“环境 evidence -> `test_execution.start` -> 实际命令 -> execution evidence -> `test_execution.finish`”完成，环境/执行 evidence 均锁定 Case v2、REQ v1 与 CODE_CHANGE v1。

| 应用 | Adopted model / revised case | v2 环境与执行证据 | 新 Test Execution | 实际可观察结果 |
| --- | --- | --- | --- | --- |
| C++ inventory | TM-LIVE-MATRIX-CPP v2；TC-LIVE-MATRIX-CPP v2 | EVD-LIVE-ENV-CPP-V2；EVD-LIVE-EXEC-CPP-V2 | execution-0713a3b2ee9142fc80f6c079b4b7faf2 PASS | 公共 CLI unittest：2/2 PASS，exit 0。 |
| Python expenses | TM-LIVE-MATRIX-PY v2；TC-LIVE-MATRIX-PY v2 | EVD-LIVE-ENV-PY-V2；EVD-LIVE-EXEC-PY-V2 | execution-4738d4b39f5541a5bc1dcf886cc6b4a3 PASS | CSV CLI unittest：5/5 PASS，exit 0。 |
| Web notes | TM-LIVE-MATRIX-WEB v2；TC-LIVE-MATRIX-WEB v2 | EVD-LIVE-ENV-WEB-V2；EVD-LIVE-EXEC-WEB-V2 | execution-aa0589f424264cd28bd56fe5458775f0 PASS | Node business-module suite：3/3 PASS，exit 0；浏览器 E2E 未执行。 |
| Java booking | TM-LIVE-MATRIX-JAVA v2；TC-LIVE-MATRIX-JAVA v2 | EVD-LIVE-ENV-JAVA-V2；EVD-LIVE-EXEC-JAVA-V2 | execution-711777fe49c34d24b0ad4fed4160175d PASS | Java public-CLI unittest：2/2 PASS，exit 0。 |
| WeChat expenses | TM-LIVE-MATRIX-WECHAT v2；TC-LIVE-MATRIX-WECHAT v2 | EVD-LIVE-ENV-WECHAT-V2；EVD-LIVE-EXEC-WECHAT-V2 | execution-3e20a3c741c74c209dd7b7eb13335408 PASS | fake-wx Page-adapter Node suite：3/3 PASS，exit 0；原生微信/IDE/真机未执行。 |

每个最新 snapshot 同时保留相应 Case v1 的历史 PASS 和上表 Case v2 的新 PASS；最新 `lifecycle_report` 均显示 `conclusion=PASS`、`complete_snapshot=true`、`recommend_release=false`。这仅验证版本化的 spec/code -> model/case v2 -> execution/evidence/report 可追溯链；不改变既有 G0/G7 状态，也不构成完整需求、NFR、浏览器/原生 E2E、Gate、发布或人工验收结论。

## G7 assessment：故意不作决定

| 应用 | Assessment | Candidate | 明确缺口 |
| --- | --- | --- | --- |
| C++ | assessment-4f2b496ba2b445e7890285595b1226d3 | BLOCKED | G0 未 PASS；test_plan、executable_cases、test_environment、test_results、defect_summary、regression、test_conclusion 缺 Gate 合格证据。 |
| Python | assessment-2ad04f79829c4013b055a11f095cf164 | BLOCKED | 同上。 |
| Web | assessment-3a064dfc6cbf482c92ca0ad1ae6d5836 | BLOCKED | 同上；此 Node 结果也不覆盖浏览器 E2E。 |
| Java | assessment-cf033d3594e145a5a1a8ab65d3c47aa1 | BLOCKED | 同上。 |
| WeChat | assessment-a8112a2929104af3b938cbaa52979310 | BLOCKED | 同上；fake wx 不覆盖 IDE、原生 wx、真机或发布。 |

没有执行 gate.decide，也没有登记 human approval、发布、部署或 release recommendation。本次仅证明真实状态可从 spec/code 工件进入可见的 Case/Execution/Evidence/Report 链，而不证明项目已通过完整 G7 或任何更高 Gate。
