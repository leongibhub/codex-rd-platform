# Python CSV 费用分析工具测试模型

状态：DRAFT；先于实现；需求：`REQ-MATRIX-PY-01` 至 `REQ-MATRIX-PY-04`；任务：`TASK-V3-003`。

开发者单元测试只验证模块和 CLI 的确定行为；独立 Tester 后续另行编写黑盒测试，不能以本文件或开发者测试代替。

| ID | 需求 | 类型 / 风险 | 输入和步骤 | 预期 | 自动化方式 |
| --- | --- | --- | --- | --- | --- |
| TC-MATRIX-PY-001 | 01, 02 | 正向 / 基本汇总 | 读取两类四行 UTF-8 CSV | 类别合计、总额和类别顺序正确 | `unittest` 纯函数 |
| TC-MATRIX-PY-002 | 02 | 边界 / 二进制浮点误差 | `0.10`、`0.20` | 总额为字符串 `0.30` | `unittest` 纯函数 |
| TC-MATRIX-PY-003 | 01 | 兼容 / UTF-8 BOM 与列顺序 | 含 BOM、重排列名的有效 CSV | 正常读取和汇总 | 临时文件 + CLI 子进程 |
| TC-MATRIX-PY-004 | 03 | 负向 / 无可分析数据 | 空文件与仅表头文件 | 明确失败 | 临时文件 + CLI 子进程 |
| TC-MATRIX-PY-005 | 03 | 参数化负向 / 日期 | 空、格式错、不存在的日历日期 | 明确失败 | `unittest` 纯函数 |
| TC-MATRIX-PY-006 | 03 | 参数化负向 / Decimal | 空、非数字、负数、NaN、sNaN、Infinity、-Infinity | 明确失败 | `unittest` 纯函数 |
| TC-MATRIX-PY-007 | 01, 03 | 负向 / CSV 结构 | 缺列、额外列、缺字段或多字段、空类别 | 明确失败 | `unittest` 纯函数 |
| TC-MATRIX-PY-008 | 04 | 端到端负向 / 失败输出 | 不存在文件和无效数据执行 CLI | 非零、stderr 有 `error:`、stdout 空 | CLI 子进程 |
| TC-MATRIX-PY-009 | 04 | 端到端负向 / 参数 | 缺少或附加路径参数执行 CLI | `argparse` 非零且无成功 JSON | CLI 子进程 |
| TC-MATRIX-PY-010 | 01, 02 | 回归 / QA 失败归因 | UTF-8 BOM 的 `category,amount,date` 与中文类别 | 退出 0，精确类别和总额 JSON | 临时文件 + CLI 子进程 |
| TC-MATRIX-PY-011 | 02 | 回归 / 默认 Decimal 上下文 | `9999999999999999999999999999 + 2` | 精确结果 `10000000000000000000000000001`，不舍入 | `unittest` 纯函数 |
| TC-MATRIX-PY-012 | 02, 03 | 边界 / Decimal 资源 | 1,000/1,001 有效位与指数 1,000/1,001 | 边界内精确接受；超限明确拒绝 | `unittest` 纯函数 |

执行记录将在实现后以真实命令、测试数量、退出码和输出摘要补充到 `implementation.md`；在此之前为 `NOT_EXECUTED`。
