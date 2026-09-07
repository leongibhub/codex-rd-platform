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

## 2026-09-07 当前 CI 与复审增补（保留上方历史）

- 提交 `026263f` 的 [GitHub Actions run 34038680898](https://github.com/leongibhub/codex-rd-platform/actions/runs/34038680898) 当前为 3/4 jobs SUCCESS：Windows Runtime 273 PASS、1 skip；Windows platform 133 PASS、3 skips；独立 job 实际为 98 tests、1 error（不能写成 98 PASS 再加 1 FAIL）。该独立失败是 Windows 存在 `wsl.exe` 却没有可启动 Linux distribution，不得把环境缺口改写为产品成功。
- WSL readiness 修复后的本机端点 suite 为 30 PASS、24.700 秒；当前 root full suite 为 99 PASS、1 skip、114.547 秒。两项都是当前本机 QA 观察，不能代替新的 hosted CI；新 CI 仍 `PENDING`。
- 历史 reviewer P1 为 worker fast pause→resume 重复执行风险和未受宿主严格条件约束的 stage claim。它们已在 TASK-V3-016 r9 / TASK-V3-021 r7 得到独立复测与 review；TASK-V3-020 r3 attempt 2 的复审也已通过，当前 module review scope 为 P0=0、P1=0。该模块级结论不外推为真实批准、生产执行或全局完成；TASK-V3-020 r3 首个 review 的 TC912 证据/记录失败仍保留为历史。
- 历史 full-runtime `294` tests run reported one Windows `WinError 32` during `DeploymentExecutorTests.test_real_isolated_deploy_and_independent_http_health_succeed` teardown: the temporary `app` cwd was still locked while the fixture cleaned up. No deployment assertion failed. The fixture now observes its owned HTTP child exit and releases its completed `Popen` owner before `TemporaryDirectory.cleanup()`. A later reproducible split rerun (needed because the local command-output window is 30 seconds) observed 10/10 with 1 host symlink-privilege skip in 6.363 s, then 10/10 in 29.117 s: 19 PASS, 1 skip, with no `WinError 32`. This is fixture-lifecycle evidence, not a production executor leak conclusion; a fresh full CI run remains required.

## 2026-09-07 冻结前 Runtime 快照与回归增补（不作最终结论）

对当前 Runtime 快照的只读核对显示以下任务状态；`DONE` 仅是该 Runtime
任务的已登记质量链状态，绝不等于项目 Gate、真实部署、人工批准或验收。

| 任务 / 追踪 | 当前 Runtime 状态 | 仍需完成的事实 |
| --- | --- | --- |
| `TASK-V3-016` / `REQ-V3-016` | revision 9、`DONE`、4/4 checks；r8 已由 r9 取代。canonical fence 覆盖 unknown external-outcome invalidation/control 与 rollback，并将 adopted dependency resolution 延后到 atomic claim；post-claim context 使用持久 adopted refs 的有界脱敏生命周期记录。developer run `run-02c7d4559e71482a83e04c4ec278a7f3` 为 64 个 tests PASS；独立 unit `run-901b8eb923704979bb35775a5fe7cd9c` 为 64/64 PASS、26.886856 s，独立 integration `run-a918a474aa18436887ac526af9a180ff` 为 22/22 PASS、19.173931 s（新增 TC939）；review `run-95e3f86d8cdd4bbc9758b395059355ff` 已登记。 | `DONE` 是当前 Runtime 的模块质量链；该 review 仅限当前源码/隔离 fixture。新 CI 仍 `PENDING`；它不是端点总体、项目 Gate、外部执行或验收结论。 |
| `TASK-V3-018` / `REQ-V3-018` | revision 4、`DONE`、4/4 checks；正式 Runtime 记录原子性仍只在隔离 fixture/本机源码范围有证据。 | 不存在真实目标部署、回滚、G10 或 release acceptance。 |
| `TASK-V3-020` / `REQ-V3-020` | revision 3、`DONE`、4/4 checks。首个 review `run-3dffaf1ab6c2462dbda92e7b08cf33b2` 因 TC912 将未执行的五栈回归写为 PASS、且与末行 `NOT_EXECUTED` 矛盾而 `FAIL`，历史保留且没有观察到产品源码回归。attempt 2 unit `run-7ecc1fb37c4a415aabcd37872ceb305b` 为 33/33 PASS、15.482481 s；integration `run-2f1239aa6e794fe5ae01e6539c89fb7c` 为 15 条实际命令 PASS、31.697916 s（不是 15 个测试用例），覆盖 C++ WSL build/unit/integration、Python build/unit、Web unit、Java 8 build/unit/integration、微信 unit/integration；另有独立五栈 13/13、Web Node 3/3、微信 fake-`wx` Node 3/3 与 CLI/fixture 4/4。TC912 已据此更正；attempt 2 review `run-192ea18554814c1a8155e6a206da993a` 为 PASS。 | `DONE` 仅是当前 Runtime 的模块质量链。微信 fake-`wx` 不构成原生微信证据；初次错误 package 命令 `Ran 0` 不计 PASS，fixture RED→GREEN 未改变产品 validator Gate。hosted CI、live Responses、真实人类批准、生产部署/回滚、客户验收与顶层 Gate 仍分别未由此产生 PASS。 |
| [`CR-V3-005`](CR-V3-005-host-stage-policy.md) → `TASK-V3-021` / `REQ-V3-021` | revision 7、`DONE`、4/4 checks；r4–r6 已被 r7 取代。r7 解决 TC semantic adoption drift、repair 输出 exact refs、及内置 Gate FAIL/rollback recovery dependency binding。独立 QA unit 7/7、integration 18/18，reviewer 17/17；review `run-3e3576b548ca4dea91dbbc52e813c693`。详见[host policy](orchestration-policy.md)。 | 当前 policy review scope 的 P0=0/P1=0；该模块级结论只适用于当前源码与隔离 Runtime/local-file fixture，不构成真实 Gate、批准或生产执行。 |
| `TASK-V3-022` / `REQ-V3-008,021` | revision 1、`DONE`、4/4 checks；[只读状态面](orchestration-status.md)只解释阶段与前提，固定不授权执行。 | 不创建/推进 Gate，且不替代 TASK-021 的 policy QA 或人工验收。 |

冻结前的实际回归历史必须保留，且不能挑选旧绿结果作最终版本结论：platform
suite 曾为 133 PASS、217.852 seconds；稍早 full runtime 为 288 PASS、177.502
seconds、2 skips，发生在最终 freeze 之前。后续 full runtime 为 294 tests、1 FAIL，
原因是 QA fixture teardown 的 Windows `WinError 32`，其 cleanup 修复不让该旧
run 变成 PASS。full independent 实际为 109 tests、1 error、1 skip（成功 107），而非
“109 PASS + 1 FAIL”；`TC304` 旧 fixture 将非 safe retry 当作可继续路径，现已改成明确的
negative 断言，并以显式临时 `safe_to_retry`
场景覆盖允许路径。在该历史记录时，修正后的最终冻结回归结果与新的 hosted CI 都仍 `PENDING`；
后续本机冻结结果见下表，hosted CI 仍待实际输出。

其后实际 full runtime 为 303 tests、OK、2 skips、254.998 s；该 run 开始时
`TASK-V3-021` 仍在 r4，因此不是随后 r5/r6 的完成证据。full platform 则为 133 tests、
210.172 s、`FAILED (errors=2)`，原因是上述 QA fixture copytree 漏排 `.rd-platform`，
复制时并行 Runtime 正删除临时目录而出现 `WinError 3`。首个新增回归 test 还曾因
contextmanager wrapper 的 globals 错误失败；已改为被装饰函数 `__wrapped__` 的 globals，不是产品缺陷，
原始工具/fixture失败历史保留。TC304 与 deployment fixture cleanup 后续复测的 deployment
split 为 19 PASS、1 host-permission skip，未再出现 `WinError 32`；这不回写旧 294-test
失败。随后 current fixture 的 full platform 为 134 tests、178.309 s、OK，定向 validator
contract 为 28 tests、28.178 s、OK；其新增 RED→GREEN 仅证明 `.rd-platform` 不被 fixture
复制，并未改动产品 validator Gate。当前各域冻结结果见下表；hosted CI 仍 `PENDING`。

## 当前冻结验证表（范围化，不作 Gate）

| 验证 | 可观察结果 | 解释边界 |
| --- | --- | --- |
| Full Runtime | `OBSERVED`：307 tests、236.304 s、exit 0、2 skips。 | 当前冻结源码的本机 Runtime 回归；不替代外部 API、批准、部署或验收。 |
| Full platform | `OBSERVED`：QA 当前 134 tests、179.961 s、OK（先前同一已修 fixture run 为 178.309 s）。 | 包含 fixture live-state exclusion 回归；不是产品 validator Gate 决定。 |
| Full independent | `OBSERVED`：当前 113 tests、135.173 s、OK、1 skip，包含新增 TC940。 | 旧 112 tests/148.845 s/OK/1 skip 是 TC940 新增前的冻结后历史快照；旧 146.471 s 也是前一轮，均不借作当前结果。此本机独立全量结果不替代 hosted CI 或任何外部事实。 |
| 五应用与工具 | `OBSERVED`：独立 Python 13/13、Node 6/6、`python -X utf8` Skill quick validation、JS syntax 和 diff check 均 PASS。 | 局部应用/工具回归，不替代执行端 reviewer 或外部事实。 |

当前 V3 模块质量链为 `OBSERVED`：TASK-V3-016 r9、TASK-V3-018 r4、TASK-V3-020 r3、
TASK-V3-021 r7 和 TASK-V3-022 r1 均已在 Runtime 登记 `DONE`；TASK-V3-020 的首审失败保留，attempt 2 review 已通过。顶层 template Gate、live Responses、真实人类批准、生产部署/回滚、客户验收与新 hosted CI 均未因此产生 PASS。

当前冻结源码 checkpoint 为提交 `fbd9b36d5ad429bd3528328c1ec6a06b49cc990b`（45 个变更文件）。该提交早于本页对 TASK-V3-020 attempt 2 完成及 review 结果的后续文档补录；它如实固化当时的源码状态，并不改写 Git 中的历史提交事实。无论 checkpoint 或后续模块质量链，都不是全量完成标记，也不替代 hosted CI 或任何外部事实。

本轮对既有五应用的范围化重跑也已观察到：独立 Python suite 13 tests、12.839 s、OK；
显式 Node 两文件 6/6 PASS、141.7366 ms；以 `python -X utf8` 执行 Skill
`quick_validate.py` 为 PASS，JS syntax 与 diff check 成功。此前不带 UTF-8 的 GBK
错误保留为工具/编码历史，不被这次正确编码调用抹除。这些是既有应用与 Skill 的局部
回归证据，不替代 final-freeze 端点 QA、hosted CI、Gate 或外部验收。

## 仍需真实外部事实，而不是生成记录

1. 无工具 API 后端的真实账号端到端验证需要配置受权凭据；目前有传输契约、源码准入及恢复 fixture 证据，没有远端 API PASS。
2. 微信 IDE/真机、正式部署目标、真正的人工签名验收不能由 Node stub 或临时密钥代替。接口已经实现，不代表这些外部事件发生过。
3. 原有同一次 8 小时公开读路径 soak 已完成并核对 4,952 次采样、最大间隔 8.191594 秒及零读错误；监控已暂停。范围仅为合成 SQLite 公开读路径，不是完整应用长稳或内存无泄漏结论，详见 [长稳记录](performance-validation.md)。
4. `orchestrate-start` 创建依赖工作计划，不自动把模型文档升成基线/测试/审批。可信宿主按 Skill 执行、独立验证并通过真实证据推进 Gate；这些控制不能为了“全自动完成”而旁路。

所有可执行工具只对明确受权的项目和目标工作。远端请求取消结果可能未知；不承诺本地暂停就已停止远端计费。日志恢复冲突保留文件与诊断，须由宿主核对后恢复，不能自动覆盖外部修改。

## 最终 hosted CI 与交付补录

冻结源码 `fbd9b36d5ad429bd3528328c1ec6a06b49cc990b` 已推送至 `origin/codex/platform-v3-lifecycle`，其 [run 34095997725](https://github.com/leongibhub/codex-rd-platform/actions/runs/34095997725) 于 `2026-09-07T07:48:30Z` 完成 SUCCESS。Windows/Ubuntu 的 Runtime-platform 与五应用 manifest 共 4/4 作业成功，Ubuntu 原生安装与重复安装步骤成功；具体作业 ID 和真实 API 观察见 [CI 执行记录](ci-execution.md)。这覆盖本页此前“新 CI PENDING”的快照，不删除历史失败。

本轮 Runtime 看板的 23 个工程任务均为 DONE，独立终审在当前源码范围无未解决 P0/P1；TASK-V3-020 首审 FAIL 与 attempt 2 复验 PASS 同时保留。中文和英文 README 已更新安装、Skill 调用、可观察状态、受控执行、恢复以及验证边界。后续文档提交单独校验，不冒充上述源码 CI 的提交。没有合并 main、发布 tag、生产部署或替用户签署验收；外部执行条件仍按前节如实列明。
