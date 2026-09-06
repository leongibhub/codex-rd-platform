# Platform orchestration Skill 本机正向实用验证

文档状态：DRAFT。执行者：真实宿主 `/root/v3_skill_forward`，职责 `tester`。本记录核对现有 `examples/multistack/python_expenses`，不修改应用，不声明人工批准、开发、审查、部署或发布完成。

## 委托与自决范围

本次实际委托：“核对这个费用统计工具，给我一个能看到需求到测试的本机记录，不要再问我问题，也不要改已有应用”。父任务已实际派发本 Tester。本次没有注册其他角色，历史开发者文档只作为现有规格来源。

已完整阅读 `.agents/skills/platform-orchestration/SKILL.md`、仓库 `AGENTS.md`、V3 README、生命周期 API、Stack Harness 说明以及 V2 接入说明；当前分支 `codex/platform-v3-lifecycle`，基准提交 `9655f33`。工作区存在并行开发变更。本轮只拥有本文和 `.rd-platform/forward-validation/`。

顶层项目仍为 `lifecycle_mode: template`。本次创建独立的实际核对项目；模板 Gate Register 和 RTM 不填充。核对项目的完整生命周期与所有 Gate 尚无批准证据；只计划建立需求解释、风险测试模型、用例和实际执行。

## 初始模型与假设

- 事实：现有工具公共接口为 `python expense_analyzer.py INPUT.csv`；规格和测试模型均标记 DRAFT。
- 目标与使用者：本地使用者需要核对费用统计的精确性和失败输出，并能从需求定位实际用例和结果。
- 工作流：提供本地 UTF-8 CSV → 执行命令 → 检查退出码、stdout JSON、stderr → 将输入摘要、命令和结果关联到对应版本用例。
- 数据与权限：仅本轮人工合成的费用数据；读取已有源码与规格，写入隔离状态/证据。本轮不需要客户数据、网络、安装或部署。
- 可逆假设：沿用现有 DRAFT 的 UTF-8/BOM、列顺序、Decimal 字符串、严格日期、非负有限金额和错误退出语义。它们是本次测试解释，不是新的人类批准。
- 依赖：仓库 `.venv` Python 可用；实际探测记录为 AVAILABLE。现有应用内容在执行前后以 SHA-256 比较。
- 未知与非目标：完整历史开发/审查身份与审批未导入；多币种、税、持久化、性能压力和外部部署不在本次授权范围。

## 需求解释与测试点

所有登记工件和用例保留 DRAFT 状态；没有使用 `freeze` 或生成文档来冒充确认。

| 需求 | 本次可观察验收 | 风险 / 测试点 |
| --- | --- | --- |
| REQ-FWD-001 | 有效 UTF-8（可带 BOM）、重排列 CSV 可读取 | 中文编码、列顺序错误；TP-FWD-001 |
| REQ-FWD-002 | 类别与总额为精确 Decimal 字符串，类别排序稳定 | 财务累计舍入；TP-FWD-001 |
| REQ-FWD-003 | 负值、非有限金额、坏日期和坏结构拒绝 | 坏数据产生成功汇总；TP-FWD-002 |
| REQ-FWD-004 | 无效输入/不存在文件退出 1、stdout 空且 stderr 以 error: 开头；缺参退出 2 | 自动调用方误认成功；TP-FWD-002 |

模型 `TM-FWD-001` 先定义输入/统计/输出功能树、CLI 测试对象、风险及测试点，再登记结构化用例；每例包含需求、输入、顺序步骤、预期及自动执行入口。

## 实际执行记录

执行前初始隔离 `snapshot` 返回 projects/agents/tasks/runs/events/defects 全为空；`stack-probe` 退出 0，Python/Node/Java/javac 为 AVAILABLE，cxx 为 NOT_AVAILABLE。本测试仅选择 Python 公共 CLI，工具结果不推导为其他平台验证。

实际执行时间：2026-09-06，本机 Asia/Shanghai；逐条 UTC 起止时间保留在原始记录中。驱动命令 `.venv/Scripts/python.exe -B -X utf8 .rd-platform/forward-validation/run_validation.py` 退出 0；后续映射精化与重测驱动 `.venv/Scripts/python.exe -B -X utf8 .rd-platform/forward-validation/refine_case_mapping.py` 退出 0。

