# 平台 V3 全生命周期扩展设计

- Record ID: `DES-V3-001`
- Change: `CR-V3-001`
- Document State: `BASELINED`
- 基线：V2 提交 `9655f33`，现有 `Runtime`、SQLite、CLI、看板和四阶段模块质量闭环继续有效。
- 需求来源：用户要求继续实现完整平台，并用同一 Skill 生成和验证 C++、Python、Web、Java、微信小程序等主流应用；用户要求不再就普通实现细节提问。该指令授权实施和测试，不等于任何测试、Gate、发布或验收已通过。

## 1. 目标、边界与验收需求

V3 将 V2 从“可观察的模块交付运行时”增量扩展为“宿主辅助的全生命周期工程控制面”。模型仍由 Codex 等外部宿主提供，仓库运行时负责持久事实、契约校验、依赖、追踪、Gate 评估、测试执行记录和可观察性；它不伪装成后台自主模型服务。

| ID | 可验证需求 |
| --- | --- |
| `REQ-V3-001` | 项目具有独立于 V2 调度状态的 G0–G11 生命周期实例，并可恢复当前阶段、候选动作、阻塞项和用户待决事项。 |
| `REQ-V3-002` | 需求、设计、任务、代码变更、测试模型、测试用例、缺陷、发布和生命周期文档均为带版本、状态和来源的结构化工件。 |
| `REQ-V3-003` | 追踪关系按类型校验，可计算 Requirement→Design→Task→Code→Test Case→Execution→Defect→Release 的 COMPLETE/PARTIAL/GAP 状态。 |
| `REQ-V3-004` | Gate 仅由类型正确、状态合格、版本未失效的证据评估；缺少证据不产生 PASS，需人工批准的 Gate 不得由模型代签。 |
| `REQ-V3-005` | 测试先建立功能树、风险、测试对象、测试类型和测试点，再产生结构化且可自动化的 Test Case。 |
| `REQ-V3-006` | Test Case 可映射真实自动化命令和执行证据；失败创建分类待定缺陷，修复后只重跑影响集并执行回归。 |
| `REQ-V3-007` | Release 只有在 G10 决策、交付清单、部署/回滚材料和准出证据满足策略时可进入 READY；RELEASED 还必须有真实部署证据和明确操作员动作。 |
| `REQ-V3-008` | 看板同时显示项目、Agent、Task、Workflow、Artifact、Trace、Test、Defect、Gate、Release 状态，并能解释“为何等待、缺什么、下一步谁处理”。 |
| `REQ-V3-009` | pause/resume/retry/reject/modify/reassign/skip/rollback 均形成事件；变更只作废受影响版本及下游证据，不从头重做无关工作。 |
| `REQ-V3-010` | 同一 `platform-orchestration` Skill 至少驱动 Python、C++、Web、Java、微信小程序五类样例，并逐项记录生成、构建、单测、集成/黑盒、独立 review 的真实结果或明确不可执行原因。 |
| `NFR-V3-001` | V2 API、数据库内容和 G0–G11 编号兼容；升级为只增表迁移，旧版本可忽略新表。 |
| `NFR-V3-002` | 单机 SQLite 的**设计容量目标**为 100 个项目、10 万工件版本、100 万事件；这不是已取得的性能结果，必须经容量基准后才能宣称满足。查询必须分页并有组合索引，内容大于 1 MiB 改存仓库文件并记录摘要。 |
| `NFR-V3-003` | 运行状态改变、事件和幂等结果在同一事务提交；进程退出、重复请求和宿主断线可恢复，不产生部分 Gate/Release 决策。 |
| `NFR-V3-004` | HTTP 仍为 loopback 控制面且不能执行任意命令；工作区路径必须限制在项目根目录；凭据仅保存引用或脱敏摘要。 |
| `NFR-V3-005` | 所有决策、版本失效、证据来源、Agent 交接和外部执行均可审计；生成时间戳不能替代发生时间或人工批准。 |

