# V3 多技术栈应用独立测试

测试执行者：`/root/v3_qa_apps`（Runtime 角色 `tester`）。

范围：本记录基于 [多技术栈 Skill 实战验收](../superpowers/specs/2026-09-06-multistack-selftest.md) 及各应用已交付的规格/应用说明，在首次接触实现前建立。开发者声称、源代码结构和开发者测试不作为黑盒预期依据。测试数据均为本地合成数据。本文不是 Gate、发布、原生微信运行或人工验收结论。

## 方法与边界

- 先在 Runtime 以本人的真实 Tester 身份启动每个已就绪任务的 `unit`，实际执行 manifest 中的开发者单元命令；再仅在该命令实际通过后顺序启动 `integration`，执行独立、面向公共 CLI/业务模块接口的测试。
- 每个 `PASS` 都必须附有本次执行的命令、退出码与可观察断言。未执行阶段明确标注 `NOT_EXECUTED`；工具缺失使用 `NOT_AVAILABLE`。
- Web 仅由本测试验证可导入的业务模块。真实浏览器用户流程由父任务单独验证。
- 微信 Node 页面对 `wx` 使用本测试自建、显式注入的 stub；它不是微信原生运行，不能证明导入、真实 `Page`、真实存储、真机或发布。

## 风险驱动独立用例模型

| 用例 | 应用 / 关联需求 | 类型与风险 | 公共输入 / 可观察预期 | 执行状态 |
| --- | --- | --- | --- | --- |
| TC-IQA-CPP-01 | C++ / REQ-MATRIX-CPP-01,04 | CLI 集成、跨进程持久化 | 两次 `add` 后用新进程 `get`；数量为累加值 | PASS，EVD-IQA-CPP-004 |
| TC-IQA-CPP-02 | C++ / REQ-MATRIX-CPP-02,05 | 负向、失败写入 | 过量 `deduct`、负数、坏数据；非零退出且文件字节不变 | PASS，EVD-IQA-CPP-004 |
| TC-IQA-CPP-03 | C++ / REQ-MATRIX-CPP-03 | 功能 / 确定性 | 乱序 SKU 后 `list` 为词典序；缺失 SKU 非零 | PASS，EVD-IQA-CPP-004 |
| TC-IQA-PY-01 | Python / REQ-MATRIX-PY-01,02 | CLI 正向、编码与精度 | UTF-8 BOM、重排列的 CSV；JSON 类别词典序、`0.10 + 0.20 = "0.30"` | PASS，EVD-IQA-PY-003 |
| TC-IQA-PY-02 | Python / REQ-MATRIX-PY-03,04 | 边界 / 负向 | 空文件、仅表头、坏日期、负值、Infinity、字段数错误、缺失/额外参数；非零，stdout 为空 | PASS，EVD-IQA-PY-003 |
| TC-IQA-PY-03 | Python / REQ-MATRIX-PY-02 | 回归 / Decimal 精度 | 超长十进制数加 `0.2` | JSON 十进制文本精确，不转为浮点或科学计数 | PASS，EVD-IQA-PY-003 |
| TC-IQA-PY-04 | Python / REQ-MATRIX-PY-03,04 | 回归 / 资源与错误边界 | 有限但极端指数的 `1E+1000000` | 明确非零；stdout 无成功 JSON | PASS，EVD-IQA-PY-003 |
| TC-IQA-WEB-01 | Web / REQ-MATRIX-WEB-01..05 | 业务模块集成、状态恢复 | 经导出业务接口创建、更新、查询、删除与重新读取；存储状态符合行为且查询不改变集合 | PASS，EVD-IQA-WEB-003 |
| TC-IQA-WEB-02 | Web / REQ-MATRIX-WEB-01,05,06 | 边界、安全导向 | 空白/501 字符被拒绝；坏存储返回空集合；HTML 样字符串保持普通数据 | PASS，EVD-IQA-WEB-003 |
| TC-IQA-WEB-03 | Web / REQ-MATRIX-WEB-05 | 回归 / 可靠性 | storage `getItem` 抛错 | 读操作降级为空集合，不向调用方抛错 | PASS，EVD-IQA-WEB-003 |
| TC-IQA-JAVA-01 | Java / REQ-MATRIX-JAVA-01,02,05 | CLI 集成、时间边界 | 跨进程添加、相邻允许、同房重叠拒绝并字节不变；不同房允许 | PASS，EVD-IQA-JAVA-003 |
| TC-IQA-JAVA-02 | Java / REQ-MATRIX-JAVA-03,04,05 | 负向 / 数据保持 | 列表过滤与取消；未知 ID、坏时间、额外参数和坏文件非零且不写 | PASS，EVD-IQA-JAVA-003 |
| TC-IQA-WECHAT-01 | 微信 / REQ-MATRIX-WECHAT-002,003 | 业务模块集成、金额精度 | 页面 stub 输入 `0.10`、`0.20`；写入整数分，合计显示 `0.30` | PASS，EVD-IQA-WECHAT-003 |
| TC-IQA-WECHAT-02 | 微信 / REQ-MATRIX-WECHAT-002,004,005；NFR-001 | 负向 / 存储恢复 | 无效金额不写；删除目标后新 adapter 从同一 fake wx 恢复；坏存储降级为空 | PASS，EVD-IQA-WECHAT-003 |
| TC-IQA-WECHAT-03 | 微信 / NFR-MATRIX-WECHAT-001 | 回归 / 原子性 | 已有 `Number.MAX_SAFE_INTEGER` 分，再新增 `0.01` | 累计溢出报错且 fake wx 的持久化记录值不增加 | PASS，EVD-IQA-WECHAT-003（Node stub） |
| TC-IQA-WECHAT-04 | 微信 / REQ-MATRIX-WECHAT-001..005 | 原生兼容性 | 微信开发者工具导入、真实交互和存储 | NOT_AVAILABLE（当前环境未提供工具） |

