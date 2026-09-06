# V3 实施追踪与证据索引

变更 `CR-V3-001`；设计 `DES-V3-001`；基线提交 `9655f33`。
这是 V3 工程升级的范围化索引，不填充模板中央 RTM、不建立项目 Gate 决定。最终代码版本由包含本文件的 Git 提交固定；实际发布/验收链仍为 `PARTIAL`。

## 需求 → 实施任务 → 代码 → 测试 → 审查

所有需求定义见[设计基线](../superpowers/specs/2026-09-06-platform-v3-design.md)。任务编号沿用[实施计划](../superpowers/plans/2026-09-06-platform-v3.md)，补充查询/模型工作是同一任务范围的有记录拆分，不重新编号历史记录。

| Requirement | Task | 主要代码 | 可重放测试与证据 | 当前边界 |
| --- | --- | --- | --- | --- |
| REQ-V3-001 | TASK-V3-001 | `rd_platform/lifecycle.py`, `lifecycle_store.py`, `lifecycle_work.py` | `tests/runtime/test_lifecycle.py` 初始化、work/lease/pause；独立 TC-V3-IND-304 | 生命周期实例真实存在，五项目未决定 Gate |
| REQ-V3-002 | TASK-V3-001/004 | `lifecycle_base.py`, `lifecycle_models.py` | `test_lifecycle_models.py`；独立 TC-V3-IND-501/503；五模型 v2 adoption | 原始 legacy v1 来源 NOT_AVAILABLE；不补写作者 |
| REQ-V3-003 | TASK-V3-001 | `lifecycle_base.py`, `lifecycle_reporting.py` | typed links、影响失效测试；独立 TC-V3-IND-301；真实 REQ/CODE→case/execution | suite-level 聚合追踪，不等于每个子需求完整覆盖 |
| REQ-V3-004 | TASK-V3-001 | `lifecycle_governance.py` | Gate freshness/negative tests；独立 TC-V3-IND-303/306 | 缺认证 approval provider 默认拒绝；无真人 Gate PASS |
| REQ-V3-005 | TASK-V3-001/003 | `lifecycle_models.py`, `lifecycle_testing.py`；五应用风险模型 | `test_case_model_and_execution_requirements`；独立 TC-V3-IND-501/502；live v2 记录 | 每个项目仍须自己的风险模型和验收范围 |
| REQ-V3-006 | TASK-V3-001 | `lifecycle_testing.py` | `test_failure_fix_retest_regression_independent_close`；独立 TC-V3-IND-302/307；真实模块 FAIL→Fix→Retest→Review | synthetic fixture 的缺陷/审批不冒充真实项目事实 |
| REQ-V3-007 | TASK-V3-001/004 | `lifecycle_governance.py`, `lifecycle_reporting.py` | synthetic full Gate/release/rollback contract；报告 adverse-release tests | 没有真实生产部署、回滚、G10 或验收 |
| REQ-V3-008 | TASK-V3-004 | `cli.py`, `web.py`, `static/`, `lifecycle_query.py` | adapter tests；独立 TC-V3-IND-401..403；浏览器阅读 RED/GREEN | 看板反映持久化事实；宿主负责启动实际 Agent |
| REQ-V3-009 | TASK-V3-001/004 | `lifecycle_work.py`, `lifecycle_base.py`, `lifecycle_models.py` | pause/lease/idempotency/rollback tests；独立 TC-V3-IND-301/304/502 | pause 不杀外部进程；回滚不重写历史 |
| REQ-V3-010 | TASK-V3-002/003/004 | `stack_harness.py`；`examples/multistack/`；Skill | 五应用单测+独立黑盒+review；Skill-forward 9 current PASS 及 GREEN | 微信仅 Node domain/fake-wx，原生 NOT_AVAILABLE |
| NFR-V3-001 | TASK-V3-001/004 | `store.py`, `lifecycle_store.py` | 原平台 98、旧样例 19、V2兼容 Runtime 回归 | 新表保留，未执行破坏性回退 |
| NFR-V3-002 | TASK-V3-001/004/005 | `lifecycle_store.py`, `lifecycle_query.py`, `scripts/benchmark_lifecycle.py` | 501 records 分页；实际 100项目/10万版本/100万事件，129.7199秒/294764544字节/0读取错误；独立预算/中断测试 | 合成只读容量已测；8小时读路径 soak RUNNING，非完整系统稳定性 |
| NFR-V3-003 | TASK-V3-001 | `runtime.py`, `lifecycle_work.py` | 事务/幂等、租约过期与响应丢失旋转 tests | 非长时故障稳定性基准 |
| NFR-V3-004 | TASK-V3-001/002/004 | `web.py`, `stack_harness.py`, `lifecycle_base.py` | 路径/secret/argv/HTTP tests；独立 TC-V3-IND-201..212/305/308 | Windows symlink fixture NOT_EXECUTED；Harness不是恶意代码沙箱 |
| NFR-V3-005 | TASK-V3-001/004 | `lifecycle_governance.py`, `lifecycle_models.py`, `lifecycle_query.py` | 不可变版本/证据/历史FAIL/旧模型adopt；独立 runtime review | Git 与 Runtime 是相互链接的记录；禁止以日志充当人工签名 |