不在当前本地控制面的能力：多租户身份认证、云端模型托管、恶意代码安全沙箱、未经授权的生产部署、代替真人验收。微信开发者工具、Apple/Android SDK 等外部专有工具也不随仓库分发。

## 2. 架构选择与 ADR

### ADR-V3-001：在 V2 单体内增加版本化生命周期域

**选择**：保留 `rd_platform.runtime.Runtime.execute()`、`snapshot()` 和全部 V2 表；新增 `LifecycleService`，由 `Runtime` 在同一事务内调用。新增表使用 `lc_` 前缀，不给现有表加列。

**备选**：重写 V2；或立即拆为事件总线和多个微服务。重写会丢失已验证的并发、幂等和证据规则；微服务会在当前单用户规模引入部署和一致性成本。增量模块化单体可回滚、易测，并保留以后按接口拆分的边界。

**后果**：V2 `snapshot()` 的顶层结构保持不变；V3 使用单独的 `lifecycle_snapshot()`。旧代码可读取升级后的数据库；若回退旧代码，新表保留但不被解释。迁移前仍应备份 `.rd-platform/state.db`。

### ADR-V3-002：关系型索引保存元数据，仓库保存大工件

**选择**：状态、关系和小型 JSON 保存 SQLite；SRS、设计、报告、源码清单等正文保存在项目仓库，数据库保存仓库相对路径、SHA-256、Git commit 和媒体类型。小于 64 KiB 的结构化模型允许内联，单版本硬上限 1 MiB。

**备选**：全部正文进 SQLite；或只扫描 Markdown。前者使 Git 评审和差异追踪变差，后者不能原子校验状态、关系和幂等。混合模型让 Git 继续成为工程记录，SQLite 成为运行事实索引。

### ADR-V3-003：Gate 采用“机器评估 + 明确决策”两步

**选择**：`gate.assess` 只产生候选结论、缺失项和策略版本；`gate.decide` 才能写 Gate Status。策略要求人工批准时，必须引用 `kind=human_approval,status=VERIFIED` 的证据，并记录可信宿主提供的操作者标识；模型输出不能创建该证据。

**备选**：满足检查后自动 PASS；或 Gate 全靠手工 Markdown。自动 PASS 会把存在误判的校验当成授权，纯手工无法可靠闭环。两步制区分“材料齐全”和“有权决定”。

### ADR-V3-004：质量 Run 与 Test Case Execution 分域

**选择**：V2 `runs` 继续表达 task 的 implementation/unit/integration/review 门禁；V3 `lc_test_executions` 表达具体 Test Case 的执行。一个质量 Run 可引用多个 Test Execution Evidence，但两者状态不互相冒充。

**原因**：一次 `pytest` 可覆盖多条用例，一条系统用例也可能跨多个任务。强行合并会破坏重试、覆盖率和缺陷归因。

### ADR-V3-005：Skill 由真实宿主解释，Harness 只执行显式计划

**选择**：Skill 负责 Analyze→Plan→Dispatch→Verify 的行为约束；结构化 `work_order` 是模型与运行时的边界；本地 Harness 只以 argv 数组执行已落盘的测试计划。HTTP 不暴露执行接口。

**后果**：系统可以展示真实 Agent 交接，但不能宣称 Skill 文件本身会启动 Agent。宿主中断后，READY/CLAIMED work order、租约和最后心跳可恢复。

## 3. 组件和职责

```text
自然需求 / 现有仓库
        │
        ▼
platform-orchestration Skill ── 外部模型宿主 / Codex Agent
        │  work_order + typed output contract
        ▼
Runtime.execute (V2兼容门面)
  ├─ V2 TaskQualityService ─ runs / defects / events
  ├─ LifecycleService ────── stages / artifacts / trace / gates
  ├─ TestService ─────────── test model / cases / executions / defects
  ├─ ReleaseService ──────── manifest / deploy / rollback facts
  └─ QueryProjection ─────── board summary / explanation / pagination
        │
        ├─ SQLite：事务状态、关系、索引、事件
        ├─ Git workspace：版本正文、源码、脚本、报告
        └─ Trusted CLI runner：真实本地命令；无 HTTP 任意执行
```

