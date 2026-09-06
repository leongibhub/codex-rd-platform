# TASK-V3-008 harness 实际实现记录

作者：真实宿主 `/root/v3_skill_forward`，本轮角色developer。实现记录不是独立验收。父协调者已在主Runtime记录本轮 implementation run；本文件不代其finish或签Gate。

## 已实现

- `scripts/validate_python_lifecycle.py` 提供 prepare/execute/finalize，调用公开Runtime facade；不使用直接SQL填充业务事实。
- prepare先读snapshot，复用run.json，登记实际developer、依赖工作、连续文档、现有Git来源、4条REQ/3条NFR、风险模型和37个单独版本化用例。BASELINED为本次固定输入，未写APPROVED或人类批准。
- execute要求不同于developer的实际tester，真实启动36个公开CLI用例与1个既有unit suite用例；每个执行都先start，再保存真实命令/输入摘要/输出/断言和EVD，再finish。已完成运行的resume只导出当前事实，不重复执行。
- finalize要求外部已经登记的真实review EVD ID清单，核对独立身份、范围、当前版本与G0–G8有效决定；不会创建reviewer、review、Gate决定或human_approval。
- 保留原应用`TASK-V3-003`与`6665bc5a5c4c441b523f9249dd860b7695daec72`的既有实现事实。`CODE-MATRIX-PYTHON-EXPENSES`表示实际Git基线；不声称本轮重新开发原应用。

## 实际准备与本地验证

真实prepare项目为 `project-337a2843b20e407981e60c2a28c605e4`，数据库 `.rd-platform/python-lifecycle/actual/state.db`。prepare命令实际退出0：37例全部NOT_EXECUTED，0 Gate决定，0 review/human approval。独立应用执行随后由父任务实际派发的Tester负责，当前结果见隔离报告和对应Tester记录。

首次harness契约命令 `.venv/Scripts/python.exe -B -X utf8 -m unittest tests.runtime.test_python_lifecycle_selftest -v` 实际7/7 PASS，13.559s；测试临时库中的角色清楚标为synthetic fixture，不是生产评审。测试涵盖逐需/资源分区、准备幂等恢复、不能自充tester、来源漂移拒绝、真实正负CLI输出、finalize缺外部证据拒绝及缺actor不污染恢复索引。

## BUG-PLC-PROV-001：报告生成者来源修正

自查发现通用artifact helper默认采用prepare作者，导致Tester生成的DOC-PLC-TEST-REPORT原版错误标记developer为created_by；test_execution与测试EVD的执行者本来正确。主责为本harness developer，不是费用应用缺陷，也不是用例失败。

修复：报告注册显式传当前实际tester；导出review_subject_refs从当前artifact版本读取，避免CODE修订后仍输出旧v1。新增报告作者来源契约测试实际PASS（1例，3.485s）。`CODE-PLC-HARNESS`已通过公开非业务变更revision升到v2，源码摘要 `78aea9fc1ba77ee061b8f36314f27dfb8dd4a44637562a2b7cb90f5ef06b93d7`。没有修改原应用或测试预期。

独立Tester保留已经完成的37次实际执行，负责对其报告DOC的来源作真实版本修正并登记引用新版本的EVD；不能通过回删原记录或虚构重跑来抹去原错误。其纠正与独立核验完成前，该来源问题保持待确认状态；本developer不代签其证据。

后续新增当前版本review-plan契约检查。最终完整命令 `.venv/Scripts/python.exe -B -X utf8 -m unittest tests.runtime.test_python_lifecycle_selftest -v` 实际9/9 PASS，22.415s。

本developer只读核对独立Tester已经导出的真实报告：37/37当前用例PASS，4条REQ与3条NFR的traceability均COMPLETE，`complete_snapshot=true`、`recommend_release=false`。这与自己运行的harness契约测试分开记录；不是由developer写入独立test_execution。

独立review和Gate决定仍由root派发的Reviewer完成。G9真实人工验收、生产部署、市场数据、性能SLA和长期稳定性不在该已执行证据中。

## 独立 Review P2：已持久报告的中断恢复窗口

真实独立Reviewer指出：应用执行和报告/EVD都已完成，但进程在work.finish或完成索引保存前中断时，恢复逻辑跳过已完成CLI却重新生成带新generated_at的报告，触发不可变文件冲突。根因是将“生成当前快照”和“恢复原始证据”混用。原失败由父协调者保留，TASK-V3-008已进入attempt 2；本developer不关闭该独立发现。

