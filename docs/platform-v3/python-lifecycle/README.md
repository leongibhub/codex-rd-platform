# Python 费用工具的逐需求生命周期核对

任务：TASK-V3-008。范围是核对既有 `python_expenses` 的当前 Git 基线，并使每条 REQ/NFR 有版本化测试证据；不重新开发应用，不倒造先前项目过程。

当前阶段由独立运行库的有效 Gate 记录决定。本目录文档是本次基线解释、设计观察与验证计划。BASELINED 表示固定本次工作输入，APPROVED/人工批准不得由脚本产生。G0–G8 的决定必须来自真实独立 Reviewer；G9 人工验收另需真实批准服务和决定。

## 可重放入口

```powershell
# 参数中的 actor 必须是宿主实际派发并接受工作的身份；不能借用例子中的角色名。
& .\.venv\Scripts\python.exe -B -X utf8 scripts/validate_python_lifecycle.py prepare --output-dir .rd-platform/python-lifecycle/actual --documents-dir docs/platform-v3/python-lifecycle/runs/actual --actor /root/v3_skill_forward --host-assignment "TASK-V3-008 harness implementation accepted by actual host"

# 由独立 Tester 实际执行，使用其真实 actor 与 host assignment。
& .\.venv\Scripts\python.exe -B -X utf8 scripts/validate_python_lifecycle.py execute --output-dir .rd-platform/python-lifecycle/actual --actor ACTUAL_TESTER_ID --host-assignment "Actual independently assigned test execution"

# Reviewer 在同一数据库登记真实 review 和 G0–G8 决定后，传已存在的 EVD ID 清单。
& .\.venv\Scripts\python.exe -B -X utf8 scripts/validate_python_lifecycle.py finalize --output-dir .rd-platform/python-lifecycle/actual --review-evidence REVIEW_ID_BUNDLE.json
```

`prepare` 可恢复同一个 run.json 所指项目；它固定源码摘要、连续文档、工件/模型/用例并输出评审计划。`execute` 在真实命令前登记 Test Execution，完成后附 argv、输入摘要、退出码、输出、断言；已完成版本不会因重启被重复执行。旧失败不会被自动关闭。进程退出只说明自测命令结果；测试数量与断言另外核验。

`test-report.md` 是执行时保存的不可变原始报告，不会在恢复时补写新字段或更新时间。旧报告缺少 freshness 字段（或记录 `NOT_CHECKED`）不是当前有效性证明：恢复和可更新的 `test-report.json` 导出会另外查询正式当前报告，重新验证执行证据文件摘要、来源和版本。当前 `STALE`/`BLOCKED` 不得沿用原 `PASS`；只有已知派生注释的兼容变化可以通过，case/执行/结果/需求/证据/环境/source 绑定仍须保持一致。

`finalize` 不创建 reviewer、人类批准、review EVD 或 Gate PASS。输入格式为 `{"reviewer_id":"实际独立身份","evidence_ids":["已经登记的 EVD ID"]}`。缺证据、错角色、作者自审、引用不完整、未完成或失效 Gate 均返回待处理状态。`promotion-plan.json` 导出逐 Gate 的 API 格式；占位符是待填写请求模板，不是已执行事实。

生成的数据库/原始命令输出在隔离输出目录；本次文档与执行报告在 `--documents-dir`，所有 path-backed 工件锁定文件摘要。请将报告与其原始运行目录一并保留；不要把本机数据库提交进 Git。

## 事实来源及边界

- [项目与调研模型](project-model.md)：用户委托、推断、适用性评估与风险。
- [需求/NFR](requirements.md)：每条输入、可观察结果和未新增的承诺。
- [当前架构观察](architecture.md)：依据实际源代码，不沿用旧设计的失效函数名。
- [执行计划](plan.md)：依赖、分工、风险测试点、真实执行与评审交接。
- [独立评审合同](review-contract.md)：G3/G4/G8 的真实评审与 G0–G8 推进方法。

市场、竞品和外部技术研究在这个固定应用的本机验证项目中只进行有依据的适用性判定，不编造市场数据。并发压力、长期稳定性、网络隔离监测、生产部署和客户验收不在本次测试范围。任何 G0–G8 PASS 也不意味着这些项已执行。