## 执行记录

| 应用 | Runtime 任务 | 单元阶段 | 独立集成阶段 | 缺陷 |
| --- | --- | --- | --- | --- |
| `cpp_inventory` | `task-bee072b4c58e4cd99f5df51a484ba7cb` | PASS，EVD-IQA-CPP-003（attempt 2） | PASS，EVD-IQA-CPP-004（attempt 2） | BUG-QA-001 历史测试资产问题；Runtime `defect-e8a2783d6e5a41d79f93f91c745a93f5` 仍保留 |
| `python_expenses` | `task-ba16f26b15ca4110b71d69cb1f61db2f` | PASS，EVD-IQA-PY-003（attempt 2） | PASS，EVD-IQA-PY-003（attempt 2） | BUG-QA-002 已重测通过；Runtime `defect-b04196e559af4a17af3120185bd1c0e1` 仍保留 |
| `web_notes` | `task-b49068ef61e8478d9a97718c3769aeae` | PASS，EVD-IQA-WEB-003（attempt 2） | PASS，EVD-IQA-WEB-003（attempt 2；业务模块，浏览器由另一执行者负责） | BUG-MATRIX-WEB-001 已重测通过；Runtime `defect-fbb838210d954e11a02ab7c531748ce7` 仍保留 |
| `java_booking` | `task-040d30aa16f54e84afb74dae678450ac` | PASS，EVD-IQA-JAVA-003（attempt 2） | PASS，EVD-IQA-JAVA-003（attempt 2） | BUG-MATRIX-JAVA-001 已重测通过；Runtime `defect-0dbaae8a56774132b7a6438ab05756bf` 仍保留 |
| `wechat_expenses` | `task-6f889da4a2bc4c3e90aec0a83983edc1` | PASS，EVD-IQA-WECHAT-003（attempt 2） | PASS，EVD-IQA-WECHAT-003（显式 `wx` stub）; 原生 TC-IQA-WECHAT-04 NOT_AVAILABLE | BUG-MATRIX-WECHAT-001 已重测通过；Runtime `defect-2dce500f8c984e2d8c3e90efb8d19d93` 仍保留 |

### 已观察到的执行证据

