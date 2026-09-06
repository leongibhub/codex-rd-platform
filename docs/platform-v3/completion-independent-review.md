# CR-V3-003 独立代码与架构审查

评审状态：`IN_REVIEW`。评审基线为 `fd649c8`，当前对象是该基线之上的共享工作区变更；工作区尚未冻结，因此本报告不是最终 G8、发布或人工验收结论。

## 范围与门禁结论

本轮只审查已经出现且可执行的 `agent_projection.py`、`orchestration.py`、`Runtime.snapshot`、CLI/看板集成、worker、SSH 审批、部署和 Linux setup。并行开发中尚未出现或尚未冻结的交付物不按“缺失实现”报缺陷。

- Spec compliance：**FAIL（当前工作快照）**。真实无敏感 sentinel 探测已确认当前 Codex auto-review/profile 可以读写 workspace 外路径，REQ-V3-016 的控制面隔离不成立；替代 proposal backend 正在实施但尚未冻结。
- Code quality：**FAIL（当前工作快照）**。当前 worker 修复后的测试契约尚未全部同步，且实现/文档存在 output protocol 漂移；不能把较早绿色快照沿用为当前结论。
- Gate ruling：**NOT APPROVED**。未发现 P0；当前存在已确认开放 P1，且代码尚未冻结、P2/回归也未收敛。
- 边界裁定：取消进程可以保留 bounded/redacted 的 `worker_command / OBSERVED` 诊断，但不得成为 artifact、`output_refs`、`VERIFIED` 或 `DONE` 依据。当前 artifact admission 与 `work.finish` 已处于同一事务，本报告不把纯诊断记录列为缺陷。

## 开放发现

### CRV3-RV-001 — P1 — 已完成 deployment operation 可被不同配置/目标复用为成功 — RESOLVED / RETESTED

- Requirement/task：REQ-V3-018 / TASK-V3-018；操作幂等、目标绑定和数据完整性。
- Evidence：`rd_platform/deployment.py::_entries` 与 `execute_deployment` 当前在命中 `COMPLETED` 时直接返回 `prior[-1]["result"]`，没有比较已记录 `fingerprint` 与当前配置。
- Reproduction：先以 `operation_id=same-key` 完成 trial deploy；第二次保持同一 ID，但改变 `environment` 且把 deploy argv 改为 `exit 99`。第二次没有执行新命令，仍返回第一次的 `TRIAL_SUCCEEDED`，且返回对象仍是 `action=deploy`。
- Failure/impact：不同环境、argv、source hash 或 action 会被旧成功错误覆盖；自动化调用方可能把未部署目标当作已成功，破坏审计与恢复决策。
- Resolution evidence：实现已在 lock 前后核对 `config + effective action` fingerprint；当前 developer/independent 负面测试覆盖 target/payload 冲突及 deploy↔rollback 两个方向并通过。独立重放同 ID deploy→rollback 现在得到 fingerprint conflict，旧 deploy side effect 不被第二动作伪改。最终冻结后仍需完整回归。

### CRV3-RV-002 — P1 — 项目内 symlink 可把 argv 脚本逃逸到 root 外并绕过 source hash 固定 — RESOLVED / RETESTED

- Requirement/task：REQ-V3-018 / TASK-V3-018；显式目标、工件摘要与漂移阻断。
- Evidence：plain relative script 固定与每次命令前重哈希已经实现，但 `_command_sources` 将 `cwd/deploy.py` resolve 到 root 外后当成“trusted host tool”跳过；`_source_hashes` 同样会跟随 source entry 的 symlink。它没有区分配置本来就是外部 host executable，还是 lexical project path 经 link 逃逸。
- Reproduction：在 WSL 临时 project 下创建相对 `deploy.py` symlink 指向 `/tmp/.../outside/deploy.py`，`source_hashes` 只包含无关 `src`；executor 接受并返回 `TRIAL_SUCCEEDED`，外部脚本的实际 side effect 存在。
- Failure/impact：工作区内容可把受摘要约束的部署 argv 重定向到未固定的 root 外代码；receipt fingerprint 不能证明实际执行字节，破坏部署证据完整性。
- Resolution evidence：当前实现先保留 lexical cwd 归属，再逐组件拒绝 symlink/junction/reparse traversal，source hash 和 argv source 共用该约束。真实 WSL file-symlink 复现现在于 launch 前返回 `ValueError: source hash path cannot traverse symbolic links or junctions`；Windows junction 用例通过。Windows 普通 file symlink 因当前宿主缺创建权限而 skip，但不影响已执行的 Linux file-link 与 Windows directory-junction 边界证据。