Agent 仍按专业责任划分，而不是按每项活动无限增员：Orchestrator 是宿主责任；Requirement/Product/Architect/Developer/Tester/Reviewer/Documentation/Release 保持独立角色。性能、安全、黑盒、自动化和缺陷归因默认是 Tester/Reviewer 的 Skill 或工作流能力；只有任务规模或独立性要求达到阈值时才派独立 Agent。编译器、浏览器、扫描器、CI 和云系统是 Tool/MCP，不是 Agent。

## 4. 兼容 API 契约

现有 API 不删除、不改语义：

```python
Runtime(db_path).execute(command: str, data: dict, *, request_id: str | None = None) -> dict
Runtime(db_path).snapshot(project_id: str | None = None) -> dict
```

新增读取 API：

```python
Runtime(db_path).lifecycle_snapshot(
    project_id: str,
    *,
    after_sequence: int = 0,
    limit: int = 200,
) -> dict
```

`limit` 范围 1–500。返回：

```json
{
  "schema_version": "lifecycle-v1",
  "project_id": "project-...",
  "lifecycle": {"current_gate":"G3","state":"WAITING_HOST","progress":{"decided":3,"total":12}},
  "summary": {"artifacts":12,"trace_gaps":2,"tests":{"PASS":8,"FAIL":1},"open_defects":1},
  "work_orders": [], "artifacts": [], "trace_links": [], "test_models": [],
  "test_cases": [], "test_executions": [], "gate_evaluations": [], "releases": [],
  "events": [], "next_sequence": 481, "has_more": false
}
```

新增命令及最小 payload：

| Command | Payload | 关键后置条件 |
| --- | --- | --- |
| `lifecycle.initialize` | `{project_id, repository_root, mode:"active"}` | 同项目幂等创建 G0–G11；不改变 V2 `project.stage`。 |
| `lifecycle.control` | `{project_id, action:"pause|resume|rollback", reason, target_gate?}` | pause/resume 只控制生命周期调度；rollback 必须给出更早的 target_gate，保留历史决定并作废受影响评估。 |
| `work.create` | `{project_id, gate_id, activity, required_role, why, input_refs[], output_contract, dependencies[]}` | 生成 READY work order；依赖必须同项目。 |
| `work.claim` | `{work_order_id, agent_id, lease_seconds}` | 角色匹配、单一活动租约；返回完整 handoff 包。 |
| `work.heartbeat` | `{work_order_id, agent_id, lease_token}` | 延长租约；token 只以摘要持久化。 |
| `work.finish` | `{work_order_id, agent_id, lease_token, status, output_refs[], summary}` | 只接受当前租约；状态 `DONE|FAILED|WAITING_USER|BLOCKED`；引用须存在。 |
| `artifact.create` | `{project_id, artifact_type, artifact_id, title, state, content_ref, source}` | 新建 version=1；ID 前缀/类型/路径/摘要校验。 |
| `artifact.revise` | `{artifact_id, expected_version, state, content_ref, reason, change_id?}` | 乐观锁；新版本追加，旧版本不覆盖；影响分析后作废下游。 |
| `evidence.register` | `{project_id, evidence_id, kind, status, source, locator, sha256?, observed_at?, recorded_by, metadata}` | 只允许证据域状态；校验 locator/path 和摘要；记录事实但不推导批准。 |
| `trace.link` | `{project_id, from:{type,id,version?}, to:{type,id,version?}, relation}` | 校验端点、同项目、允许的关系和重复；产生可审计 link。 |
| `trace.invalidate` | `{link_id, reason, change_id}` | 保留历史，状态改为 INVALIDATED。 |
| `test_model.create` | `{project_id, artifact_id, requirement_refs[], function_tree, risks[], objects[], types[], test_points[]}` | 必须先有 requirement；风险和 test point 有稳定 ID。 |
| `test_case.create` | 见第 7 节 | 用例必须引用 test point 和 requirement；未定义自动化方法时状态 MANUAL。 |
| `test_execution.start` | `{case_id, case_version, environment_ref, executor_id, run_id?}` | 创建 ACTIVE execution；锁定 case 版本和环境。 |
| `test_execution.finish` | `{execution_id, result, actual_result, evidence_refs[], metrics?}` | `PASS|FAIL|BLOCKED|NOT_EXECUTED`；PASS/FAIL 必须有执行证据。FAIL 自动建 OPEN 缺陷。 |
| `defect.classify` | `{defect_id, category, severity, owner_role, rationale, evidence_refs[]}` | category 为 PRODUCT/TEST_SCRIPT/ENVIRONMENT/CONFIGURATION/REQUIREMENT/PERFORMANCE。 |
| `defect.resolve` | `{defect_id, fix_task_id, fix_evidence_refs[], regression_execution_refs[], resolved_by}` | fix task 已完成且影响回归均真实 PASS 才进入 RESOLVED；Developer 不能以自己的实现结果代替独立重测。 |
| `defect.close` | `{defect_id, review_evidence_refs[], closed_by}` | 仅 Reviewer/测试负责人身份、当前版本 review 证据有效时由 RESOLVED 进入 CLOSED。 |
| `gate.assess` | `{project_id, gate_id}` | 写不可变 assessment：candidate、checks、missing、policy_version；不写 Gate Status。 |
| `gate.decide` | `{assessment_id, status, decision_evidence_refs[], decided_by}` | assessment 未过期；PASS 必须满足策略；原子写 DECIDED 和事件。 |
| `release.create` | `{project_id, release_id, version, artifact_refs[], requirement_refs[], known_issue_refs[], rollback_ref}` | 创建 DRAFT 清单，引用均锁定版本。 |
| `release.ready` | `{release_id, assessment_id, decision_evidence_refs[]}` | 只在 G10 PASS 且无 blocker/critical 未接受风险时 READY。 |
| `release.record_deployment` | `{release_id, environment_ref, result, evidence_refs[], operator}` | 记录真实执行；不会因命令 exit 0 自动产生人工验收。 |
| `release.rollback` | `{release_id, reason, evidence_refs[], operator}` | 记录 ROLLED_BACK/ROLLBACK_FAILED；保留原发布事实。 |

