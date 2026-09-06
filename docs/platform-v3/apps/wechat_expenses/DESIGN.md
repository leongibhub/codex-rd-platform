# 微信本地记账本设计

`DES-MATRIX-WECHAT-001` · 对应 `REQ-MATRIX-WECHAT-001` 至 `005`

## 组件与数据流

```
WXML events -> Page adapter -> expense-domain -> records in Page data -> WXML
                         |                    |
                         +-> wx storage adapter+
```

- `lib/expense-domain.js` 是无 `wx`、无 UI 的 CommonJS 领域模块：解析金额、构造/验证记录、追加、删除、合计与显示格式化。
- `pages/index/index.js` 只将原生 `Page` 生命周期和事件绑定到领域模块；它从全局 `wx` 建立存储适配器。导出的 `createPageDefinition(wxApi)` 是 Node 测试入口，生产注册调用 `Page(createPageDefinition(wx))`。
- 存储键固定为 `wechat-expenses.records.v1`。每次新增或删除先在内存中构造候选集合，并先计算合计、格式化完整视图；仅当这些不变量全部成立后调用存储写入。读取失败、非数组或任意记录无效时使用空数组，防止坏存储进入 UI；若有效单条记录的累计值仍溢出，`onLoad` 显示可恢复的空态和错误，且不写回或覆盖原始存储。

## 数据契约

```json
{"id":"r_...","amountCents":1234,"category":"餐饮","createdAt":"2026-09-06T00:00:00.000Z"}
```

金额文本遵循 `^[0-9]+(\\.[0-9]{1,2})?$`，且必须大于零。界面从 `data-*` 取得删除 ID，领域层仍拒绝未知 ID。

## API 依据与验证范围

计划使用微信小程序的 `Page`、`wx.getStorageSync` 和 `wx.setStorageSync` API。已尝试访问微信官方开发文档页面（2026-09-06），当前浏览通道返回不可重试错误，故未从其内容推导额外行为；实现仅采用本任务明确要求的同步读写形式。实际 API 导入/执行尚未验证。
