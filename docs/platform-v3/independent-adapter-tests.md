# V3 CLI、HTTP 与生命周期报告独立测试

执行者：/root/v3_qa_apps（Tester）。范围：TASK-V3-004 适配层，关联 REQ-V3-003、REQ-V3-004、REQ-V3-007、REQ-V3-008、REQ-V3-010 与 NFR-V3-004。测试模型在实现质量阶段开始前，依据 DES-V3-001 的只读 HTTP、分页、报告和可信 CLI 边界建立；不以开发者测试作为预期来源。

## 风险驱动用例

| 用例 | 类型/风险 | 输入和可观察预期 | 状态 |
| --- | --- | --- | --- |
| TC-IQA-ADAPTER-001 | HTTP 功能/兼容 | 初始化合成 lifecycle 项目后 GET /api/lifecycle?project_id=...；200 JSON，返回项目、schema 和分页字段。 | PASS，EVD-IQA-ADAPTER-002 |
| TC-IQA-ADAPTER-002 | HTTP 边界/输入校验 | 缺 project_id、重复 query、非整数 after/limit、after<0、limit=0/501。 | PASS，EVD-IQA-ADAPTER-002 |
| TC-IQA-ADAPTER-003 | HTTP 安全 | POST /api/commands 提交 lifecycle.initialize；HTTP 拒绝，生命周期项目未被该请求创建。 | PASS，EVD-IQA-ADAPTER-002 |
| TC-IQA-ADAPTER-004 | CLI 可靠性/无副作用 | 对不存在的 --db 执行 stack-probe；标准输出为 JSON，退出码 0，DB 不创建。 | PASS，EVD-IQA-ADAPTER-002 |
| TC-IQA-ADAPTER-005 | CLI 负向 | 对不存在项目执行 lifecycle；非零且 stderr 无 traceback/argument-parser invalid choice。 | PASS，EVD-IQA-ADAPTER-002 |
| TC-IQA-ADAPTER-006 | 报告正确性/空数据 | 无 Test Case/Execution。 | PASS，EVD-IQA-ADAPTER-002 |
| TC-IQA-ADAPTER-007 | 报告数据一致性 | 旧版本 PASS、当前版本 FAIL，或只有旧执行。 | PASS，EVD-IQA-ADAPTER-002 |
| TC-IQA-ADAPTER-008 | 报告分页与发布安全 | 集合截断、缺当前 case、DEPLOYMENT_FAILED/CHANGE_PENDING/ROLLED_BACK release。 | PASS，EVD-IQA-ADAPTER-002 |

## 执行记录

主控 Runtime 任务：task-5ae84d62357e4887ac35eb7877f3bc9e。

| Evidence | Runtime run / command | Observable result |
| --- | --- | --- |
| EVD-IQA-ADAPTER-001 | unit run run-4c13a30260b0402e889d6e9cc710b90f; .venv/Scripts/python.exe -X utf8 -m unittest tests.runtime.test_v3_adapters tests.runtime.test_lifecycle_reporting -v | exit 0; 8/8 developer adapter/report tests passed. |
| EVD-IQA-ADAPTER-002 | integration run run-f96512f626634da5842fb950096a57fd; .venv/Scripts/python.exe -X utf8 -m unittest tests.independent_multistack.test_v3_adapter_blackbox -v | exit 0; 4/4 independent tests passed. HTTP used a temporary DB and a loopback ephemeral port; CLI used temporary absent DB paths; reporting used in-memory synthetic snapshots. |

No defects were observed in this independent execution. This result covers the listed local adapter contracts only; it is not a Gate, deployment, release recommendation, human acceptance, production HTTP security assessment, browser result, or capacity benchmark. 主控单独记录的浏览器操作不作为本测试报告的 PASS。