| 持久化对象 | 本次真实 ID / 状态 |
| --- | --- |
| 项目 | `project-091ba3fe7f254f18a163bf168a84ba7b` |
| 唯一 Agent | `/root/v3_skill_forward` / `tester` |
| V2 核对任务 | `task-eddd90e5616e497c8abf6271a1bb679d`；implementation、unit、integration、review 没有 Run 通过证据 |
| 建模工作单 | `work-861453076d234c39abffab780df9c48c` / DONE |
| 依赖建模的执行工作单 | `work-291140b2b70a4f2ea41fcc3031cbcde3` / DONE |
| 依赖执行的映射精化/重测工作单 | `work-d8b5262d7f4e45bc8f0d241ba13e0488` / DONE |
| 新版 Skill 窄 GREEN 工作单 | `work-001b32566924400e99be358c9a89f5ae` / DONE |
| 版本化对象 | 1 BG、4 DRAFT REQ、1 测试模型、9 DRAFT 用例 |
| 执行事实 | 当前 9/9 PASS；历史 12 次 PASS（含 2 次映射修订重测及 1 次新版 Skill 窄 GREEN）；14 条 EVD；48 条含历史在内的 typed trace links |
| Gate / Release | 2 次 G7 assessment；0 次 Gate decision；0 Release；不推荐发布 |

四个工作单都在我的实际宿主执行中完成 `claim → heartbeat → finish`；租约凭据只在进程内使用，日志已移除原值。工作单 DONE 只指该工作合同完成。

| 当前用例版本 | 需求 | 实际输入 / 检查 | 退出码 / 结果 | 证据 ID |
| --- | --- | --- | --- | --- |
| TC-FWD-001 v1 | 001, 002 | 两类别；`0.10 + 0.20`；类别 a/z 排序 | 0 / PASS；a=0.30，z=2.00，总额=2.30 | EVD-TC-FWD-001；最新 EVD-FWD-GREEN-001 |
| TC-FWD-002 v1 | 001, 002 | `9999999999999999999999999999 + 2` | 0 / PASS；精确 10000000000000000000000000001 | EVD-TC-FWD-002 |
| TC-FWD-003 v1 | 001, 002 | 真实 UTF-8 BOM；`category,amount,date`；中文“餐饮” | 0 / PASS；餐饮和总额均为字符串 0.30 | EVD-TC-FWD-003 |
| TC-FWD-004 v1 | 003, 004 | amount=-1 | 1 / PASS；stdout 空，stderr 为 error: 前缀 | EVD-TC-FWD-004 |
| TC-FWD-005 v1 | 003, 004 | amount=Infinity | 1 / PASS；stdout 空，stderr 为 error: 前缀 | EVD-TC-FWD-005 |
| TC-FWD-006 v1 | 003, 004 | date=2026-02-30 | 1 / PASS；stdout 空，stderr 为 error: 前缀 | EVD-TC-FWD-006 |
| TC-FWD-007 v1 | 003, 004 | 表头使用 cost 而非 amount | 1 / PASS；stdout 空，stderr 为 error: 前缀 | EVD-TC-FWD-007 |
| TC-FWD-008 v2 | 004 | 输入路径明确不存在 | 1 / PASS；stdout 空，stderr 为 error: 前缀 | EVD-TC-FWD-008-V2 |
| TC-FWD-009 v2 | 004 | 不传路径参数 | 2 / PASS；stdout 空，stderr 为 usage: 前缀 | EVD-TC-FWD-009-V2 |

每个用例由真实独立 Tester 启动原应用的公共 CLI，检查实际退出码、独立 stdout/stderr 和精确输出；失败退出是负向用例的预期，因此这些用例 PASS 不表示被测命令退出 0。正向用例还断言 stderr 空、类别顺序和 JSON 金额字符串。没有使用内部 `analyze_csv` 函数替代公共接口。

输入文件使用真实 UTF-8 字节写入，BOM 为实际 `EF BB BF`，换行是实际 LF。BOM/中文用例输入 SHA-256 为 `9345e4a6c8ae51dcb2e93c51e2fec7a366a2878af85033db3aac01e9cb5da165`。每次 `test_execution.start` 在进程启动前登记；匹配 execution ID、Tester、用例精确版本的 VERIFIED EVD 在进程结束后登记，再 `test_execution.finish`，不存在事后补造开始记录。

TC-FWD-008/009 的初版将两个负向需求都关联到用例，复核认为范围过宽，故通过 `test_case.revise(expected_version=1)` 收窄为 REQ-FWD-004。两例 v2 已重新执行，v1 的实际执行仍为不可变历史；当前报告没有将旧 v1 执行冒充 v2 结果。原 G7 assessment 也作为历史保留，修订后重新评估。

## 需求到真实证据的可读链路