### CRV3-RV-003 — P1 — formal `action=rollback` 被登记成新的成功 deployment — RESOLVED / RETESTED

- Requirement/task：REQ-V3-018 / TASK-V3-018；部署与回滚事实域分离。
- Evidence：`execute_deployment` 对 `action=rollback` 执行 rollback/rollback-health，但随后无条件调用 `_register_formal`；该函数先登记 `kind=deployment`，再调用 `release.record_deployment`。只有 `result.status != PASS` 才调用 `release.rollback`。同时 `_formal_preflight` 只接受 `READY` release，无法处理正常的 `RELEASED`/`DEPLOYMENT_FAILED` 显式回滚。
- Reproduction：用只返回 READY + current G10 的隔离 Runtime double 执行 formal rollback；物理 rollback PASS 后观察到命令序列为 `evidence.register`, `release.record_deployment`，没有 `release.rollback`。
- Failure/impact：正式回滚可把 release 状态重新写成 RELEASED，并将 rollback receipt 错标为 deployment evidence；真实恢复历史被反转。
- Resolution evidence：实现已拆分 `_register_formal_deployment` / `_register_formal_rollback`；真实隔离 Runtime fixture 完成 deploy 后 rollback，release 保留 1 条 deployment、1 条 rollback 并成为 `ROLLED_BACK`。最终冻结后仍需完整回归。

### CRV3-RV-004 — P1 — 正式部署 Gate 漂移/登记失败仍返回总体 PASS — RESOLVED / RETESTED

- Requirement/task：REQ-V3-018 / TASK-V3-018；正式 Gate 复核、unknown/crash/reconciliation。
- Evidence：`execute_deployment` 捕获 `_register_formal` 的 `KeyError/ValueError` 后只设置 `formal_registration_error`，保留 `result.status == PASS`；CLI `deploy-run` 又把 PASS 映射为进程 exit 0。
- Reproduction：隔离 Runtime 在物理 deploy/health 成功后令 formal evidence registration 抛出模拟 Gate drift；side effect 已存在，返回 `status=PASS`、`formal_registration_error="simulated Gate drift"`。
- Failure/impact：编排器会把“物理动作成功但正式 release 未登记、需人工对账”的 unknown/partial 状态当作正式成功。
- Resolution evidence：当前结果在登记失败时改为总体 `FAIL` 并保存 `actual_status=PASS`；CLI 同时拒绝带 `formal_registration_error` 的 0 退出。developer formal-drift 用例通过。最终冻结后仍需完整回归。

### CRV3-RV-005 — P1 — Linux setup 创建的默认 venv 与自身 MCP trust check 不兼容 — RESOLVED / RETESTED

