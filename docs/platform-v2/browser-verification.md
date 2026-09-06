# 浏览器可见性验收记录

- Evidence ID: EVD-V2-UI-001
- Evidence Status: OBSERVED
- 日期：2026-09-06
- 目标：http://127.0.0.1:8020/；当前主机已有运行服务。
- 方法：实际浏览器可访问性树/DOM交互，非截图目测判PASS；本次为一次性探索验收，不声称已是稳定CI浏览器回归。

## 实际观察

1. 页面显示实际例子项目/任务、宿主worker身份、implementation→unit→integration的真实交接及3/4检查；review启动后显示review:ACTIVE，不提前DONE。
2. 初次创建“浏览器验收专用项目”时，数据库写入成功，但前端出现 `Cannot read properties of null (reading 'reset')`。登记BUG-V2-002，主责frontend，原因是await后event.currentTarget已失效。
3. 开发者在await前保存form引用后，重新加载并创建“浏览器控件验收（未执行代码）”，创建成功、表单复位、无该错误，任务READY/0/4。
4. 在同一实际任务上通过UI选择pause，界面显示PAUSED；选择resume后显示READY。两次均保留0/4，没有把控制成功计为代码/测试通过。
5. Agent表展示实际 `/root/v2_example_app`、`/root/v2_independent_qa` 的角色/状态/心跳；运行详情可展开summary/evidence/输出。

## 数据与边界

- 控件验收项目与真实小应用演练项目分开；控件任务没有执行代码，不用于产品Gate。
- 测试记录保留于忽略Git的本机SQLite；没有删除用户项目/源代码或变更外部系统。
- 浏览器页面已标记为交付页保留，服务只监听loopback。
- 此记录不覆盖多浏览器、移动端、屏幕阅读器完整兼容性或生产部署。
- BUG-V2-002：RESOLVED，待最终独立Review；没有伪造人工验收。

## 最终界面复验（2026-09-06 16:31–16:35）

- 重新加载实际服务后，首屏为概览和 Agent 表，项目任务与事件随后展示；创建/控制区默认折叠。
- 在“项目名称”填入不提交的验收文字，随后快照时间从16:33:02推进至16:33:56，输入仍保留。清空该测试输入后收起控制区，未创建额外项目。
- 未点击刷新也观察到运行数10→16→17，真实独立测试交接持续出现；READY/ACTIVE/FAILED和历史review:FAIL均按事实展示。
- AVAILABLE Agent不再因历史心跳过期被误标失联；最终截图观察到两名真实Reviewer处于BUSY、指向不同实际任务。
- 此复验是OBSERVED浏览器证据，不扩展为完整兼容性、无障碍或自动化CI认证。
