# 微信本地记账本实现与开发者验证

`TASK-V3-003` · `REQ-MATRIX-WECHAT` · 开发者实现记录

## 实现摘要

- 新增可由微信开发者工具导入的原生小程序工程：`app.json`、`app.wxss`、首页 `Page`、WXML 和 WXSS；`project.config.json` 有效地声明小程序根目录和编译类型，故意未填入 AppID。
- 领域模块将金额转换为整数分，拒绝零、负数、科学计数、超过两位小数和不安全金额；所有合计也保持整数分。
- 页面适配器只经 `wx.getStorageSync`/`wx.setStorageSync` 使用本地存储。Node 测试由明确的 `fakeWx` 传入 `createPageDefinition`，不存在模拟全局 `wx` 或把替身结果冒充原生执行。
- 提供 schema v1 `manifest.json`；命令均是 argv 数组，未使用 shell 字符串或本机绝对路径。

## 结果

| EVD | 命令 | 结果 |
| --- | --- | --- |
| EVD-MATRIX-WECHAT-DEV-RED | `node --test examples/multistack/wechat_expenses/test/*.test.js`（实现前） | `FAIL`：两个测试文件均因目标模块缺失而失败。这是预期 RED 基线。 |
| EVD-MATRIX-WECHAT-DEV-001 | `node --test examples/multistack/wechat_expenses/test/*.test.js` | `PASS`：6/6 Node 测试通过（TC-MATRIX-WECHAT-001 至 006）。 |
| EVD-MATRIX-WECHAT-DEV-002 | `node --check examples/multistack/wechat_expenses/lib/expense-domain.js`；`node --check examples/multistack/wechat_expenses/pages/index/index.js`；`git diff --check -- examples/multistack/wechat_expenses docs/platform-v3/apps/wechat_expenses` | `PASS`：语法与补丁空白检查通过。 |
| EVD-MATRIX-WECHAT-DEV-003 | `node --test examples/multistack/wechat_expenses/test/expense-domain.test.js examples/multistack/wechat_expenses/test/page-adapter.test.js`（REV-V3-APP-001 修复） | `PASS`：8/8 Node 测试通过；TC-MATRIX-WECHAT-008 先以 6/8 失败建立 RED，再验证 `MAX_SAFE_INTEGER + 0.01` 不写入、正常重载，及已损坏超额存储可恢复显示且原值不被覆盖。 |

## 限制与后续独立验证

`TC-MATRIX-WECHAT-007` 是 `NOT_AVAILABLE`：当前环境没有微信开发者工具，因此未验证工程导入、原生 `Page` 注册、真实 `wx` 存储、真机运行或发布。这些限制不由 Node 结果覆盖。独立 Tester 应在可用原生工具中执行 TC-007；独立 Reviewer 仍未执行。

## 追踪

`REQ-MATRIX-WECHAT` → `REQ-MATRIX-WECHAT-001` 至 `005`（SPEC）→ `DES-MATRIX-WECHAT-001`（DESIGN）→ `TASK-V3-003` → `TC-MATRIX-WECHAT-001` 至 `007`（RISK-TEST-MODEL）→ `EVD-MATRIX-WECHAT-DEV-RED` / `001` / `002`（本文件）。

`REV-V3-APP-001` → `NFR-MATRIX-WECHAT-001` → `TC-MATRIX-WECHAT-008` → `EVD-MATRIX-WECHAT-DEV-003`。开发者修复不关闭独立 Review 发现；需要独立复测和复审。