```text
BG-FWD-001 v1
  refines → REQ-FWD-001 / 002 v1
    verified_by → TC-FWD-001 / 002 / 003 v1
      executed_by → 对应真实 TEST_EXECUTION v1
        evidenced_by → EVD-TC-FWD-001 / 002 / 003
  refines → REQ-FWD-003 / 004 v1
    verified_by → TC-FWD-004 / 005 / 006 / 007 v1
      executed_by → 对应真实 TEST_EXECUTION v1
        evidenced_by → 对应 EVD
  REQ-FWD-004 v1
    verified_by → TC-FWD-008 / 009 v2
      executed_by → execution-7f18dff365834073bae30c6de7b11e0b /
                    execution-64083326158a4dd485bde899a0899317
        evidenced_by → EVD-TC-FWD-008-V2 / EVD-TC-FWD-009-V2
```

完整工程追踪仍为 PARTIAL，报告列出的缺项为 DES、TASK 工件和 CODE_CHANGE。这里的 V2 task 与 V3 work 不是伪装为开发代码变更的 TASK 工件。没有为了填满追踪而声称本轮设计/开发了已有应用。

## 本机读取与证据定位

从仓库根目录执行以下真实公共命令即可重读；它们都已执行并退出 0：

```powershell
& .\.venv\Scripts\python.exe -B -X utf8 -m rd_platform --db .rd-platform/forward-validation/state.db snapshot --project-id project-091ba3fe7f254f18a163bf168a84ba7b
& .\.venv\Scripts\python.exe -B -X utf8 -m rd_platform --db .rd-platform/forward-validation/state.db lifecycle --project-id project-091ba3fe7f254f18a163bf168a84ba7b
& .\.venv\Scripts\python.exe -B -X utf8 -m rd_platform --db .rd-platform/forward-validation/state.db lifecycle-report --project-id project-091ba3fe7f254f18a163bf168a84ba7b
& .\.venv\Scripts\python.exe -B -X utf8 -m rd_platform --db .rd-platform/forward-validation/state.db report --project-id project-091ba3fe7f254f18a163bf168a84ba7b
```

- [生命周期正式测试报告](../../.rd-platform/forward-validation/lifecycle-report.json)：`LIFECYCLE_DECLARED_TEST_SCOPE`，total=9，executed=9，PASS=9，`complete_snapshot=true`，`recommend_release=false`。
- [生命周期完整快照](../../.rd-platform/forward-validation/lifecycle.json)：需求、模型、用例版本、trace、工作单、执行、EVD、Gate 历史。
- [模块报告](../../.rd-platform/forward-validation/report.json)：V2 `MODULE_QUALITY` 为 NOT_EXECUTED，未伪造 implementation PASS。
- [首次 API 实际日志](../../.rd-platform/forward-validation/api-journal.json)、[映射修订实际日志](../../.rd-platform/forward-validation/mapping-refinement-journal.json)：公开 Runtime 调用与真实返回，包含独立身份、工作交接和 V2 拒绝。
- 每例原始记录为 `.rd-platform/forward-validation/TC-FWD-00N-result.json`；008/009 当前记录为 `TC-FWD-008-v2-result.json` / `TC-FWD-009-v2-result.json`，包含真实 argv、起止时间、输入摘要和逐项断言。
- [执行前摘要](../../.rd-platform/forward-validation/app-hashes-before.json)、[执行后摘要](../../.rd-platform/forward-validation/app-hashes-after.json)：5 个既有文件（含原有缓存）完全相同。源码 SHA-256 为 `e5b1fd29183b182d3288feba8168d7babb5112972d67493291f8d1694151193f`。命令使用 `-B` 禁止产生新的 Python 缓存。

这些隔离数据库和生成输出受 `.rd-platform` 的 Git 忽略规则管理；本文作为仓库内持续文档保留其状态与可重读入口。本 Tester 未提交代码。

## 首次使用的流程摩擦与边界

