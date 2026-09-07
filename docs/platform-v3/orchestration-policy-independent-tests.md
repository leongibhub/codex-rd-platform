# REQ-V3-021 独立测试模型与执行记录

状态：revision 7 独立 QA `PASS`；独立代码审查仍需单独完成。测试文件：`tests/independent_v3/test_orchestration_policy.py`。所有执行均使用临时 SQLite 数据库和临时目录；其中的 verifier、operator、证据、Gate 与微型本机文件应用都是测试 fixture，绝不是本仓的人类批准、发布、部署或验收事实。

## 风险模型

| 测试项 | Requirement / 风险 | 类型 | 可观察断言 |
| --- | --- | --- | --- |
| TC-V3-021-01 | REQ-V3-021；调用者绕开 worker 而直接执行 `Runtime.execute('work.claim')` | 安全导向、集成 | G(n) 在前置 Gate 未通过时拒绝 claim；`DONE` 仅允许 DRAFT 候选输出，且不改变 Gate。 |
| TC-V3-021-02 | REQ-V3-021；证据或需求版本变化后旧租约继续写入 | 回归、负向 | 变更 G0 证据后 G1 heartbeat 被拒；输入版本失效的工作保持 `REVIEW_REQUIRED`，不能重新 claim/finish。 |
| TC-V3-021-03 | REQ-V3-021；以实现者或普通记录代替 G9 的真实认证渠道 | 安全导向、集成 | 无 provider 返回 `NOT_AVAILABLE`；仅明确标记的 temporary synthetic verifier 可作为机制 fixture 使 G9 PASS，从而允许 G10 受策略 work claim。 |
| TC-V3-021-04 | REQ-V3-021；FAIL 被自动误分类、无限重试或用陈旧验证关闭 | 功能、负向、恢复 | FAIL 先产生单一 triage；无效 owner/category 被拒；分类后只能产生一次 fix→retest→review；失败本机命令、实际修复、实际命令重测和新鲜 reviewer 证据才能关闭 BUG。 |
| TC-V3-021-05 | NFR-V3-021；策略升级破坏既有非 bootstrap 项目 | 兼容性 | 未选择 `orchestration-v1` 的 legacy 生命周期项目仍保留原始 claim 行为。 |
| TC-V3-021-06 | REQ-V3-021；同一 case 反复 FAIL 造成无限自动 repair | 恢复、边界、负向 | 相同 case-version/需求范围的前三个 BUG 分别保留独立链；第四个 BUG 保留且为 `PENDING_HUMAN`、无 work；不同 case 仍有独立预算。 |
| TC-V3-021-07 | REQ-V3-021；repair work 在领域状态之前用无关输出伪造完成 | 集成、负向、角色隔离 | 错误角色 claim、FIXED/RESOLVED/CLOSED 前 finish 均拒绝；匹配 developer→tester→reviewer 的 lease 仅在 `defect.fix`→`resolve`→`close` 后使 fix/retest/review 三 work `DONE`。 |

## 执行命令与判定

```powershell
.venv/Scripts/python.exe -X utf8 -m unittest tests.independent_v3.test_orchestration_policy -v
```

## 实际执行证据

- 2026-09-07，revision 2 独立 unit run `run-36295e3ff451441ba05aa12725a72840`：当时独立模块 5/5 `PASS`，3.876 秒，exit code 0。
- 2026-09-07，revision 2 独立 integration run `run-798591688cdc42f9a2c6078955b05d06`：当时独立模块 5/5、实现侧策略模块 3/3、bootstrap 回归 1/1，共 9/9 `PASS`，5.514 秒，exit code 0。
- 2026-09-07，revision 3 扩展后本机预检：独立模块 7/7 `PASS`，7.449 秒，exit code 0。后续 P1 要求 public `work.create` 拒绝 repair metadata，故该预检不能作为 revision 4 证据；实现稳定后必须重新执行并登记。
- 2026-09-07，revision 5 独立 unit run `run-e41ed0cfa5dc484599bdd52f9775d810`：独立模块 7/7 `PASS`，10.204 秒，exit code 0。
- 2026-09-07，revision 5 独立 integration run `run-e0be81fb803f4e18989596b10288f33d`：独立模块 7/7、Runtime policy 6/6、bootstrap 1/1，共 14/14 `PASS`，15.590 秒，exit code 0。
- 2026-09-07，revision 6 独立 unit run `run-030bd34c65e9498a9a1aa5bc599893f0`：本机命令曾观察到独立模块 7/7 通过，但任务在登记前已升级为 revision 7；该 run 状态为 `INVALIDATED`，没有被登记为 `PASS`，也没有被用于 revision 7 结论。
- 2026-09-07，revision 7 独立 unit run `run-08b47cfd324441f0b40766671dd84027`：命令 `.venv/Scripts/python.exe -X utf8 -m unittest tests.independent_v3.test_orchestration_policy -q`，独立模块 7/7 `PASS`，10.181 秒，exit code 0。
- 2026-09-07，revision 7 独立 integration run `run-103efb41c50647f798b88e3a27d73f07`：命令 `.venv/Scripts/python.exe -X utf8 -m unittest tests.independent_v3.test_orchestration_policy tests.runtime.test_orchestration_policy tests.runtime.test_orchestration -q`，独立模块 7/7、策略集成模块 10/10、编排回归 1/1，共 18/18 `PASS`，18.196 秒，exit code 0。
- 实际本机小应用旅程在 `TC-V3-021-04` 中可观察执行：临时 `bounded_app.txt` 初始为 `BROKEN`，Python 命令实际返回 7；修复为 `FIXED` 后同一命令实际返回 0。Runtime 保留 FAIL、UNCLASSIFIED→PRODUCT 分类、唯一 triage/fix/retest/review 链、fresh retest 和 fresh reviewer close 的机制记录。它是临时测试数据，不是本仓 Bug 关闭或生产问题修复。

结论：revision 7 的独立 QA 范围通过。覆盖完整 G0→G9 的候选 v1→同内容 v2 采纳链、精确 Gate 证据、G10 依赖输入绑定、TEST_CASE 语义漂移拒绝与治理字段采纳、失败修复预算、精确领域输出绑定与关闭路径；这些仍是临时机制 fixture，不构成项目人类批准或 Gate 结论。独立代码审查尚未由本测试工作代替。若后续复审或 CI 出现失败，必须保留原始结果并创建/关联对应 `BUG`，不得用 fixture 写成真实人类批准或项目 Gate 结论。
