# Web 样例真实浏览器验证

- 执行者：主控 `/root`；这是开发者之外的宿主浏览器操作，不替代独立 QA Agent 的报告。
- 日期：2026-09-06；地址：`http://127.0.0.1:8022/`；Codex 内置浏览器。
- 启动：`.venv\Scripts\python.exe -m http.server 8022 --bind 127.0.0.1 --directory examples/multistack/web_notes`。
- 测试对象：Web notes；合成笔记 `QA-20260906-离线笔记`，没有真实用户数据。

| ID | 需求/风险 | 实际操作与观察 | 结果 |
| --- | --- | --- | --- |
| TC-V3-BROWSER-001 | REQ-MATRIX-WEB 创建/注入 | 输入标题及 `<img src=x onerror=alert(1)> 中文正文`，点击 Add note；页面文章中以普通段落文字出现，没有图片元素或脚本对话框 | PASS |
| TC-V3-BROWSER-002 | REQ-MATRIX-WEB 持久化 | 刷新页面；标题和原正文仍可见 | PASS |
| TC-V3-BROWSER-003 | REQ-MATRIX-WEB 编辑 | 点击 Edit，正文改为“已编辑的中文笔记”，保存后显示新正文及 Note updated | PASS |
| TC-V3-BROWSER-004 | REQ-MATRIX-WEB 搜索 | 搜索“不存在的QA关键词”显示 No notes found；搜索“中文”只显示测试笔记 | PASS |
| TC-V3-BROWSER-005 | REQ-MATRIX-WEB 删除 | 点击 Delete、清空查询、刷新；No notes found，测试笔记已删除 | PASS |

证据为本次 CUA DOM/可访问性快照与实际点击结果，不是生成的 Playwright 脚本。页面存储不可用修复有单独 Node 回归；本轮浏览器处于存储可用环境，不宣称浏览器级故障注入。没有执行跨浏览器、真机微信、8–72 小时稳定性或生产发布。

## 平台看板浏览器检查

在 `http://127.0.0.1:8023/` 实际打开 V3 页面，选择真实 `Skill实战 · python_expenses`。
观察到 G0 与 G7 为 IN_REVIEW、其余 Gate 为 NOT_EVALUATED、0/12 决策；显示真实 5 工件、1 用例及新执行记录。五应用任务显示 DONE 4/4，平台修复任务仍显示 ACTIVE，历史 FAIL 可见。

发现并修复阅读问题：展开“真实测试执行”可看到 `execution-2b06444e58d94f61a7366be592238e47`，下一次自动刷新使详情关闭，ID 从 DOM 消失（RED）。修复为有展开证据/控制表单时暂缓自动刷新，页面明确提示；手动刷新仍可用。GREEN 浏览器复查单独记录，不把语法检查算浏览器操作。

GREEN：重新加载修复后的 JS、选择同一项目、展开同一执行，跨过自动刷新间隔后 CUA DOM 仍包含该执行 ID，且出现“正在查看展开内容，自动刷新暂缓”提示；两个实际断言均为 true。独立 Reviewer 另行检查监听器、固定选择器、textContent 和手动刷新路径并批准该窄改动。
# 最终交付端口复核（2026-09-06）

代码冻结后仅停止了经 PID/CommandLine 核实的本项目旧 8020 与临时 8023 看板，保留 SQLite 数据；用最新代码重新启动 `python -X utf8 -m rd_platform serve` 于 `127.0.0.1:8020`。在内置浏览器新标签中看到本轮 10 个任务 DONE 和全部 4/4 质量检查。

选中 `Skill实战 · python_expenses`，页面显示 6 个版本化产物、1 个模型、1 个用例、2 个实际执行；展开后同时看到历史 v1 `execution-2b06444e58d94f61a7366be592238e47` 与最新 v2 `execution-4738d4b39f5541a5bc1dcf886cc6b4a3`。G0/G7 仍 IN_REVIEW、未作出结论，未因重测 PASS 自动改变 Gate。最终标签已留给用户查看。

旧 V2 未初始化 lifecycle 的项目选择后会显示“生命周期未就绪”，这表示该项目尚无 V3 实例，不代表 V2 任务丢失。未创建假的生命周期数据填满界面。
