# Python CSV 费用分析工具规格

状态：DRAFT；需求追踪：`REQ-MATRIX-PY`；任务追踪：`TASK-V3-003`。

## 接口

入口：`examples/multistack/python_expenses/expense_analyzer.py`。

```text
python expense_analyzer.py INPUT.csv
```

成功时退出码为 `0`，stdout 是一行 UTF-8 JSON：

```json
{"categories":{"food":"0.30","transport":"2.00"},"total":"2.30"}
```

`categories` 按类别字典序输出。金额是十进制字符串；该表示保留 `Decimal` 的值而不让 JSON 浮点读取破坏精度。失败时 stdout 为空，stderr 以 `error:` 开头并说明原因，退出码为 `1`；命令参数错误由 `argparse` 返回 `2`。

为给本地 CLI 明确资源边界，每个金额最多 1,000 个有效位，`Decimal` 指数必须在 -1,000 至 1,000，且 CSV 最多 100,000 条费用行。超出任一边界会以输入错误退出，绝不返回舍入后的成功金额。

## 功能需求和验收

| ID | 要求 | 可验证验收 |
| --- | --- | --- |
| REQ-MATRIX-PY-01 | 读取 UTF-8 CSV 的 `date`、`category`、`amount` | 接受 UTF-8（含 BOM）输入及任意列顺序；首行必须恰有这三列且每行恰有三个字段。 |
| REQ-MATRIX-PY-02 | 按类别与总额输出 JSON | 对有效且在资源边界内的多行数据输出类别合计与总额；类别排序稳定，合计使用显式精度的 Decimal，不静默舍入。 |
| REQ-MATRIX-PY-03 | 拒绝无效业务数据 | 空输入、只有表头、坏/空日期、空类别、空/无效金额、负值和非有限值均明确失败。 |
| REQ-MATRIX-PY-04 | 明确命令行失败语义 | 不存在文件和无效输入返回非零且不输出成功 JSON；缺少或多余路径参数返回 argparse 的非零结果。 |

## 非目标

本示例没有独立黑盒测试、人工验收、发布、部署或长期运行结论；它们由后续独立角色和平台交付材料分别记录。
