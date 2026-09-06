# Python CSV 费用分析工具实现记录

任务：`TASK-V3-003`（Python 子应用）；需求：`REQ-MATRIX-PY`、`REQ-MATRIX-PY-01` 至 `REQ-MATRIX-PY-04`。

## 实现摘要

- 新增标准库 CLI `expense_analyzer.py`：使用 UTF-8-SIG CSV、严格的列/行/日期校验和 `Decimal` 汇总；成功时输出金额字符串 JSON，失败写 `error:` 到 stderr 并返回非零。
- 新增 9 个开发者单元/CLI 测试，覆盖正常汇总、Decimal `0.10 + 0.20`、BOM/重排列、零值、空输入、日期/金额/结构拒绝和退出语义。
- 新增 manifest v1；只声明已具备的 `build` 与开发者 `unit` argv 命令，不将独立黑盒验证冒充为 integration。`build` 以 `-X pycache_prefix={build}/pycache` 将字节码缓存限制在受控构建目录，避免在应用源码树产生构建产物。
- 处理独立评审 `REV-V3-APP-002`：解析后按已验证输入的指数跨度和行数推导本地 Decimal 精度，不再使用默认 28 位累加上下文；同时明确限制每金额 1,000 有效位、指数范围 [-1,000, 1,000] 和 100,000 行，超限失败而不返回舍入结果。
- 处理 `REV-V3-APP-003`：manifest 的 unit 与 build 均使用 `-X pycache_prefix={build}/pycache`，使受 Harness 执行的导入/编译缓存进入 `.rd-platform/build/python_expenses/pycache`。

## 实际验证

| 检查 | 命令 | 结果 | 证据状态 |
| --- | --- | --- | --- |
| RED 起点 | `PYTHONUTF8=1 .venv\\Scripts\\python.exe -m unittest discover -s examples\\multistack\\python_expenses\\tests -v` | 退出 `1`；模块不存在，收集到 1 个 `ModuleNotFoundError`。 | OBSERVED |
| 开发者单元 | `PYTHONUTF8=1 .venv\\Scripts\\python.exe -m unittest discover -s examples\\multistack\\python_expenses\\tests -v` | 退出 `0`；9 tests passed，0 failures/errors，耗时 0.655s。 | OBSERVED |
| 字节码编译 | `.venv\\Scripts\\python.exe -m compileall -q examples\\multistack\\python_expenses` | 退出 `0`，无输出。 | OBSERVED |
| diff 格式 | `git diff --check` | 退出 `0`，无输出。 | OBSERVED |

## BUG-MATRIX-PY-001 归因与 attempt 2

独立 Tester 的 integration attempt 1 实际为 `FAIL`：3 个用例中 2 个通过，`test_bom_reordered_header_and_exact_totals` 失败。保留该首次失败的 Runtime run `run-550a33c9a740431da74c7bd76ec1464a`，不覆盖其证据。

开发者复核发现该 QA fixture 的 Python 字符串写入了字面 `\\n`，而非换行符；文件因此是单行且表头不再恰有 `date`、`category`、`amount` 三列。依据 `REQ-MATRIX-PY-01`，拒绝该非 CSV 输入是正确行为。因此归类为 `TEST_SCRIPT`，不是产品缺陷；没有为接受字面反斜杠-n 而放宽 CSV 校验。独立 Tester 需修正其自身 fixture 并重新执行黑盒回归。

attempt 2 的开发者 manifest 验证（真实运行）使用 `run_matrix(..., phases=('build', 'unit'))`：build 退出 `0`，unit 退出 `0`，10 tests passed，0 failures/errors。`-X pycache_prefix={build}/pycache` 已同时用于 manifest 的 build 和 unit 命令；Harness 将缓存写入 `.rd-platform/build/python_expenses/pycache`。另以真实 UTF-8-SIG 文件执行 `category,amount,date` 加中文类别，CLI 退出 `0`，输出为 `{"categories":{"出行":"0.20","餐饮":"1.10"},"total":"1.30"}`。此处为开发者回归证据；独立重新测试仍为 `NOT_EXECUTED`。

## REV-V3-APP-002 / REV-V3-APP-003 修复证据

新增回归后，manifest unit 的 RED 真实退出 `1`：12 个测试中 2 个失败。`9999999999999999999999999999 + 2` 被默认 Decimal 28 位上下文静默表示成 `1.000000000000000000000000000E+28`；`1e1001` 未触发资源边界拒绝。该 RED 直接对应 `REV-V3-APP-002`。

修复后实际执行 `run_matrix(..., phases=('build', 'unit'))`：build 退出 `0`，unit 退出 `0`，14 tests passed，0 failures/errors，耗时 0.756s。build 和 unit 的实际 argv 均含 `-X pycache_prefix=D:\\codex-rd-platform\\.rd-platform\\build\\python_expenses/pycache`；构建缓存路径由 Harness 报告为 `.rd-platform/build/python_expenses/pycache`。`git diff --check -- examples/multistack/python_expenses docs/platform-v3/apps/python_expenses` 退出 `0`（仅有 Git 行尾转换警告）。这是开发者修复证据，不替代独立 QA 重测或独立 review。

这些是开发者自测证据，不是独立测试、代码审查、发布、人工验收或任一项目 Gate 的 `PASS`。

## 后续状态

独立黑盒测试曾实际执行并以 `FAIL` 结束（3 例中 2 例通过、1 例失败）：`tests/independent_multistack/test_python_expenses_blackbox.py` 的正向 fixture 将 `\\n` 写为字面反斜杠加 n，因此生成单行、非三列表头 CSV；CLI 按 `REQ-MATRIX-PY-01` 拒绝，输出 `error: CSV header must contain exactly date, category, amount`。该证据需要独立 Tester 修正其测试 fixture 后重跑；开发者不会为了接受非 CSV 的字面 `\\n` 而放宽格式验证。独立评审：`NOT_EXECUTED`。发布包、部署和人工验收：`NOT_EXECUTED`。

## Skill 可用性观察

`platform-orchestration` 的“先读 snapshot、以真实 Agent/run 记录阶段、开发者与独立角色分离”流程可直接执行：父协调者为该实际开发身份开启 implementation run，本文只记录实际命令与输出。当前 V2 `run` CLI 将一次命令同时 start/finish 阶段，因此对于已由协调者开启的 ACTIVE run，使用受控 `run.finish` 命令记录开发证据，而不能再次调用 `run` 创建重叠阶段。该限制未改变应用实现范围。
