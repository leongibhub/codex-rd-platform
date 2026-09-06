# TASK-V3-010 独立 Test-run 验证

执行者：`/root/v3_qa_apps`（independent Tester）  
日期：2026-09-06  
范围：公共 CLI `python -m rd_platform ... test-run` 对已基线化、版本锁定 `AUTOMATED/argv` Test Case 的真实本地执行及证据接纳。本文不测试 HTTP 任意执行、不把本地 argv runner 表述为恶意代码沙箱，也不构成 Gate、发布、部署或人工验收。

## 测试模型

来源：`TASK-V3-010` 的可验证验收、`REQ-V3-006`（真实自动化命令与执行证据、失败缺陷）、`NFR-V3-003`（无部分状态）、`NFR-V3-004`（受信任本地 argv / 根目录限制）和 `NFR-V3-005`（版本与外部执行可审计）。模型先建立测试对象“版本绑定的 runner Case”、风险和 FUNCTIONAL test point，再创建 Case v2。

每个独立用例在新的 `TemporaryDirectory` 中经公开 `Runtime.execute` 建立独立项目、`REQ-001`、一个真实路径/hash 匹配的 `CODE-001`，和 Test Model/Case。Case v2 的 `automation` 明确为 `AUTOMATED`、`method=argv`、`argv=["{python}", "assertion.py"]`、`cwd="."`，且 `subject_refs` 为 `CODE-001 v1`。受测 argv 是测试自身生成的临时 Python 文件；不复用实现方 fixture 或 mock runner。

## 环境与实际命令

| 项目 | 观察值 |
| --- | --- |
| Host | Windows PowerShell，`D:\codex-rd-platform` |
| Python | `.venv\Scripts\python.exe --version`：`Python 3.13.5` |
| 开发回归命令 | `.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_lifecycle_runner -v` |
| 独立公共接口命令 | `.venv\Scripts\python.exe -X utf8 -m unittest tests.independent_v3.test_lifecycle_runner_independent -v` |
| 实际 CLI 入口 | 每个用例以子进程运行 `.venv` Python 的 `-m rd_platform --db <isolated-state.db> test-run --project-id … --case-id TC-001 --case-version 2 --executor-id tester` |

## 用例、可观察结果和状态

| 用例 | 类型 / 风险 | 步骤与预期 | 实际可观察结果 | 状态 |
| --- | --- | --- | --- | --- |
| TC-V3-IND-1001 | FUNCTIONAL / 版本或证据未绑定 | 运行打印断言成功的 argv；要求 Execution PASS、environment/execution evidence、可读取哈希 result 文件 | CLI 退出 0；Execution `PASS`、exit code 0；结果文件的 Case ref 为 `TC-001 v2`，并有 `test_environment` 与 `test_execution` evidence | PASS |
| TC-V3-IND-1002 | NEGATIVE / 失败被伪装成成功 | argv 输出后以 17 退出 | CLI 退出 1；Execution `FAIL`、exit code 17，创建一个 OPEN defect 且 `source_execution` 匹配 | PASS |
| TC-V3-IND-1003 | RECOVERY / 超时后延迟副作用仍发生 | argv sleep 2 秒后才写 `late.txt`；runner timeout 0.15 秒 | CLI 退出 1；Execution `FAIL`、`timed_out=true`；`late.txt` 不存在 | PASS |
| TC-V3-IND-1004 | RELIABILITY / 输出预算仍记 PASS | argv 输出 70,000 个字节 | CLI 退出 1；Execution `FAIL`、`output_truncated=true`；记录 stdout 不超过 65,536 bytes | PASS |
| TC-V3-IND-1005 | AUTHORIZATION / stale Case 或 developer 冒充 Tester 可启动命令 | 以 Case v1，及以 `developer` 对 Case v2 调用 | 两次 CLI 均为参数/契约拒绝 exit 2；无 sentinel、无 Test Execution | PASS |
| TC-V3-IND-1006 | DATA_CONSISTENCY / 运行后 CODE_CHANGE 漂移仍接纳 PASS | argv 修改已经被 `CODE-001` 路径 SHA-256 锁定的 `subject.py`，自身退出 0 | CLI 退出 1；命令观察仍为 `PASS`，但 Execution `FINISHED/BLOCKED`，无 defect；`result_path=null`，`unadmitted_result_path` 指向存在的 `RAW_COMMAND_OBSERVATION`，相邻 `admission.json` 为 `NOT_ADMITTED` | PASS |
| TC-V3-IND-1007 | RECOVERY / 生命周期暂停中把运行结果接纳为 PASS | 子进程 test-run 写 `started.txt` 后 sleep；确认启动后由独立 CLI `command lifecycle.control pause` | 运行 CLI exit 1、JSON Execution `FINISHED/BLOCKED`；断言进程仍完成写入 `completed.txt`，证明 pause 没有伪称杀死外部命令 | PASS |

最终独立命令实际退出 0，7/7 PASS，耗时 6.412s。上述 PASS 是独立临时项目中具体可观察结果，不是对任意用户 argv、HTTP 执行、生产任务或发布安全性的泛化保证。

## 初始 RED、缺陷与重测

第一次开发回归执行发生在审查回归正被引入/修复的窗口，实际命令运行 9 项并出现两项失败；该输出不被掩盖：

| BUG | 关联需求 / 复现 | 首次实际观察 | 处置与复测 |
| --- | --- | --- | --- |
| BUG-V3-RUNNER-001 | NFR-V3-003；`test_draft_case_must_not_execute` | `run_case()` 没有拒绝 `DRAFT` Case，预期 `ValueError` 未出现 | 修复后同一开发回归命令实际 9/9 PASS；独立所有 Case 均为 BASELINED v2。RETESTED PASS，独立 review 结论另行处理。 |
| BUG-V3-RUNNER-002 | NFR-V3-003；`test_interrupt_is_blocked_without_product_failure` | 注入 `KeyboardInterrupt` 后 Execution 实际为 `FAIL`，而非 fail-closed `BLOCKED` | 修复后同一开发回归命令实际 9/9 PASS；本独立的中途 pause 用例确认真实在途结果为 `BLOCKED`。RETESTED PASS，独立 review 结论另行处理。 |

修复后的开发回归命令：9/9 PASS（1.894s）。修复后的独立公共 CLI 命令：7/7 PASS（6.412s）。未登记人工批准、Gate 决策、部署或 release recommendation。

## 结论与未执行项

本轮验证了 PASS/FAIL、真实 timeout、实际 runner 输出预算、错误 executor、旧版本、源文件 TOCTOU 漂移与运行中 pause 的 fail-closed 表现。尚未执行：恶意 argv 的隔离/沙箱验证、HTTP 命令执行（设计上不提供）、多机/跨 OS 进程树恢复、长期负载/稳定性、真实生产凭据或部署。它们保持 `NOT_EXECUTED`，不能从本地临时项目的 7 项 PASS 推导。