所有变更命令支持 V2 同样的 `request_id` 幂等语义；同 request ID 不同载荷拒绝。HTTP 默认只允许读取以及原 V2 有限控制；V3 写命令先仅由可信 CLI/宿主调用。以后开放单项 HTTP 控制必须逐项威胁建模。

## 5. 数据模型与增量迁移

所有表均新增，不修改 V2 表列，时间使用 UTC ISO-8601，JSON 使用严格 `allow_nan=False`。实体表包含 `created_at`，版本表包含 `created_by` 和不可变摘要。

| 表 | 核心列 / 约束 |
| --- | --- |
| `lc_projects` | `project_id PK/FK projects`, `repository_root`, `mode`, `current_gate`, `state`, `policy_version`; state=`ACTIVE|PAUSED|WAITING_HOST|WAITING_USER|BLOCKED|FAILED|CLOSED`。 |
| `lc_gates` | `(project_id,gate_id) PK`, `ordinal 0..11`, `evaluation_state`, nullable `gate_status`, `current_assessment_id`, `decided_at`; gate_id 固定 G0–G11。 |
| `lc_work_orders` | `id PK`, project/gate/activity/role/why/input/output/dependencies/status/attempt/lease_digest/lease_until/agent/version；唯一活动 claim 索引。 |
| `lc_artifacts` | `id PK`, project/type/title/current_version/current_state；`UNIQUE(project_id,id)`。 |
| `lc_artifact_versions` | `(artifact_id,version) PK`, state/content_kind/path/inline_json/sha256/git_commit/source_json/created_by/created_at/superseded_by；正文二选一。 |
| `lc_trace_links` | `id PK`, project/from_type/from_id/from_version/to_type/to_id/to_version/relation/status/change_id；有效关系唯一索引。 |
| `lc_test_models` | `id PK`, project/artifact_id/version/model_json/status/created_at；模型结构见第 7 节。 |
| `lc_test_cases` | `id PK`, project/current_version/status；`lc_test_case_versions(case_id,version,...)` 追加保存结构化字段。 |
| `lc_test_executions` | `id PK`, project/case_id/case_version/environment_ref/executor_id/run_id/status/result/evidence_refs/actual/metrics/start/finish；每用例版本至多一个 ACTIVE。 |
| `lc_defects` | `id PK`, project/source_execution/category/severity/status/owner_role/requirement_refs/fix_task_id/regression_case_refs/version；与 V2 defects 分域但可 trace。 |
| `lc_gate_assessments` | `id PK`, project/gate/policy_version/input_digest/candidate/checks/missing/status/created_at`；不可变。 |
| `lc_gate_decisions` | `id PK`, assessment/project/gate/status/evidence_refs/decided_by/created_at；一个 assessment 至多一个 decision。 |
| `lc_evidence` | `id PK`, project/kind/status/source/locator/sha256/observed_at/recorded_at/recorded_by/metadata/supersedes_id；不可变。 |
| `lc_releases` | `id PK`, project/version/status/current_revision/created_at`; 版本表保存锁定清单和策略输入。 |
| `lc_events` | `sequence INTEGER PRIMARY KEY AUTOINCREMENT`, event_id UNIQUE/project/entity/type/data/occurred_at/recorded_at/actor；供增量看板。 |
| `lc_migrations` | `version PK`, `sha256`, `applied_at`；已应用脚本摘要不一致时拒绝启动。 |