| EVD | Runtime run / 命令 | 可观察结果 |
| --- | --- | --- |
| EVD-IQA-PY-001 | `run-679046b5fa9b41c9b8349f4b87b0ff4d`; `.venv\\Scripts\\python.exe -m unittest discover -s examples\\multistack\\python_expenses\\tests -v` | 退出码 0；9/9 通过。 |
| EVD-IQA-PY-002 | `run-550a33c9a740431da74c7bd76ec1464a`; `.venv\\Scripts\\python.exe -m unittest discover -s tests\\independent_multistack -p test_python_expenses_blackbox.py -v` | 退出码 1；3 例中 2 通过、1 失败。事后审查本 Tester 的 fixture 发现其把 `\\n` 写成字面量反斜线+n，形成单行而非有效 CSV；该证据不能证明产品违反 REQ-MATRIX-PY-01。fixture 已修正，旧失败保留，须在新 attempt 重测。 |
| EVD-IQA-CPP-001 | `run-4d585e877f5045beb537a4acda9a76f6`; `.venv\\Scripts\\python.exe -X utf8 examples\\multistack\\cpp_inventory\\verify.py --phase unit` | 退出码 0；输出 `5 tests passed`。另以同一 driver `--phase build` 实际构建了公共 CLI，退出码 0。 |
| EVD-IQA-CPP-002 | `run-c687c89e44024f01a115d85e12d8095d`; `.venv\\Scripts\\python.exe -m unittest discover -s tests\\independent_multistack -p test_cpp_inventory_blackbox.py -v` | 退出码 1；2 例中拒绝写入例通过，但本 Tester 将预期换行误写为字面量反斜线+n。实际 CLI 返回正确 `7` 加换行；不是 REQ-MATRIX-CPP 产品失败。已修正脚本，必须在新 attempt 重新执行所有阶段。 |
| EVD-IQA-CPP-003 | `run-d35ef0e24f874ce3b7e2b5bc633005f0`; `.venv\\Scripts\\python.exe -X utf8 examples\\multistack\\cpp_inventory\\verify.py --phase unit` | attempt 2，退出码 0；输出 `5 tests passed`。 |
| EVD-IQA-CPP-004 | `run-b089d11e2294469b9aacc3bfc6ab807c`; `.venv\\Scripts\\python.exe -m unittest discover -s tests\\independent_multistack -p test_cpp_inventory_blackbox.py -v` | attempt 2，退出码 0；2/2 通过。公共 CLI 的跨进程累加/词典序/缺失查询、过量扣减/非法数量/坏持久化字节保持均有实际断言。 |
| EVD-IQA-WEB-001 | `run-836f353e89d34535a420c4426f2f5f5a`; `node --test examples\\multistack\\web_notes\\tests\\notes.test.js` | 退出码 0；6/6 通过。 |
| EVD-IQA-WEB-002 | `run-181c413e446d4b679f2dcdca46bf2baf`; `node --test tests\\independent_multistack\\web_notes_business.test.mjs` | 退出码 0；2/2 通过：创建、编辑、删除、搜索不改存储、坏数据降级、HTML-like 字符串作为数据。真实 DOM 文字渲染不由此证明。 |
| EVD-IQA-JAVA-001 | `run-474cd4179f7f44d4b6f496dbbadcaf3e`; `C:\\Program Files\\Java\\jdk-1.8\\bin\\java.exe -cp .rd-platform\\build\\java_booking\\classes booking.BookingStoreTest .rd-platform\\build\\java_booking\\unit-data` | 退出码 0；`BookingStoreTest: 18 assertions passed`。此前以 manifest 的 JDK 8 `javac` argv 实际编译至 `.rd-platform\\build\\java_booking\\classes`，退出码 0。 |
| EVD-IQA-JAVA-002 | `run-d7e1661cabb64f1a9494726324c4ec10`; `.venv\\Scripts\\python.exe -m unittest discover -s tests\\independent_multistack -p test_java_booking_blackbox.py -v` | 退出码 0；2/2 通过：跨进程读写、相邻允许、重叠/坏命令字节不写、取消与列表。 |
| EVD-IQA-WECHAT-001 | `run-ba071e63e0c7456c9c930147d8429a57`; `node --test examples\\multistack\\wechat_expenses\\test\\expense-domain.test.js` | 退出码 0；3/3 通过。 |
| EVD-IQA-WECHAT-002 | `run-a480879ff1b049a2bf812be8bdf53d32`; `node --test tests\\independent_multistack\\wechat_expenses_page_stub.test.js` | 退出码 0；2/2 通过：stub 存储为分、恢复、无效输入不写、删除和坏存储降级。此为 Node 替身而非原生微信结果。 |
| EVD-IQA-PY-003 | `run-0dd01aac97944e779caf055248bf38da`（unit）和 `run-6da5d6f6d15f4f2482098d8e667dce6d`（独立 integration）；分别执行开发 `unittest discover -s examples\\multistack\\python_expenses\\tests -v` 与独立 `unittest discover -s tests\\independent_multistack -p test_python_expenses_blackbox.py -v` | attempt 2；均退出码 0。开发单元 14/14；独立公共 CLI 5/5，包括真实 BOM/重排列、精确长 Decimal、极端指数拒绝和既有负向集合。 |
| EVD-IQA-WEB-003 | `run-665ff6ed9a654572bf6712e2c15a3042`（unit）和 `run-9129e4c728224844a41751f1902dd358`（独立 integration）；分别执行开发 Node suite 与 `node --test tests\\independent_multistack\\web_notes_business.test.mjs` | attempt 2；均退出码 0。开发单元 8/8；独立业务模块 3/3，包含抛错的 storage 读取降级。真实浏览器 DOM/E2E 仍不由此证明。 |
| EVD-IQA-JAVA-003 | `run-4c78c26fa12f46bf879f35107b5b029b`（unit）和 `run-bf0329990253491685738be675d47782`（独立 integration）；JDK 8 `javac` 实编译后，执行 `BookingStoreTest` 与独立公共 CLI unittest | attempt 2；均退出码 0。开发单元报告 18 assertions；独立 CLI 2/2 通过。 |
| EVD-IQA-WECHAT-003 | `run-1003cafadd20428a85a6530193040bf3`（unit）和 `run-3e28eef6e3074b1a8b4070b06e0ef660`（独立 integration）；开发 domain Node suite 与显式 fake `wx` 页面测试 | attempt 2；均退出码 0。开发单元 4/4；独立 stub 3/3，确认累计分值溢出不新增持久化记录。非原生微信结果。 |

