# 微信本地记账本风险驱动测试模型

开发者测试（Node）和未来独立测试必须分离。本文件是测试设计，不是执行结果。

| TC | 需求 | 类型 / 风险 | 输入 | 步骤 | 预期 | 自动化方式 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-MATRIX-WECHAT-001 | 002,003 | 单元 / 浮点舍入 | `0.10`,`0.20` | 解析、追加、合计 | 合计 `30` 分、显示 `0.30` | Node domain unit |
| TC-MATRIX-WECHAT-002 | 002 | 单元负向 / 坏账目写入 | 空、`0`、负数、三位小数、科学计数 | 尝试追加 | 抛错；原集合不变 | Node domain unit |
| TC-MATRIX-WECHAT-003 | 002,004 | 单元 / 数据完整性 | 有效记录、重复 ID、未知删除 ID | 追加/删除 | 重复拒绝；未知删除不变 | Node domain unit |
| TC-MATRIX-WECHAT-004 | 005 | 模块集成 / `wx` 隔离 | 明确 fake `wx` | 新建 page、输入、提交 | fake storage 写整数分记录；不需要全局 `wx` | Node Page adapter |
| TC-MATRIX-WECHAT-005 | 003,004 | 模块集成 / 持久化 | fake storage 已有记录 | 新 Page `onLoad` | 列表和合计恢复 | Node Page adapter |
| TC-MATRIX-WECHAT-006 | 005 | 模块集成负向 / 损坏存储 | 非数组/坏记录 | 新 Page `onLoad` | 空态且不崩溃 | Node Page adapter |
| TC-MATRIX-WECHAT-007 | 001-004 | 原生手工 / 导入和交互漂移 | 微信开发者工具 | 导入、输入、删除、重启 | 原生 UI 结果符合规格 | `NOT_AVAILABLE`：工具缺失 |
| TC-MATRIX-WECHAT-008 | 002-004,NFR-001 | 单元和模块集成 / 累计溢出破坏持久化 | 已存 `MAX_SAFE_INTEGER` 分；新增 `0.01`；以及已损坏的超额集合 | 新增、重载 | 候选被拒绝且原存储逐值不变；重载不抛出；已损坏存储仅显示可恢复空态与错误、不覆盖原数据 | Node domain + explicit fake `wx` Page adapter |

### 测试证据状态

开发者 Node 单元/适配器测试：`NOT_EXECUTED`（实现后执行）。原生开发者工具与真机：`NOT_AVAILABLE`，不得用 fake `wx` 替代。