- Requirement/task：REQ-V3-019 / TASK-V3-019；原生一键安装和真实 MCP health。
- Evidence：`scripts/setup.sh` 使用 `python -m venv .venv`，Linux 默认创建 interpreter symlink；`scripts/mcp_health_check.py:89-94` 对命令执行 `resolve(strict=True)` 后要求它仍位于 repository `.venv` 下。setup 也未验证复用的 `.venv/bin/python` 自身是 Python 3.11+。
- Reproduction：WSL 的标准 venv 生成 `bin/python -> python3`，最终解析为 `/usr/bin/python3.10`，不在 repo 下；这会被 `MCP_COMMAND_UNTRUSTED` 拒绝。当前测试只覆盖缺 identity、低版本和 validator double 失败，没有 Python 3.11+ 的真实成功路径。
- Failure/impact：普通 Linux 主机即使满足 Python 版本和依赖，也可能在 setup 最后的真实 health 自我拒绝，无法达到一键可运行。
- Resolution evidence：setup 当前使用 `venv --copies`，并在创建/复用后验证 `.venv` 与 interpreter 的 resolved containment 及实际 Python 3.11+。当前 reviewer 本地/WSL 套件 6/6 通过，覆盖 copied venv 控制流、外部 interpreter symlink 拒绝、identity 前置失败、validator fail-closed 与公开 launcher 的低版本拒绝。[GitHub Actions Ubuntu job 101496781967](https://github.com/leongibhub/codex-rd-platform/actions/runs/34036999184/job/101496781967) 及其 `Verify actual native Linux setup and repeat installation` 步骤均为 success；job head `9f12b930...` 中 `setup.sh` blob `899dc0c1...` 与当前文件一致。

### CRV3-RV-006 — P2 — trial deployment 成功被 CLI 映射为 exit 1 — RESOLVED / STATICALLY VERIFIED

- Requirement/task：REQ-V3-018/020 / TASK-V3-018/020；CLI 可自动化性与向后兼容。
- Evidence：trial executor 的成功状态是 `TRIAL_SUCCEEDED` 或 `TRIAL_ROLLED_BACK`；`rd_platform/cli.py` 当前只有 `result.status == "PASS"` 才返回 0。
- Failure/impact：成功 trial 被 CI/脚本判失败；与 JSON 结果矛盾。
- Resolution evidence：CLI 已将 `PASS`、`TRIAL_SUCCEEDED`、`TRIAL_ROLLED_BACK` 且无 formal registration error 映射为 0。最终仍需 CLI 子进程用例，而不只做静态/函数级核对。

### CRV3-RV-007 — P1 — 当前 Codex worker 可读写 workspace 外路径，控制 DB 路径分离不是安全边界 — RESOLVED / RETESTED

- Requirement/task：REQ-V3-016 / TASK-V3-016；控制面与模型执行面隔离。
- Evidence：`worker_backends.validate_backend` 只拒绝 DB 位于 repository root 内。独立架构探测在临时 workspace 及同级 `fake_control/sentinel.txt` 上运行真实 `codex exec --approve-for-me --ignore-user-config --ephemeral`，未使用 `--add-dir`、danger 或 bypass；模型成功读出固定非秘密文本、把同级 sentinel 改写，并写入 workspace。`last-message.json` SHA-256 为 `5C5BE0E740068B171A6111F915D18233EA6390DD4D21CCA28A1F6043FEC0DDE8`，记录 `outside_read/outside_write/inside_write` 均为 `SUCCEEDED`。探测没有访问真实 DB 或凭据；临时证据不是仓库受控发布证据。
- Reproduction：新建临时 `BASE/workspace` Git 仓与 `BASE/fake_control/sentinel.txt`；以 cwd `workspace` 运行上述 Codex 命令，prompt 只授权读写该固定 sentinel。宿主在执行前后比较精确字节，观察到 `RD_CONTROL_SENTINEL_V1\n` 被改为 `RD_OUTSIDE_WRITE_ATTEMPT\n`。
- Failure/impact：与 workspace 同 OS 身份可访问的控制 DB 不但可能被读取，也可能被改写；模型可绕过 Runtime 的租约、审批和 evidence authority boundary。路径保密或放在 sibling 目录不能满足“模型不可读控制 DB/铸证”。
- Resolution evidence：production backend validation 当前无条件拒绝 `type=codex`，新增 Responses transport 设置 `tools=[]`、`tool_choice=none`、`store=false`，只发送 host 组装的版本锁定 context，model response 只能进入 host proposal admission；因此上述同 OS Codex shell 路径已 fail closed。focused test 验证 Codex config 被拒绝、Responses 收到 bound context。完整研发能力与原“真实 Codex CLI backend”要求的冲突另见 RV-014；公开文档漂移见 RV-016。

### CRV3-RV-008 — P1 — dependency artifact 字节漂移可作为固定版本上下文并使 consumer DONE — RESOLVED / RETESTED

- Requirement/task：REQ-V3-016 / TASK-V3-016；输入版本/摘要、失效与晚到写入的数据完整性。
- Original evidence：早期 `worker_service._context_bundle` 只比较 current row 的 `version` 与 dependency `output_ref.version`，随后直接读取 path，没有比较 `content_ref.sha256`；`work.finish` 也未重新 fence dependency outputs。
- Reproduction：dependency DONE 输出 `DES-X v1`（登记内容 `PINNED`）；不调用 `artifact.revise`，直接把文件改为 `DRIFTED`；consumer 仍可 claim，context 在 v1 ref 下提供 `DRIFTED`，随后 `work.finish` 成功成为 DONE。观察到 registered SHA 与 actual SHA 不同。
- Failure/impact：模型可基于未登记、未固定的内容继续生命周期，且 consumer DONE 看似消费了 v1；版本链与摘要证据失真。
- Resolution evidence：当前实现将 input 与 dependency output 合并为 bound refs，在 dispatch 前、context 读取前和 artifact admission/work.finish 同一事务内校验 current version/content hash；path 内容读取也核对 SHA-256。独立重放显示 dispatch 前漂移得到总体 `FAIL` 且 work durable `REJECTED/attempt=0`，执行中漂移得到 `FAILED/attempt=1`，两者均不能 `DONE`。最终测试需把旧的 `FAILED` 单一断言同步为允许 pre-claim `REJECTED`，并固化 raw byte drift 的前/中两种负面用例。

### CRV3-RV-009 — P1 — worker 可回显既有 input ref 满足输出合同而不产生任何新输出 — RESOLVED / RETESTED

- Requirement/task：REQ-V3-016 / TASK-V3-016；真实输出、原因、版本和交接，禁止把空执行当完成。
- Original evidence：`work.finish` 只校验 output ref 的 current/type/count；worker 对 envelope 的既有 `output_refs` 没有检查其是否由当前 claim/attempt 产生或修订，也没有禁止 input/dependency ref 原样回显。
- Reproduction：work 要求 `DOC/min_outputs=1` 且 input 是 `DOC-OLD v1`；backend 返回 `DONE`、`artifacts=[]`、`output_refs=[DOC-OLD v1]`。service `completed=1`，work 成为 DONE，artifact count 不变且 input_refs 与 output_refs 相同。
- Failure/impact：特别是多个要求 DOC 的 G1/G7–G11 阶段可以复用前序文档，形成“工作已完成”假象；即使 Gate 仍独立，执行链和交接证据已经失真。
- Resolution evidence：当前 backend envelope 对任何非空 `output_refs` fail closed，只允许由 host 在当前 finish 事务中验证 path/SHA-256 并登记的新 artifacts。原始回显复现现在得到 `result.failed=1`、work `FAILED`，artifact count 不变且没有 output refs。最终需将该复现固化为 model/argv 负面测试。

### CRV3-RV-010 — P2 — worker 输出协议文档仍允许实现已经拒绝的 `output_refs` — RESOLVED / STATICALLY VERIFIED

- Requirement/task：REQ-V3-016/020 / TASK-V3-016/020；可运行接口与中英文交付一致性。
- Evidence：`worker_backends.parse_envelope` 当前对任何非空 `output_refs` 抛出 `worker backend must declare new artifacts`；`docs/platform-v3/worker-service.md` 仍写明 `output_refs must already be current Runtime references`，并暗示这种输出受支持。
- Reproduction：按文档返回任一 current ref 会被 backend 拒绝，work 成为 `FAILED`；这正是 RV-009 修复后的预期实现，却与公开协议相反。
- Failure/impact：运维者或自定义 backend 按文档实现后会稳定失败；模型 prompt/schema 也保留了一个实际禁止的非空数组形状，增加误生成和无效重试。
- Resolution evidence：worker 协议现明确 `output_refs` 必须为 `[]`，response schema 设 `maxItems: 0`，实现与示例均要求新输出经当前 attempt 的 host admission。冻结后仍需核对新增 Responses proposal 协议的中英文等价说明。

### CRV3-RV-011 — P1 — formal 项目外 receipt 在真实副作用后才导致登记失败 — RESOLVED / RETESTED

- Requirement/task：REQ-V3-018 / TASK-V3-018；正式部署预检、事实登记与已知无效配置 fail closed。
- Original evidence/reproduction：`_write_receipt` 对项目外目录返回 relative path `None`，调用方却传递 `(None, hash)`；formal helper 只检查 tuple 是否为 `None`。以真实 READY release 执行项目外 `receipt_dir` 时，deploy/health 已成功且 `served.txt` side effect 存在，之后 Runtime 才报 `path must be non-empty text`；结果 `FAIL/actual_status=PASS`，release 仍 `READY`、deployments 为 0。
- Failure/impact：配置在副作用前已确定不可能登记，却仍执行正式目标，制造可预防的生产事实/Runtime 真相分叉。
- Resolution evidence：formal 当前在创建 receipt、写 STARTED 或启动命令前要求 receipt_dir resolve 在项目根内，formal helpers 同时验证 tuple 的 relative member。原始真实 READY-release 复现现在抛出 `formal receipt_dir must stay beneath project repository`，side effect 不存在、release 仍 READY、deployments 为 0；对应定向回归通过。

### CRV3-RV-012 — P1 — Responses backend 未收到版本锁定 work context 却可完成 work — RESOLVED / RETESTED

- Requirement/task：REQ-V3-016 / TASK-V3-016；输入版本、原因和真实交接。
- Original evidence/reproduction：新增 `responses` backend 后，`_run_claim` 只为 `type == codex` 调用 `_context_bundle`。带 BASELINED BG input 的 work 经捕获 backend seam 观察到 `context_bundle=null`，模拟 no-tools response 返回 `DONE/proposals=[]` 后 work 仍成为 DONE。
- Failure/impact：远端模型不知道实际 work、原因或版本输入，min_outputs=0 时可把空上下文响应登记为任务完成。
- Resolution evidence：当前 `_run_claim` 为 Responses 组装 context，`execute_backend` 也传递 cancel event。原复现现在确认 request seam 收到精确 work id 与 resolved BG 内容；proposal/worker focused suite 10/10 通过。冻结前需把 request body/context 断言固化进测试。

### CRV3-RV-013 — P1 — proposal 与既有文件冲突时未捕获 `FileExistsError`，work 遗留 CLAIMED — RESOLVED / RETESTED

- Requirement/task：REQ-V3-016 / TASK-V3-016；失败持久化、租约恢复和数据完整性。
- Original evidence/reproduction：proposal 指向已存在 `app.py` 时，exclusive `open("x")` 抛出 `FileExistsError`，但 `_run_claim` 只捕获 `ValueError/KeyError`；执行线程崩溃，service 返回 `DISPATCHED/cancelled=1`，work 仍 CLAIMED，无 artifact 或失败摘要。
- Failure/impact：租约过期后进入 unsafe-retry skip，可恢复 work 被静默卡死；service 总体状态也与线程崩溃相反。
- Resolution evidence：materialization/admission handler 现捕获 `OSError` 并只清理由本 attempt 创建的文件。原复现现在为总体 FAIL、work FAILED，既有文件内容不变且 artifact count 为 0。冻结前仍需加入 exact collision/permission regression。

### CRV3-RV-014 — P1 — 唯一安全模型 backend 只能创建新文件，无法执行既有代码的修复/重试 — OPEN

- Requirement/task：REQ-V3-016/020 / TASK-V3-016/020；真实完整研发、失败→修复→重测循环，以及原设计的真实 Codex CLI 执行能力。
- Evidence：因 RV-007，production validation 已拒绝 `type=codex`；`responses` 的 host admission 对每个 proposal 使用 exclusive `open("x")`，没有受版本/摘要约束的 update 或 delete 操作。模型也只有 host 提供的注册 context，没有本地工具。
- Reproduction：G6 work 要求修复既有 `app.py`，Responses proposal 对同一路径给出新内容；安全实现按预期拒绝，work FAILED、旧文件保持不变、无 CODE_CHANGE artifact。即使首次 greenfield create 成功，G7 缺陷后的 retry 也无法修订该文件。
- Failure/impact：当前安全路径无法完成最普通的维护、缺陷修复和迭代开发；禁用不安全 Codex 后，用户目标“Skill 真正驱动完整研发”及 development loop 没有等价执行能力。
- Required remediation：以 material design/risk decision 选择：实现 host 侧 CAS journal（update 必须携带 expected current SHA/version、限定已授权路径/类型、拒绝 link/reparse、有限大小、原子替换并在 admission 失败时可靠恢复），或把 create-only 限制明确上升为不满足本 CR 的开放范围并不得宣称完整执行。不能退回 blind overwrite 或同 OS 不隔离 shell。

### CRV3-RV-015 — P1 — Responses 请求开始后忽略 cancel event，可阻塞至一小时 timeout — RESOLVED / RETESTED

- Requirement/task：REQ-V3-016 / TASK-V3-016；暂停/失效停止 owned execution、有限资源与服务恢复。
- Original evidence/reproduction：transport 只在 HTTP open 前检查一次 cancel，随后同步 `response.read`。slow-response fixture 进入 read 后置 cancel，1 秒后线程仍存活；释放 response 后函数返回 PASS。worker timeout 上限 3600 秒。
- Failure/impact：late DONE 虽被 lease fence 阻止，外部生成请求、费用及 worker service 仍无法按 pause/stop 及时终止。
- Resolution evidence：response read 现由 daemon reader 执行，外层轮询 cancel 并关闭 response；相同 slow-response 复现于约 0.06 秒返回 `FAIL/cancelled=true`，不再接受 late PASS。冻结前需固化 slow-read 与 run_service stop-latency regression。

### CRV3-RV-016 — P2 — 公开 worker 文档仍引导使用已禁用且证实不安全的 Codex backend — OPEN

- Requirement/task：REQ-V3-016/020 / TASK-V3-016/020；安全配置与中英文可运行交付。
- Evidence：`worker_backends.validate_backend` 当前对 `type=codex` 直接 fail closed，安全路径改为 `responses`；但 `worker-service.md`、README/README.en 的配置、flag 与运维段落仍宣传 `sandbox=workspace-write`、`approval_mode=auto-review` 和 Codex CLI 行为。
- Reproduction：复制当前文档示例运行 worker-service，配置阶段即得到 `codex backend is not production-safe; use responses proposals`；文档同时继续暗示 workspace 与 DB 分目录即可保护控制面，与 RV-007 实证冲突。
- Failure/impact：操作者按正式指南无法启动 worker，或继续相信已经证伪的安全边界；Responses key/endpoint、no-tools、proposal admission 与 create-only 限制没有可操作说明。
- Required remediation：同步中英文设计/指南/示例与 Skill，保留真实 sandbox probe 的安全 ruling，说明 Responses secret/environment、endpoint、context、no-tools、proposal/DRAFT 及当前 create-only 限制；不得把禁用 Codex 示例保留为生产路径。

## 已验证但不构成批准

### 已冻结模块的独立结论

- TASK-V3-017 / REQ-V3-017：**PASS（模块级 spec compliance 与 code quality）**。真实临时 Ed25519 developer/independent 套件 4/4，通过 challenge binding、wrong key、scope/tamper、future/expiry/TTL、Agent identity、stale artifact 与 replay；额外 reviewer 重放确认 CLI challenge→sign→register 为 `recorded_role=human`，两线程并发提交同一签名只登记 1 条 approval。V2 review run `run-03af9fbd95984c418855705d30adeabf` 为 PASS，task 已 DONE。所有 key/project/approval 均为临时 fixture，不代表真实人工批准或 Gate。
- TASK-V3-019 / REQ-V3-019：**PASS（模块级 spec compliance 与 code quality）**。当前 reviewer 本地/WSL 6/6 与上述精确源码的 Ubuntu actual setup/repeat job 均通过；V2 review run `run-5344bbd9f4b74f4082219f1302abbf0f` 为 PASS，task 已 DONE。本机 WSL 的 Python 3.10 只提供正确拒绝证据，成功 health 证据来自 Ubuntu job；两者未混淆。

- 较早开发单测快照 21/21 通过；随后独立端点套件曾 15/15 通过，并覆盖 artifact 事务、dependency version、operation fingerprint、plain relative script、formal drift/rollback 等修复。最新 worker 修复后，定向重跑暂有两个测试契约同步失败：pre-claim stale ref 现在 durable `REJECTED` 而旧断言只接受 `FAILED`，以及 output-ref fail-closed 的错误文案已改变；这不是上述绕过复现重新开放，但冻结前必须同步并全量转绿。套件仍未覆盖 CRV3-RV-002 的 Linux symlink escape、CRV3-RV-005 的真实 Linux 成功路径或 CRV3-RV-007 的真实模型读隔离。
- worker 多 artifact 登记已改为单事务；第二项无效时第一项不应残留。依赖输出 ref 的 version/content 检查已加入且旧 ref 回显已 fail closed。最终冻结后需要重跑完整回归。
- SSH challenge 当前已校验 `expires_at - issued_at <= configured TTL`；早期工作快照的 TTL 绕过已消失，不列开放发现。最终仍需复核授权、过期、重放和 Agent identity 独立用例。
- HTTP allowlist 当前不包含 worker execute、deployment execute、approval submit 或任意 argv；这是当前符合项，不代表整个本地 HTTP 面已获得身份认证。

## 最终复审条件

代码、测试和文档冻结后，逐项重放 CRV3-RV-001..016；运行完整 Runtime/platform/独立测试与五栈回归；核对真实安全 proposal execution、Linux 成功安装、部署失败补偿 receipt、formal Gate drift 与显式 rollback 历史。只有 P0/P1 清零、spec/code 两项结论重新评定后，才可给出最终 G8 建议。