主要索引：`lc_events(project_id,sequence)`、`lc_artifacts(project_id,type,current_state)`、`lc_trace_links(project_id,from_type,from_id,status)` 和反向索引、`lc_test_executions(project_id,case_id,finished_at)`、`lc_work_orders(project_id,status,gate_id)`、`lc_defects(project_id,status,severity)`。

初始化步骤：事务备份检查→执行只增表 migration 0002→写 migration 摘要→为指定项目创建 12 Gate→提交。任一步失败整体回滚。代码回滚到 V2 不删除表；数据回退由备份恢复，禁止在自动迁移中 DROP。

## 6. 工件、追踪和变更规则

允许的主链及 relation：

```text
BG/MR/PRD --refines--> REQ/NFR --realized_by--> DES
DES --planned_by--> TASK --implemented_by--> CODE_CHANGE
REQ/NFR --verified_by--> TEST_CASE --executed_by--> TEST_EXECUTION
TEST_EXECUTION --found--> BUG --fixed_by--> TASK
REQ/NFR | CODE_CHANGE | TEST_EXECUTION | BUG --included_in--> REL
任意实体 --evidenced_by--> EVIDENCE
任意受控实体 --documented_by--> ARTIFACT_VERSION
```

类型不允许的边拒绝写入。`COMPLETE` 是按当前有效版本和项目策略计算，不是调用者可任意填写的字段。最低 COMPLETE 条件：当前 requirement 至少有有效 design、task、code change、test case；当前 test case 有符合策略的最新 execution；相关未解决 blocker/critical 缺陷有明确处置；release 场景还需 included_in 关系。`NOT_APPLICABLE` 必须引用 rationale evidence，不能用来隐藏缺口。

`artifact.revise` 先计算影响集：从旧版本沿有效 trace 广度优先搜索，将下游 link 标为 `STALE`，相关 Gate assessment 标为 `SUPERSEDED`，关联 Test Case 标为 `REVIEW_REQUIRED`，已发布 Release 标为 `CHANGE_PENDING`。不相关分支保持有效。Material change 必须引用 `CR-xxx`；普通格式修订可记录 `reason` 而不创建 CR。

## 7. 测试模型、用例和缺陷闭环

`test_model.create` 的结构顺序是强约束：

```text
产品/版本理解 → 功能树 → 风险 → 测试对象 → 测试类型
→ 测试点 → 覆盖矩阵 → Test Case → Automation → Execution
```