新增实际RED契约 `test_resume_after_report_before_work_finish_keeps_original_report`：临时库内先运行一次真实费用CLI并登记FINISHED执行、报告和EVD，再注入work.finish前崩溃。恢复时实际复现 `ValueError: immutable document already exists with different content`；命令退出1，1例ERROR，3.970s。角色为明确标识的合成契约fixture，不能作为正式项目的Tester/Gate证据。

修复后的恢复路径读取原始报告字节，验证project、当前case版本/Requirement绑定、完整execution记录、结果、环境/source摘要及已登记报告SHA-256；只允许生成时间、Gate快照和随后新增的集合计数等非执行绑定字段自然不同。已经完成work但run.json未落盘时，验证原work输出和结果后仅保存索引，不重新领取DONE work。恢复的输出引用包含原执行及原EVD，不生成重复应用运行。

不接受的冲突仍明确失败：报告内容变化、报告实际作者不一致、source漂移、case/execution版本或结果变化、完成work与报告不一致。不会覆盖报告、吞掉冲突或把旧PASS当成新版本结果。

完整契约命令 `.venv/Scripts/python.exe -B -X utf8 -m unittest tests.runtime.test_python_lifecycle_selftest -v` 实际13/13 PASS，44.741s。新增覆盖两个真实中断窗口、报告篡改拒绝、case升版后旧报告拒绝，且断言已完成CLI不会再次执行、原报告字节与执行记录完全保留。

`CODE-PLC-HARNESS`通过公开artifact.revise升至v3；当前代码SHA-256为 `7efce1164e3744f893feff046e9f5dfeb084a07a6840990bb01377b4c6826433`。此修复没有变更原应用、37条正式execution、用例定义或报告作者；真实库只读核对仍为37条FINISHED。独立QA与Reviewer需对v3做实际复测/复审，结果在其独立记录中登记。

## BUG-V3-008：旧报告与当前证据投影的兼容恢复

实际独立QA在attempt 2 integration记录FAIL：正式报告模块新增observed_result/freshness/freshness_reason纯派生字段后，原37条报告与当前case_results精确比较失败。没有业务执行数据变化，不能覆写旧报告或伪造重跑来处理。父协调者登记attempt 3 implementation run `run-8dde8c0953ab431a976018600819b2b3`，本developer只处理所拥有的harness、契约测试和说明。

新增两个真实RED契约：临时项目用旧投影实际生成报告并登记执行，恢复时复现同一ValueError；另一个在真实CLI执行结束后追加其EVD文件内容，旧实现竟未拒绝。专门命令执行2例，1 ERROR + 1 FAIL，7.946s，退出1。后者根因是原始lifecycle_snapshot保留历史结果但不验证当前路径证据；只忽略新字段会继续错误导出PASS。

修复仅兼容已知派生注释：缺省observed_result按旧result解释，仍精确比较observed_result、effective result、case/执行身份与版本、需求和EVD引用；freshness/reason只有无失效信息时可规范化，未知字段仍参加比较。每次恢复另外调用正式 `lifecycle_report_from_runtime`，要求PASS/FAIL的执行投影为CURRENT并核验当前结果/结论与原始绑定一致；STALE、EVD摘要失配或当前nonPASS不能沿用旧PASS。可更新JSON导出也改用该正式当前投影。不可变Markdown继续表示执行时原始报告，缺字段或NOT_CHECKED不代表当前验证状态。

专门GREEN：2/2 PASS，10.487s。最终完整命令 `.venv/Scripts/python.exe -B -X utf8 -m unittest tests.runtime.test_python_lifecycle_selftest -v` 实际16/16 PASS，57.488s。新增覆盖旧schema恢复、真实EVD路径摘要失配拒绝、结果/版本/Requirement/EVD绑定不得被兼容规则忽略；既有两个崩溃窗口、篡改报告和新case版本拒绝继续通过。所有契约身份仅为临时库fixture，不构成正式独立验收。

公开artifact.revise在 `2026-09-06T10:55:55.792525+00:00` 将 `CODE-PLC-HARNESS` 升到v4，SHA-256 `74e7e8e45eff52ec959dbb5924da39501bb1f717fe76f7067a7c290934753f8a`。本developer只读调用实际项目的报告绑定校验返回37 PASS，未调用其execute、未登记tester或测试结果。升版前后37条execution内容相等，应用source摘要相等；原 `test-report.md` SHA-256为 `3e7335ef45355cf1408319f59b4b66c640f85f54f66100f2ee5a9389c87e243d`，未改写。独立unit/integration/review及缺陷结论由父协调者和实际质量责任人继续，旧FAIL不删除。