## 真实任务和独立性

CR-V3-002 新增 TASK-V3-005..010 的当前任务、失败重试和交付证据见 [completion-delivery.md](completion-delivery.md) 与 [completion-qa.md](completion-qa.md)。真实 CI 又产生 TASK-V3-011..014 / BUG-CI-001..004，修复、独立角色和在线结果见 [ci-execution.md](ci-execution.md)。README 执行审查还产生 TASK009 revision 2 与 TASK-V3-015 / BUG-INSTALL-001..002；真实安装首次失败与修复后正常 setup 通过见 [install-real-validation.md](install-real-validation.md)，当前独立审查见 [install-transfer-review.md](install-transfer-review.md)。模块状态不能推导项目验收或 8h PASS。以下 5 个任务是上轮基线记录，不是新任务的总计。

平台项目 `project-908e903738184820b14264adac92adda` 的 5 个任务在最终读取时均为 DONE、当前 4/4 质量检查通过：

| 子模块 | Runtime task ID | 实施 | 独立测试 | 独立审查 |
| --- | --- | --- | --- | --- |
| Lifecycle | task-e39fdf1276024f338c00c196b764a56c | /root/v3_lifecycle | /root/v3_qa_platform | /root/v3_review_runtime |
| Harness | task-ee636acafdb649eea24dc4a22ddcba5f | /root/v3_harness | /root/v3_qa_platform | /root/v3_review_runtime |
| CLI/Board/Report/Skill | task-5ae84d62357e4887ac35eb7877f3bc9e | /root | /root/v3_qa_apps | /root/v3_review_runtime |
| Collection query | task-f8748fc6225b4e4e87106f29e939dd55 | /root/v3_query | /root/v3_qa_platform | /root/v3_review_runtime |
| Test model versions | task-3719174d1366496eb8f76c16aa312abf | /root/v3_models | /root/v3_qa_platform | /root/v3_review_runtime |

五应用的开发角色分别为 /root/v3_cpp、/root/v3_python、/root/v3_web、/root/v3_java、/root/v3_wechat；独立测试 /root/v3_qa_apps，独立审查 /root/v3_review_apps。真实任务/run ID、发现和修复见下面的记录；没有把多个假名当作独立执行。

## 证据、缺陷和发布链

- [独立平台测试](independent-platform-tests.md)：TC-V3-IND-201..212/301..308/401..403/501..503，保留产品缺陷与测试 fixture 问题的不同归因。
- [独立平台审查](runtime-review.md)：4 P1、6 P2 的发现、修复及复验，最终 scoped APPROVED。
- [独立应用测试](independent-app-tests.md)和[应用审查](app-review.md)：首次 FAIL 不删除，当前范围复测/复审通过。
- [真实生命周期验证](live-lifecycle-validation.md)：五项目 case v1 历史与 case v2 新 execution ID、environment/execution evidence；当前报告 PASS，但 recommend_release=false。
- [浏览器验证](browser-validation.md)：实际 Web 用户流和看板行为，不用 Node 冒充浏览器。
- [Skill 实战](skill-forward-validation.md)：已有应用未被重建，verification-only 路由的实测修正。
- [逐需求 Python 实战](python-lifecycle/README.md)：既有 Python 工具的 4 REQ/3 NFR、37 个真实 CURRENT/PASS Case、7/7 COMPLETE RTM 和独立 G0–G8 PASS；其他四个应用不继承此完整度，G9–G11 仍未决定。
- [跨平台 CI 与缺陷闭环](ci-execution.md)：源码提交 `a55e3ce` → `ba17e35` → `62c153e`，实际 Windows/Linux 作业及失败历史，不把本机结果复制为在线证据。
- [能力状态](capability-status.md)与[发布边界](release-readiness.md)：未执行项、未来 REL、真实部署和人工验收明确保留。

代码变更与以上结果由 Git 提交绑定；Git push 只是源码交付，不创建 REL、不构成 G10/G11 或生产发布。