每个 risk 包含 `risk_id, description, likelihood, impact, priority, requirement_refs`；每个 test point 包含 `point_id, object_id, type, rationale, risk_refs, requirement_refs, coverage_rule`。没有 test point 的 Test Case 拒绝创建。

`test_case.create` payload：

```json
{
  "project_id":"project-...", "case_id":"TC-001", "test_model_id":"TM-001",
  "test_point_refs":["TP-001"], "requirement_refs":["REQ-001"],
  "test_type":"FUNCTIONAL", "module":"auth", "priority":"P0", "risk":"HIGH",
  "preconditions":["service running"], "test_data":{"user":"fixture:valid-user"},
  "steps":[{"order":1,"action":"submit credentials","expected_observation":"request accepted"}],
  "expected_result":"authenticated session is returned",
  "automation":{"method":"CLI","tool":"pytest","entrypoint":"tests/test_auth.py::test_login","status":"AUTOMATED"},
  "state":"DRAFT"
}
```

`test_type` 支持 FUNCTIONAL/NEGATIVE/BOUNDARY/PERFORMANCE/STRESS/STABILITY/COMPATIBILITY/SECURITY/RECOVERY/DATA_CONSISTENCY。`automation.status` 为 AUTOMATED/MANUAL/NOT_FEASIBLE/PENDING；NOT_FEASIBLE 必须有理由。实际结果、PASS/FAIL 不保存在 Case 定义，只保存在 Execution。

FAIL 后原子创建 `BUG-xxx`，初始 category=`UNCLASSIFIED`、status=`OPEN`。Tester/Defect workflow 分类后分配 owner；PRODUCT 类建立 fix task，TEST_SCRIPT 修测试资产，ENVIRONMENT/CONFIGURATION 修环境，REQUIREMENT 进入 CR，PERFORMANCE 进入设计/容量任务。修复完成后由影响分析选择原失败用例、同 requirement 用例、相邻风险高的用例作为回归集合。只有独立重测 PASS 且回归集合均 PASS，缺陷可进入 RESOLVED；CLOSED 仍需 Reviewer 或测试负责人证据。禁止 Developer 自行关闭。

性能、压力和稳定性结果必须记录环境、样本量、持续时间、负载模型和原始结果 locator。未真正持续 8h/24h/48h/72h 时只能记录真实时长，不能按计划时长报告。

## 8. Gate 状态机与 Workflow

仓库 canonical G0–G11 不改为用户示例中的 G0–G8。若界面需要九阶段视图，只能显示映射：G0 Idea；G1 Research；G2 Product；G3 Requirements；G4 Design；G5 Planning；G6 Development；G7 Test；G8 Review；G9 Acceptance；G10 Release；G11 Close，不能合并后改变证据要求。

```text
NOT_EVALUATED ──gate.assess──> IN_REVIEW
IN_REVIEW ──missing evidence──> IN_REVIEW + work orders / WAITING_USER
IN_REVIEW ──gate.decide───────> DECIDED(PASS|FAIL|BLOCKED)
DECIDED ──material change─────> NOT_EVALUATED（旧决定保留为历史）
```

Gate PASS 后当前阶段推进一位；FAIL 生成修复/复评 work order；BLOCKED 必须指向阻塞原因和解除条件。项目 pause 只停止新 work claim，不改 Gate；resume 恢复调度。rollback 创建补偿 work order 并按受影响版本回退，不删除事件或已发布事实。

Orchestrator 每轮只执行一个确定性循环：读取增量快照→重收过期租约→计算可执行 work order→按依赖和角色并发分派→宿主执行→校验输出契约→注册工件/证据/追踪→独立测试/review→Gate assess→需要实质决策才 WAITING_USER。提问每批不超过 3 个，并包含建议、理由和影响；普通可逆选择使用记录过的默认值。

## 9. 多栈 Skill Self-Test 矩阵