1. Skill 要求 worker 实际行动前 `run.start`；V2 新任务只能从 implementation 开始，unit 需要不同身份已完成实现。真实 `run.start(unit)` 被拒绝：`phase is not the next required quality check`。仅核对现有应用的 Tester 无法为缺失的历史实现补造 PASS。本轮已使用文档明确允许的 V3 工作租约与不绑定 V2 run 的 `test_execution` 完成测试；需要在 Skill 中明确已有应用 test-only 的分支。
2. 生命周期 API 文档列出了模型/用例大部分字段，但缺少完整可执行 payload 示例与字段值清单；本轮需要只读检查 `lifecycle_testing.py`、`lifecycle_work.py` 和 `lifecycle.py` 才能补齐精确字段。
3. Skill 正文只明确要求读 `report` 和 `lifecycle`；当前 CLI 另有 `lifecycle-report`，能给出结构化用例的正式报告。仅看 `report` 会看到 NOT_EXECUTED，而 `lifecycle-report` 正确显示本轮 9/9；两个不同分母/阶段需要明确引导，避免误读为矛盾。
4. G7 assessment 不会自动把已存在的测试环境/执行 EVD 当成全部 Gate 条件证据；需要 Gate criterion metadata、合格工件与前置 Gate。真实 candidate 为 BLOCKED，缺合格 test_plan、executable_cases、test_environment、test_results、defect_summary、regression、test_conclusion 和前置 G0 PASS/完整追踪。G7 Evaluation State 为 IN_REVIEW、`gate_status=null`，其余 Gate 为 NOT_EVALUATED；这不是已做 BLOCKED Gate decision。
5. 生命周期实现正处于并行加固，本轮公共 API 未发生临时崩溃或成功后的接口替换错误。文档对工作租约恢复和人工批准入口的介绍与读取时源码已有差异，但本轮未调用这些能力，不据此宣称其执行结果；未修改产品代码绕过限制。

本次没有发现费用 CLI 违反所选 9 例预期的产品缺陷；这不覆盖所有输入或全部非功能需求。独立审查、人工验收和发布证据为 PENDING；性能、压力、稳定性测试为 NOT_EXECUTED。本次功能用例通过不意味着任一 Gate PASS 或可发布。Skill 在本轮实际促成了先建模后执行、真实身份与租约、精确版本证据、历史保留及显式未执行边界；以上摩擦来自完整走通本机流程，而非仅阅读后的泛泛意见。

## Skill 修订后的窄 GREEN 验证

父任务根据上述发现修改了 Skill 第 3 步，并明确 `lifecycle-report` 与 `report` 的区别以及缺少 authenticated approval provider 的限制。本 Tester 完整重读新版 Skill 和更新后的生命周期 API 后，实际恢复同一个隔离项目；没有重建项目、登记其他身份、重新创建模型或重跑全部 9 例。

已读版本的 Skill SHA-256：`20bd352067d4074c217ac8f58223d86dac504592d73e15e3d978796eca445296`。新版明确指示：已有代码且无 V2 实现记录的 verification-only 工作直接使用 V3 work 与 test_execution。因此本次直接创建并领取 G7 verification 工作，复用 TC-FWD-001 v1、原环境 EVD 和原源码摘要，再执行一次真实公共 CLI。

| 观察 | 实际结果 |
| --- | --- |
| 新工作 | `work-001b32566924400e99be358c9a89f5ae`；真实 Tester claim/heartbeat/finish；DONE |
| 新执行 | `execution-9e871916a3f64cdba35b7220a2f20c29`；TC-FWD-001 v1；PASS |
| 新证据 | `EVD-FWD-GREEN-001`；源版本、退出码和全部 5 个断言满足 |
| 命令 | `.venv/Scripts/python.exe -B -X utf8 .rd-platform/forward-validation/green_resume.py`；修正读取脚本后退出 0 |
| 应用实际结果 | 退出 0；stdout 为 `{"categories":{"a":"0.30","z":"2.00"},"total":"2.30"}`；stderr 空；源码摘要不变 |
| 模块路线 | 未调用 run.start；未新建开发者或 reviewer；V2 仍无通过 Run |
| 模型边界 | 复用原 DRAFT 用例，未将旧模型声明为 BASELINED；未调用 adopt、未伪造历史来源 |
| 报告 | 实际分别调用 lifecycle-report/report/lifecycle/snapshot，均退出 0；正式用例仍 9/9 PASS，历史 12 次执行，recommend_release=false |

本次首次运行的独立测试驱动误以为 snapshot 顶层字段为 `project`，真实返回字段为 `lifecycle`，导致 `KeyError: 'project'`。错误发生在 `work.create` 和应用执行之前，归属于本 Tester 的读取脚本，不是平台或费用应用失败。已保留[初始错误记录](../../.rd-platform/forward-validation/green-driver-preflight-failure.json)，根据已观察接口修正字段后重新执行完整窄 GREEN。

结果与完整 API 顺序分别见 [GREEN 实际摘要](../../.rd-platform/forward-validation/green-summary.json)、[逐条真实调用](../../.rd-platform/forward-validation/green-api-journal.json)、[公共 CLI 原始结果](../../.rd-platform/forward-validation/green-execution-result.json)。新版已消除本轮发现的 verification-only 路由摩擦，报告范围的区别也已写明并验证；完整 payload 示例不足的易用性问题仍可改进。审批 provider 的不可用边界仅阅读并遵守，本轮未调用或声称验证真实人工批准。
