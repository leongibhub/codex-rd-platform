# CR-V3-003 / CR-V3-004 执行端交付记录

本记录从 `5800aae` 延续既有项目，未重建五个应用、清空状态库或重写历史 Gate。当前属于执行端实现/独立验证交付，不代表用户已验收全部最终愿景。

## 实现与追踪

| 需求 / 任务 | 实现 | 验证入口 |
| --- | --- | --- |
| REQ-V3-016 / TASK-V3-016 | 真实持久化 worker、租约、并发、分页队列、取消、无工具模型提案、显式源码上下文、CAS 修改、事务失败与崩溃恢复 | `test_worker_service`、`test_proposal_backend`、`test_proposal_files`、`test_proposal_admission`、独立端点测试 |
| REQ-V3-017 / TASK-V3-017 | SSH 公钥身份、绑定版本/策略的挑战、外部签名与防重放审批 CLI | `test_approval_provider`、独立真实临时 SSH CLI 测试 |
| REQ-V3-018 / TASK-V3-018 | 显式部署/健康/回滚清单、来源摘要、幂等操作身份、正式发布前置检查及真实回执 | `test_deployment`、独立本机 HTTP 部署/失败/补偿测试 |
| REQ-V3-019 / TASK-V3-019 | Linux 原生安装、copied venv、安全重复安装、配置生成与 MCP health | `test_linux_setup`、真实 Ubuntu CI 安装步骤 |
| REQ-V3-020 / TASK-V3-020 | 粗略想法启动、12 阶段工作计划、真实 Agent/work 看板、控制入口、Skill、中英文 README | `test_orchestration`、`test_execution_board`、`test_web`、独立 CLI/HTTP 测试 |

设计依据为 [DES-V3-003](completion-execution-design.md) 及 [CR-V3-004](CR-V3-004-safe-model-execution.md)。用法见 [执行指南](completion-execution-guide.md)、[中文 README](../../README.md) 和 [English README](../../README.en.md)。完整 Gate 的 source of truth 仍是对应活动项目；顶层仓库保持 template。

## 实际验证记录

- Linux 安装提交 `9f12b930fe7bc7302c51d8a10b7fea22e3d64f19` 已推送。GitHub run `34036999184` 的 Ubuntu job `101496781967` 实际安装及重复安装步骤成功；整体 run 的 Windows job 失败原因是 fixture 将 `wsl.exe` 存在误当作已安装 Linux 发行版。修复后探测必须真正启动 Bash，缺失发行版明确跳过而非冒充通过。
- 本机 platform 全套：133 tests，162.296 秒，OK。
- Runtime 中途完整回归：271 tests，144.007 秒，OK，2 skips；后续恢复边界新增测试后的最终提交由新的 CI/下方补录覆盖，不能将这组数字借用于未测版本。
- 最后定向 worker/提案/文件恢复/准入四模块：46 tests，6.990 秒，OK。包含被 unittest 收集的继承用例，不宣称 46 个互不重复业务场景。
- 既有多栈独立 Python suite：13 tests，14.598 秒，OK；Web/微信 Node 独立 suite：6 tests，144.5888 毫秒，PASS。C++/Java/Python/Web/微信源码未重新生成。
- `validate_platform.py`：PASS (TEMPLATE MODE)，Runtime check EXECUTED，Evaluated Gates NONE。
- Skill `quick_validate.py`：Skill is valid。
- 真实 Codex 实验产物：开发测试 9/9、独立公开 CLI 黑盒 4/4；其原始工作单仍为 FAIL（工件类型不合规），且该执行路径已因隔离失败禁用。这不是安全 Responses API 成功证据。
- 安全 Responses live smoke 已实际调用前置检查，输出 NOT_AVAILABLE / real_api_executed=false：本机没有该 API 凭据，未发请求、未产生费用声明或虚构模型结果。

失败与修复详见 [独立测试记录](completion-independent-tests.md) 和 [独立审查记录](completion-independent-review.md)。QA 的一次恢复 fixture 类型错误也保留为原始 FAIL，而不是删除记录后声称首轮通过。

## 仍需真实外部事实，而不是生成记录

1. 无工具 API 后端的真实账号端到端验证需要配置受权凭据；目前有传输契约、源码准入及恢复 fixture 证据，没有远端 API PASS。
2. 微信 IDE/真机、正式部署目标、真正的人工签名验收不能由 Node stub 或临时密钥代替。接口已经实现，不代表这些外部事件发生过。
3. 原有同一次 8 小时公开读路径 soak 保持运行，由既有监控等待终态。未到时长不能宣称通过，也不将公开读压力等同完整应用长稳。
4. `orchestrate-start` 创建依赖工作计划，不自动把模型文档升成基线/测试/审批。可信宿主按 Skill 执行、独立验证并通过真实证据推进 Gate；这些控制不能为了“全自动完成”而旁路。

所有可执行工具只对明确受权的项目和目标工作。远端请求取消结果可能未知；不承诺本地暂停就已停止远端计费。日志恢复冲突保留文件与诊断，须由宿主核对后恢复，不能自动覆盖外部修改。