Self-Test 不是五个静态示例目录存在即 PASS。每个案例必须由宿主明确记录 `skill=platform-orchestration`、输入 idea、实际 Agent/run/work order、生成 commit、执行命令、环境和独立 tester/reviewer。输出统一位于 `examples/multistack/<app>/`，应用目录固定为 `cpp_inventory`、`python_expenses`、`web_notes`、`java_booking`、`wechat_expenses`；每个案例有规格/测试模型文档、源码、自动测试、`README.md` 和 `manifest.json`，对应研发记录在 `docs/platform-v3/apps/<app>/`，汇总写 `docs/platform-v3/self-test-report.md`。

| Case | 最小应用 | 必需验证 | 外部工具与诚实边界 |
| --- | --- | --- | --- |
| `REQ-MATRIX-PY` | `python_expenses`：Python CSV 费用分析工具 | Python 3.11 CLI 读取 UTF-8 `date/category/amount`，Decimal 精确汇总；单元、CLI 黑盒、空输入/坏日期/负值/无穷数负向验证 | 仓库 Python 可执行，目标应完整 PASS。 |
| `REQ-MATRIX-CPP` | `cpp_inventory`：C++17 CLI 库存工具 | 增减、SKU 查询、列表、文件恢复、非负整数和缺货不写；实际编译、单元/CLI 黑盒 | 当前以 WSL `g++` 直接编译为可用路径，不强制 CMake；找不到编译器才记录工具 `NOT_AVAILABLE`、构建 `BLOCKED`。 |
| `REQ-MATRIX-WEB` | `web_notes`：HTML/CSS/JS 离线便签 | 新增/编辑/删除/搜索、localStorage、空白/长度/XSS 安全渲染；Node 业务单元和真实浏览器用户流 | Node/浏览器结果分别记录，不能用 Node 或 HTTP 200 代替浏览器结果。 |
| `REQ-MATRIX-JAVA` | `java_booking`：Java 8 会议室预约 CLI | 新增/取消/列表/文件恢复；区间重叠拒绝、相邻允许、错误输入不写；`javac` 编译和子进程黑盒 | 使用本机已安装 Java 8 语法/API，不提高到 Java 17；不得在线下载未审计工具。 |
| `REQ-MATRIX-WECHAT` | `wechat_expenses`：微信小程序本地记账本 | 原生 app.json/WXML/WXSS/Page，金额分类、列表、合计、删除、wx 存储恢复；JS 单元、结构静态检查 | wx 接口仅测试替身并明确标注；官方开发者工具、AppID或真机缺失时 native validation=`NOT_EXECUTED`，不得宣称发布成功。 |

每个案例必须经历：Idea/Discovery→DRAFT requirement→Design→Task→Developer implementation→独立 Unit/Integration或Black-box→独立 Review→报告。为了验证 Gate/Release 契约，可以生成材料并执行 `gate.assess`；除非具备真实批准、部署和验收证据，不把 G9–G11 标 PASS，也不发布这些教学样例。

矩阵汇总必须分别给出：generated、build、unit、integration/black-box、review、native/tool-specific、traceability、Gate assessment。总数只统计互不重复测试；缺工具不计 PASS。Self-Test 还必须包含一个故意失败案例以验证 BUG→Fix→Retest→Regression→Close，但最终报告保留首次 FAIL 证据。

## 10. 安全、可靠性、容量和隐私

