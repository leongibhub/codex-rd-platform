# V2 本地研发运行台

本版本把任务、Agent交接、质量检查、缺陷和控制操作存入SQLite，并提供中文看板和CLI。它保留原有9类角色、14个Skill（新增platform-orchestration）、MCP和G0–G11模板政策。

这是可信本地操作员/宿主协作工具，不是已自动连接模型的无人值守云服务。无需新增依赖；Python >=3.11。原MCP依赖仍用于原平台校验。

## 启动

在仓库根目录：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform serve
```

打开 http://127.0.0.1:8020/ 。仅允许127.0.0.1，其他host拒绝。用 `--db` 在子命令前指定隔离数据库：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform --db .rd-platform/my-project.db serve --port 8021
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform snapshot
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform discover "开发一个内部测试管理系统"
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform report
```

看板支持创建项目、登记Agent、创建任务、查看运行/事件、暂停/恢复/重试/拒绝/重新分配/修改/跳过。任务输入使用JSON对象，Requirement ID每行一条。全部信息来自数据库，不加载伪造的进度数据。单个任务的4项检查是 implementation、unit、integration、review；不是整个产品的全部测试类型。

## 把真实Agent工作接入

在Codex中使用仓库Skill `platform-orchestration`。宿主负责真正派发Agent，本地Runtime负责验证任务依赖、阶段和证据，不能仅创建一个Agent名称就声称已启动模型。

Python接口也可被其他可信宿主调用：

```python
from rd_platform.runtime import Runtime

r = Runtime('.rd-platform/state.db')
p = r.execute('project.create', {'name': '我的应用', 'idea': '业务目标'}, request_id='project-once')
r.execute('agent.register', {'id': '实际宿主开发者ID', 'role': 'developer'}, request_id='developer-once')
t = r.execute('task.create', {
    'project_id': p['id'], 'title': '实现一个模块', 'why': '满足已确认业务需求',
    'role': 'developer', 'requirements': ['REQ-001'], 'dependencies': [],
    'inputs': {'spec': 'docs/my-approved-spec.md'},
}, request_id='task-once')
run = r.execute('run.start', {'task_id': t['id'], 'agent_id': '实际宿主开发者ID', 'phase': 'implementation'})
```

上例仅登记开始；不能直接抄一条PASS作为结束。实际执行后将真实命令/输出/产物引用填入 `run.finish` 的 evidence。测试与审查必须使用实际独立执行者。HTTP不暴露run.start/run.finish或任意命令执行，只有可信CLI/宿主可操作。

### 执行真实本地测试

`run` 是可信CLI适配器，会记录start、实际exit/output/time以及finish；shell=False，必须使用argv列表。先注册对应角色，并使用真实task ID：

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform run --task-id TASK_ID --agent-id TESTER_ID --phase unit --cwd . --timeout 60 -- .\.venv\Scripts\python.exe -m unittest examples.task_board.test_unit -q
```

TESTER_ID必须已登记为tester；implementation必须已通过。下一阶段integration随后review。命令失败、超时或输出超过预算都会记录FAIL，CLI非0退出并打开缺陷。命令exit0本身不能证明验收充分：宿主仍须选择适用测试、检查测试数量和结果、执行独立Review。

## 控制语义

- pause：使当前Run失效并停止调度，不等于终止外部Agent/远端作业。用宿主取消工具处理真实进程，另记录结果。
- resume：只恢复可恢复暂停状态；FAILED不能通过pause/resume绕开retry。
- retry：有上限，开启新attempt并重新做全部质量检查，不复用旧PASS。
- modify：增加revision，使受影响下游任务旧结果过期；晚到输出不能覆盖新版本。
- reassign：不能在活动执行中无声转移，新的实际执行须符合分配与角色。
- reject/skip：不是PASS；SKIPPED不满足下游DONE依赖。
- 同一request_id、同载荷只执行一次；同ID不同载荷拒绝。

## 需求和报告边界

`discover` 是无模型依赖的初始结构化辅助，明确标 `baseline_no_model`。使用宿主Agent补充领域分析、业务流程、隐含需求、冲突和风险，再问关键问题。`freeze` 只输出DRAFT SRS和PARTIAL RTM，不能伪造用户批准。

`report` 范围为MODULE_QUALITY：区分当前版本/attempt的执行、失败、阻塞、未执行、跳过，另列历史缺陷。测试覆盖不冒称完整设计/代码/发布追踪。即使模块完成，未有部署和人工验收时也只给NO_RELEASE_EVIDENCE，不自动给产品发布PASS。

## 测试与演练

```powershell
& .\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests/runtime -v
& .\.venv\Scripts\python.exe -X utf8 -m unittest examples.task_board.test_unit examples.task_board.test_blackbox -v
& .\.venv\Scripts\python.exe -X utf8 scripts/validate_platform.py
```

`examples/task_board` 是独立Agent实际开发和黑盒验证的小应用，需求见其SPEC。X-Role仅是测试角色边界，绝不是身份认证；不能部署到互联网。真实Agent交接证据留在本机运行库和本目录报告，不把模拟审批当成人工验收。

原 `tests/platform/test_setup_contract.py` 有9项真实安装测试，普通无安装回归不运行；单独受控环境才运行整个原测试集。使用仓库venv而不是系统Python，以免MCP版本不同制造错误基线。

## 数据、备份与恢复

- 数据默认 `.rd-platform/state.db`，Git忽略；不要把本机任务数据或凭据提交远端。
- SQLite事务保证命令和事件同时提交；重新运行同一DB恢复记录。中断的活动Run不会自动冒称成功，操作员应核验真实宿主状态后pause/resume或失败处理。
- 停止服务和其他写入者后复制DB做备份；若将来启用WAL，使用SQLite backup API而不是只复制主文件。恢复前保留当前DB副本，用明确目标替换，再查看snapshot核验。
- 代码回退采用Git受控revert/已知版本重新部署，不删除运行证据；本版本尚未提供通用数据库降级或环境自动回滚按钮。
- 运行输出按预算截取，敏感命名环境变量值尽力脱敏；不能保证任意业务文本自动脱敏。不得让测试命令打印秘密或把私有结果复制到公共仓库。

## 尚未完成的升级目标

后台模型执行服务、真正的用户鉴权/多租户、结构化全生命周期关系存储、完整G0–G8政策迁移、通用部署/回滚适配器、全套性能/压力/长稳/安全矩阵、无人值守缺陷修复策略、知识模式评测。当前版本不冒充整个架构升级最终验收。
