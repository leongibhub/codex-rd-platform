# Platform V2 Runtime Implementation Plan

> For agentic workers: execute with the repository implementation/testing/code-review skills and task-scoped independent verification. User explicitly requested implementation without another approval round.

**Goal:** 交付可使用的本地V2运行基础，而不是更多空模板。
**Architecture:** 版本化SQLite运行事实、受控命令、只读快照、同源本地看板。宿主执行与状态内核分离。
**Tech Stack:** Python >=3.11 stdlib + plain HTML/CSS/JS；现有MCP依赖保留。
**Spec:** docs/superpowers/specs/2026-09-06-platform-v2-runtime-design.md

## Global Constraints

- 不改main；当前分支codex/platform-v2-runtime。用户随后明确确认GitHub地址，推送现有origin，不创建GitLab远端。
- 用户AGENTS要求独立工作并行；按互不重叠文件所有权并行实现，覆盖通用Skill的串行默认。接口以上述spec为准。
- 不修改旧测试结果或宣称旧项目Gate PASS。每任务先写失败测试，再实现；独立测试和review后方交付。
- 子Agent不创建子Agent、不提交共享目录其他人的改动；主审统一提交。

## Task 1: TASK-V2-001 Durable runtime

Files: rd_platform/__init__.py, runtime.py, store.py; tests/runtime/test_runtime.py, tests/runtime/__init__.py.
Consumes: DES-V2-001接口。Produces: Runtime.execute/snapshot。
REQ-V2-001..005。先写临时SQLite测试：重复请求只创建一个对象、缺依赖拒绝、开发自验拒绝、FAIL重试全链、pause迟到输出拒绝、modify后下游失效。示例预期：`self.assertEqual(rt.execute('project.create', {'name':'a','idea':'b'},request_id='once')['id'], rt.execute('project.create', {'name':'a','idea':'b'},request_id='once')['id'])`。
- [x] 观察RED，实现事务/状态/校验，运行 `python -m unittest tests.runtime.test_runtime -v`。
- [x] 记录命令/count/exit；独立Review验证规格与并发边界。

## Task 2: TASK-V2-002 Dashboard and CLI

Files: rd_platform/web.py, cli.py, __main__.py, static/index.html, static/app.js, static/style.css; tests/runtime/test_web.py。
Consumes: Runtime接口；discovery/reporting按spec纯函数。Produces: loopback server+CLI。
REQ-V2-006/009。先HTTP真实临时端口测试：外站Origin拒绝、未知Host拒绝、过大body拒绝、run.finish不暴露HTTP、空快照无假任务、合法控制持久可见。`python -m unittest tests.runtime.test_web -v`。
- [x] RED→GREEN后交付可启动Board；用户可创建项目、任务、控制任务和查看事件。
- [x] CLI提供 `python -m rd_platform --help`，serve默认127.0.0.1:8020。

## Task 3: TASK-V2-003 Discovery and reporting

Files: rd_platform/discovery.py, reporting.py; tests/runtime/test_discovery.py, test_reporting.py。
Consumes: 原始idea和runtime snapshot。Produces: 初始模型、待确认问题、SRS/RTM/测试报告。
REQ-V2-007/008。先验证空idea拒绝、最多3个关键问题、推断不冒充事实、缺少必答不冻结、未执行不PASS、失败阻止建议发布。`python -m unittest tests.runtime.test_discovery tests.runtime.test_reporting -v`。
- [x] RED→GREEN，固定返回函数签名并通知CLI实现者。
- [x] 报告示例必须真实计算执行数/分母，无fake metrics。

## Task 4: TASK-V2-004 Compatibility fixes

Files: scripts/write_local_config.py; tests/platform/test_config_rewrite.py; .codex/agents/documentation-manager.toml。
REQ-V2-010。真实两MCP临时配置运行脚本，断言other section字节不变，含多行args；缺失目标拒绝且文件不变。先观察RED，再仅更新目标section。统一Evidence状态枚举。`python -m unittest tests.platform.test_config_rewrite -v`。
- [x] 修复回归；旧manifest/validator契约仍通过。

## Task 5: TASK-V2-005 Harness, docs and self-test

Files: rd_platform/runner.py; tests/runtime/test_runner.py; examples/; README.md; .gitignore; .agents/skills/platform-orchestration/SKILL.md; docs/platform-v2/。
Consumes: Task1..3接口。Produces: 真实命令执行、演练、操作说明。
- [x] 先测试真实子进程成功/失败/timeout，shell=False；集成内核记录证据。
- [x] 小应用用真实unittest和HTTP测试；演练发生实际review FAIL→修复→retest，保留真实宿主Agent身份。
- [x] 独立Tester执行定向单元/系统/黑盒测试；主协调执行完整回归及浏览器验收；独立Reviewer审完整分工范围，职责及证据见delivery-report。
- [x] 写原始输出与报告、启动说明、备份恢复/限制；提交Git，推送用户确认的GitHub origin并读回SHA（89261eb，见implementation-log）。

## Preflight interface check

| Tasks | Shared contract | Decision |
| --- | --- | --- |
| 1/2/5 | Runtime.execute/snapshot | 函数名、commands、字段在spec冻结；不重写其他任务源码 |
| 2/3 | discover/freeze, reporting | 3先发送函数签名，2使用延迟import |
| 4/others | 原平台脚本与新package | 所有权无交叉；新增Skill后同步manifest的14项清单并执行契约回归 |
| Each | 测试与生产行为 | 以真实临时DB/HTTP/命令观察结果，不断言mock本身 |

Progress由docs/platform-v2/implementation-log.md记录，检查框只在实际结果产生后更新。