- `repository_root` 在初始化时解析为绝对路径，所有 content path/cwd 经 `resolve()` 后必须仍位于根目录；拒绝 symlink/junction 越界和 `..`。
- 证据 metadata 经过敏感字段扫描；token/password/cookie/authorization/private_key 等只保存 `[REDACTED_SECRET]` 或外部 secret reference。原始执行输出沿用 V2 有界采集和脱敏。
- Test automation 仅由可信 CLI 读取仓库受控 manifest，命令是 argv 数组、`shell=False`；看板不可提交 argv。恶意生成代码仍需容器/VM 沙箱，V3 本机 runner 不是安全沙箱。
- work lease 使用随机 token，数据库只保存 SHA-256；过期后可重领，旧宿主结果以版本/lease 检查拒绝。外部进程须由宿主显式取消，状态失效不冒称已杀进程。
- SQLite 延续 V2 当前 journal 配置、busy timeout 和短事务，本轮不切换 WAL；是否改 journal mode 必须另做兼容、备份恢复和并发基准。文件正文先写临时文件并 fsync/原子 rename，再在事务中登记摘要。登记失败的孤儿临时文件可清理，绝不覆盖已登记版本。
- 大列表必须分页；看板默认取 summary 和最近 200 条事件。超过目标容量时提供 PostgreSQL Store 适配器，而不是在 SQLite 上引入分布式锁。
- 备份包含 SQLite 一致性备份、仓库 commit 和外部 evidence locator 清单。恢复后校验数据库 foreign key、migration digest、artifact sha256、Git commit 可达性。

## 11. 可观察性与看板投影

每个 work order 显示：Agent/role、activity、why、input refs、output contract、status、attempt、lease/heartbeat、blocker、dependencies、next owner。项目顶部显示 current Gate、Gate evaluation state、材料完成度、追踪缺口、测试计数、缺陷严重度和 Release 状态。

事件同时记录 `occurred_at`（来源声称发生时间）和 `recorded_at`（平台落库时间），来源不可信时 evidence status 只能 INFERRED/OBSERVED。看板的“下一步”由策略解释器输出 reason codes，例如 `MISSING_REQ_TEST_LINK`、`WAITING_HUMAN_APPROVAL`、`OPEN_BLOCKER_DEFECT`，而不是模型自由文本猜测。

健康指标：READY/CLAIMED work 数、租约过期数、各 Gate 等待时长、trace gap 数、用例执行/失败/阻塞数、缺陷平均修复时长、runner 超时/截断数。它们用于运营，不等价于质量或 Gate PASS。

## 12. 实施切片与验证顺序

1. `TASK-V3-001 Lifecycle`：只增表 migration 和 artifact/evidence/trace/test/defect/Gate/release/workflow API；先做旧 DB 升级与 V2 回归。内部实现切片可用 `TASK-V3-001-A`（artifact/trace）、`-B`（test/defect）、`-C`（Gate/release/workflow），但它们不是新的顶层 Task ID。
2. `TASK-V3-002 Stack harness`：实现 manifest v1、工具探测、占位符解析、路径限制、真实 argv 运行、源码摘要和分阶段报告。
3. `TASK-V3-003 Five applications`：在 `examples/multistack/` 生成并闭环验证五个应用；子记录使用 `TASK-V3-003-CPP|PY|WEB|JAVA|WECHAT`，均追踪回同一个顶层 Task。
4. `TASK-V3-004 Integration and skill`：接入 lifecycle CLI/看板、更新 `platform-orchestration` Skill、执行全回归、迁移恢复、浏览器检查和独立架构/代码 review；HTTP 保持无任意执行。

每个切片执行 Code→Unit→Integration→Review→Fix→Retest，不能等所有代码完成后统一测试。V2 的 189 项交付回归是升级基线，不自动成为 V3 结果；最终必须记录当前提交上的新鲜、可复现结果。

## 13. 当前事实与完成定义

本文件建立了可实施契约，尚未证明 V3 代码、五类应用、专有工具验证、部署或 G0–G11 项目 Gate 已完成。实现后只有同时满足以下条件才可称“V3 本地平台实现完成”：

- 新旧数据库迁移、并发、幂等、版本失效、路径和秘密负向测试通过；
- 工件/trace/test/Gate/release/workflow 的 API、CLI 和看板读取均有自动测试；
- 五类案例均实际通过其可用工具范围内的开发、独立测试和 review，缺失的专有工具明确 NOT_AVAILABLE/NOT_EXECUTED；
- 至少一个真实失败完成分类、修复、重测、回归并由独立 Reviewer 关闭；
- 原 V2 和治理校验无回归；独立 Review 无未解决 P0/P1；
- 最终报告将“平台模块完成”“样例验证”“真实部署”“人工验收”分开结论。
