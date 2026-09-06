# 平台 V2 本地运行基础设计

- Record ID: DES-V2-001
- Document State: BASELINED
- 请求来源：用户在现状审计后明确要求“直接修改吧，修改完后记得提交到gitlab”。这授权实施和提交，不代表最终验收。
- Change: CR-V2-001；现有 G0–G11 template 契约不改号、不虚构项目 Gate。

## 交付范围与约束

在现有仓库增量加入可运行的本地控制面：SQLite 持久 Task/Run/Event、质量闭环、需求发现结构化输入/输出、真实状态网页、CLI、实际命令执行/报告、独立测试和小项目演练。Python >=3.11，运行内核和 HTTP 使用标准库，无新云服务或必要联网依赖。包名 rd_platform，避免覆盖标准库 platform。

本地单用户信任边界：CLI 为可信操作员/宿主适配器；HTTP 仅绑定127.0.0.1，拒绝外站 Origin/异常 Host、限制请求体，不提供任意命令或代码执行接口。身份字段用于可信宿主的职责分离，不冒称恶意本地用户无法伪造。暂停是停止调度/逻辑取消，不能宣称杀死未经跟踪的远端进程。

AI 推理仍由当前 Codex/其他宿主负责；提供结构化交接包与 CLI 接口，不伪装已拥有后台独立模型服务。无需密钥的需求发现提供有解释的初始模型和待确认建议；不把关键词规则当作深入 LLM 理解。真实自主模型连接通过可替换适配器后续接入，界面如实显示连接方式。

## 验收标准与追踪

| ID | 验收 |
| --- | --- |
| REQ-V2-001 | 项目/Agent/Task/Run/Event 持久化，重开数据库可恢复，事件有顺序和关联ID |
| REQ-V2-002 | 任务依赖必须同项目且已存在，未DONE依赖不能开始；每任务最多一个活动Run |
| REQ-V2-003 | implementation→unit→integration→review，开发执行者不能自验；测试与review身份分离；有证据的最终review PASS才DONE |
| REQ-V2-004 | FAIL创建缺陷，retry有上限且清空旧轮验证，重测全链通过后关闭关联缺陷；失败/跳过不可计PASS |
| REQ-V2-005 | pause/resume/retry/reject/reassign/modify/skip控制有事件；修改递增版本、作废下游旧结果，迟到Run拒绝回写；重复请求幂等 |
| REQ-V2-006 | 看板展示真实项目、角色、任务理由、输入输出、阶段/状态、完成检查数、阻塞、交接和事件；无假数据 |
| REQ-V2-007 | 一句话产生事实/推断/未知、业务流、权限数据风险、少量关键问题及建议/原因；确认后导出SRS/RTM；不自动批准 |
| REQ-V2-008 | 运行测试命令真实采集exit/output/time，超时为失败；报告区分PASS/FAIL/NOT_EXECUTED/BLOCKED并给出发布建议 |
| REQ-V2-009 | CLI和HTTP契约一致，HTTP不接收任意命令、不允许外站写入，输出转义，数据目录gitignore |
| REQ-V2-010 | 修复MCP配置更新误改其他section，保留现有平台回归；提供启动/备份/恢复/限制说明 |

## 公共接口（跨任务冻结）

`rd_platform.runtime.Runtime(db_path)`：每次操作独立事务/连接，SQLite锁和事务保护并发；`execute(command: str, data: dict, *, request_id: str | None = None) -> dict`；`snapshot(project_id: str | None = None) -> dict`。

snapshot 顶层键：projects、agents、tasks、runs、events、defects（均为字典列表）。Task至少有id、project_id、title、why、role、requirements、dependencies、inputs、status、revision、next_phase、checks_passed、checks_total；Run含id/task_id/agent_id/phase/status/revision/evidence/summary；event有id/type/project_id/task_id/run_id/created_at/data。project含id/name/idea/stage；agent含id/role/status/task_id/heartbeat_at。

commands：

- project.create `{name, idea}` → project对象（带id）。
- agent.register `{id, role}` → agent对象；role developer/tester/reviewer/requirement_analyst等，未知role拒绝。
- task.create `{project_id,title,why,role,requirements:[str],dependencies:[id],inputs:dict}` → task对象。
- run.start `{task_id,agent_id,phase}` → run对象；phase implementation/unit/integration/review；职责和顺序由内核校验。
- run.heartbeat `{run_id}` → run对象。
- run.finish `{run_id,status:PASS|FAIL,summary,evidence:dict}` → task对象；evidence非空，失败打开defect；review成功方可DONE。
- task.control `{task_id,action,reason,...}` → task对象；action pause/resume/retry/reject/reassign/modify/skip；reassign带agent_id；modify可带title/why/inputs。
- project.control `{project_id,action:pause|resume,reason}` → project对象。

ID由内核生成；agent ID允许宿主提供。非法请求抛 ValueError/KeyError，不能500或部分提交。request_id复用同命令/载荷返回同结果，不同载荷拒绝；任意状态改变和事件原子提交。暂停/修改/重试使活动Run失效，不接受其之后finish。跳过状态SKIPPED，不满足依赖DONE。质量检查以当前revision和attempt为准。

## 模块边界

- rd_platform/runtime.py + store.py：事务、状态、依赖、质量、事件、缺陷。
- rd_platform/web.py + static/：本机只读快照/有限控制与真实Board；GET /api/snapshot，POST /api/commands `{command,data,request_id}`；HTTP仅允许project.create/agent.register/task.create/task.control/project.control。
- rd_platform/discovery.py：纯函数discover(idea)->dict，freeze(model,answers)->dict，显式用户确认前不标APPROVED。
- rd_platform/reporting.py：从快照导出测试/追踪报告，无执行记录不能PASS。
- rd_platform/cli.py + __main__.py：serve/command/snapshot/discover/report；JSON输入输出；持久数据默认 .rd-platform/state.db。
- rd_platform/runner.py：可信CLI命令执行适配器，argv数组shell=False，指定cwd、超时、输出预算；不得由HTTP调用。
- tests/runtime/：模块回归；examples/：明确标记演练的自包含小项目，不用演练代替真实人工验收。

## 取舍

选择本地模块化单体：可快速验证实际工作流，保留未来host/worker适配边界。拒绝纯日志看板（不提供可靠状态），暂不建分布式多租户服务（需求未明确且会扩大攻击面）。Git继续保存工程基线；SQLite保存运行事实；本次不修改旧RTM语义，以新运行记录表达独立验证与发布状态，后续做版本化迁移。

## 本轮诚实边界

可交付是V2可运行基础，不把一个版本宣称覆盖任意应用自主生成、72小时稳定性或生产安全认证。升级总目标仍按审计路线分阶段；本轮必须给出实际可运行界面、验证和已知限制。最初GitLab目的地不明确；用户随后明确确认现有GitHub仓库，授权推送origin开发分支，不合并main。

## 审查后契约澄清

- 分配绑定当前阶段，完成后清除；skip/reject也作废自身及传递下游当前版本的质量结果。
- 命令PASS证据必须exit_code为整数0，且不含timeout、截断或launch_error；独立宿主审查可用非命令证据，但不能包含矛盾失败字段。
- 输入/输出采用严格JSON：拒绝NaN/Infinity，超深或超长数值解析失败转为受控请求错误，无部分提交。
- Windows命令树使用先约束后执行的Job；输出流限额/脱敏，清理故障返回FAIL。它不是针对恶意本地用户的安全沙箱。
