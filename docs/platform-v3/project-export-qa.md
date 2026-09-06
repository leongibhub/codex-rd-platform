# TASK-V3-007 独立报告与项目导出验证

执行者：`/root/v3_qa_apps`（independent Tester）  
日期：2026-09-06  
范围：正式 `lifecycle-report` 与 `project-export` 的完整分页读取、只读来源、固定导出内容、版本/证据脱敏、完成/失败 marker 和拒绝覆盖。不是 Gate 决策、发布、部署、人工批准或整个 SQLite 文件备份结论。

## 风险模型和独立数据

依据 `TASK-V3-007` 可验证验收、`REQ-V3-002`（版本化工件）、`REQ-V3-003`（可追溯执行）、`REQ-V3-006`（执行/缺陷事实）、`NFR-V3-003`（一致读取不产生部分状态）和 `NFR-V3-005`（审计边界）设计。

每个用例新建一个临时 lifecycle 项目，不使用实现测试 helper。主用例通过公开 `Runtime.execute` 创建 `REQ-001` 两个 immutable version、Test Model 和 507 个当前 Case。为规模化读取而直接写入的 synthetic execution rows 均绑定 current Case version、current requirement reference、注册的 tester、已验证 environment evidence、同一 execution ID 的 `test_execution` evidence 及 locator SHA-256；它们是测试夹具，不是项目执行或批准证据。第 507 条为 synthetic `FAIL`，用于证明分页末尾结果不丢失。为验证 legacy/raw 记录的脱敏边界，另向隔离 DB 插入一条带有合成敏感字段、原始 stdout 与签名 URL query 的历史形状 evidence；它不是生产数据，也不绕过任何真实项目来源。

## 环境和命令

| 项目 | 实际值 |
| --- | --- |
| Host | Windows PowerShell，`D:\codex-rd-platform` |
| Python | `.venv\Scripts\python.exe --version`：Python 3.13.5 |
| 开发回归 | `.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_lifecycle_export -v` |
| 独立命令 | `.venv\Scripts\python.exe -X utf8 -m unittest tests.independent_v3.test_project_export_independent -v` |
| 被测公共接口 | 每个隔离 DB 以 CLI 运行 `-m rd_platform --db <isolated-state.db> lifecycle-report --project-id …` 与 `project-export --project-id … --output-dir …` |

## 独立用例与结果

| 用例 | 类型 / 风险 | 步骤和预期 | 实际可观察结果 | 状态 |
| --- | --- | --- | --- | --- |
| TC-V3-IND-1101 | REPORT / DATA_CONSISTENCY / 超过首个页面时遗漏失败、读取时写源、导出泄漏正文或覆盖已有证据 | 对 507 个 current Case 调 CLI report，再调 CLI project-export；逐一校验 `COMPLETE` manifest 列出的文件 byte count/SHA-256；重复同目标导出 | report 总数 507，`counts.PASS=506`，最后 `TC-507` 为 FAIL，`counts.FAIL=1`、`conclusion=FAIL`、`complete_snapshot=true`。CLI export exit 0、marker 为 `COMPLETE`，所有已列文件 hash/size 匹配；report/export 前后 source DB SQL dump digest 相同。两版 REQ 仅以版本与 `content_sha256` 导出；工件正文、raw stdout、合成敏感值及 URL query 均未出现在任一导出文件。重复导出 exit 2，原 marker hash 不变。 | PASS |
| TC-V3-IND-1102 | RECOVERY / 导出创建后目录碰撞被误作完成或覆盖 | 在真实 `export_project` 已创建目录/初始 marker 后，由独立线程创建固定 `docs` 路径的普通文件，形成实际文件系统冲突；再尝试复用同目的地 | export 抛出实际 `OSError`，`export-manifest.json` 保留且 `status=FAILED`；随后同目标仍由拒绝覆盖规则拒绝。未 mock 写入函数或导出实现。 | PASS |
| TC-V3-IND-1103 | DATA_CONSISTENCY / 已运行 PASS 的 result evidence 被改写或删除后仍被报告为 current PASS | 通过 public `test-run` CLI 实际执行一个绑定 source hash 的 `AUTOMATED argv` Case；先覆写、再删除同一个 result file；每次以 public `lifecycle-report` 及 `project-export` CLI 读取并比较 SQLite dump digest | 初始 `test-run` exit 0 且 execution 为 PASS。overwrite 与 delete 两种状态下，current row 都是 `BLOCKED`、`observed_result=PASS`、`freshness=STALE`，`historical_execution_counts={PASS:1}`；导出 report 同样为 BLOCKED 且不建议发布。每次 report/export 前后来源 DB digest 相同。 | PASS |

## Evidence freshness repair retest (attempt 2)

初始版本的 TC-V3-IND-1101 在新增 freshness admission 合同后不能再把 evidence-free `PASS` 当作可报告的 PASS：它只对末尾 Case 建立了 execution/evidence，前 506 条在重验证时应为 `NOT_EXECUTED`。这是 **TEST_SCRIPT / fixture-contract upgrade**，不是产品 BUG，也不改变已保存的初始执行证据。夹具已按上述 provenance contract 补齐后重跑。

| 阶段 | Runtime execution ID | 实际命令 | 可观察结果 | 状态 |
| --- | --- | --- | --- | --- |
| Unit | `run-0f7a6619c814495b865e8535240bced9` | `.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_lifecycle_export -q` | 12 tests，22.890s，exit 0，未截断输出 | PASS |
| Independent integration | `run-8e8ab2278d2a4ba3a55ab2f547df59de` | `.venv\Scripts\python.exe -X utf8 -m unittest tests.independent_v3.test_project_export_independent -q` | 3 tests，30.387s，exit 0，未截断输出；含 TC-1101/1102/1103 | PASS |

本地直接重跑独立套件也观察到 3/3 PASS（24.247s）；运行时质量链使用的是上表真实 `run` 记录。所有导出均来自测试临时目录；没有更改仓库模板、真实项目 DB、Gate Register、RTM 或生产数据。任务 `task-d8a1f96e12c84c4e8d21786e445e1e39` 的当前 attempt 2 已推进到 `review`（3/4 checks）；此测试并不构成 review 或 Gate PASS。

## 初始测试资产问题

| BUG | 关联用例 | 实际观察 | 处置 |
| --- | --- | --- | --- |
| BUG-QA-EXPORT-001 | TC-V3-IND-1101 | 独立测试最初将 version-index 的 artifact 标识字段误读为 `artifact_id`；实际 schema 输出字段为 `id`，导致一次 `KeyError`。这不能证明产品失败。 | 分类：`TEST_SCRIPT`（QA）。测试更正为读取 `id` 后完整重跑 2/2 PASS。 |

没有发现当前可归因于导出/报告产品实现的独立失败，因此没有创建产品 BUG。`FAILED` export marker 是本测试故意触发并已观察的恢复场景，不是交付失败。

## 未执行边界

未执行百万级容量、跨机器共享文件系统、恶意本地进程替换、真实 confidential prose 自动分类、Git commit/archive 备份恢复或生产导出。固定输出目录的父级仍需由本地受信任操作者维护；本轮的 507 行完整性证明不能扩大为上述场景的 PASS。