## 缺陷

| BUG | 关联需求 / 用例 | 状态与证据 | 主责 |
| --- | --- | --- | --- |
| BUG-QA-002 | TC-IQA-PY-01 | OPEN（QA 测试资产）。EVD-IQA-PY-002 的 CSV fixture 使用字面量 `\\n`，不满足测试预置；已修正全部 fixture 转义，旧 Runtime `defect-b04196e559af4a17af3120185bd1c0e1` 保留。 | `/root/v3_qa_apps` |
| BUG-QA-001 | TC-IQA-CPP-01 | RETESTED PASS（QA 测试资产）。EVD-IQA-CPP-002 的预期字符串错误，不能归责 C++ 产品；修正后 EVD-IQA-CPP-003/004 全部通过。旧 Runtime `defect-e8a2783d6e5a41d79f93f91c745a93f5` 仍保留，尚未由 review 阶段关闭。 | `/root/v3_qa_apps` |
| BUG-MATRIX-WEB-001 | REQ-MATRIX-WEB-05；TC-IQA-WEB-03 | RETESTED PASS。独立复审的 storage accessor 异常处理发现记录在 Runtime `defect-fbb838210d954e11a02ab7c531748ce7`；attempt 2 以 EVD-IQA-WEB-003 验证读取抛错降级为空集合。Runtime 历史 defect 未由本 Tester 关闭。 | Web 应用开发者 |
| BUG-MATRIX-JAVA-001 | REQ-MATRIX-JAVA-06；TC-IQA-JAVA-01,02 | RETESTED PASS。独立复审的 Java 测试运行时可移植性发现记录在 Runtime `defect-0dbaae8a56774132b7a6438ab05756bf`；attempt 2 实际 JDK 8 编译、单元及独立 CLI 见 EVD-IQA-JAVA-003。Runtime 历史 defect 未由本 Tester 关闭。 | Java 应用开发者 |
| BUG-MATRIX-WECHAT-001 | NFR-MATRIX-WECHAT-001；TC-IQA-WECHAT-03 | RETESTED PASS。独立复审的累计溢出污染持久化发现记录在 Runtime `defect-2dce500f8c984e2d8c3e90efb8d19d93`；attempt 2 的 EVD-IQA-WECHAT-003 确认 fake wx 未新增记录。Runtime 历史 defect 未由本 Tester 关闭。 | 微信应用开发者 |

## 工具/Skill 观察

首次启动 Python 单元阶段时，`rd_platform run` 在创建 run 前报 `ModuleNotFoundError: rd_platform.lifecycle`；后续验证该依赖文件已出现，且任务仍为 `READY/unit`、本 Tester 没有 run 记录，故重新启动才取得 EVD-IQA-PY-001。该瞬时运行库依赖状态不构成任一应用测试结果。除该观察外，本轮没有发现可归因于应用 Skill 的新行为问题。

后续仅以本节补充的实际命令、退出码、断言输出和 Runtime run ID 更新结果；任何失败将以 Runtime `FAIL` 打开真实 BUG，再交由开发者修复。
