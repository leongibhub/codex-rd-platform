# 多技术栈 Skill 实战验收

CR-V3-001；用户要求全部继续实现、无需普通问题确认，并以主流技术栈真实应用验证Skill。此文件为验收基线，不是人工最终验收。

## 五个独立的小型应用

| ID | 粗需求 | 最小可运行产品和验收 |
| --- | --- | --- |
| REQ-MATRIX-CPP | C++做一个库存工具 | CLI增减库存、按SKU查询、列表、文件持久化；非负整数库存，缺货扣减失败且不写，坏数据拒绝；重新进程读取仍一致。实际编译及运行。 |
| REQ-MATRIX-PY | Python做一个CSV费用分析工具 | CLI读取date/category/amount的UTF8 CSV，按类汇总和总额JSON；Decimal精确计算、空输入/坏日期/负值/无穷数拒绝；给出明确非0退出。 |
| REQ-MATRIX-WEB | Web做一个离线便签应用 | 浏览器新增、编辑、删除、搜索，localStorage持久化，空白/长度限制，内容安全渲染；Node测试业务模块，实际浏览器做用户流程。 |
| REQ-MATRIX-JAVA | Java做一个会议室预约工具 | CLI新增预约、取消、列表、文件持久化；同一房间时间区间重叠拒绝，相邻允许，错误输入不写；javac真实编译及子进程测试。 |
| REQ-MATRIX-WECHAT | 微信小程序做一个本地记账本 | 原生app.json/WXML/WXSS/Page，新增金额分类、列表、合计、删除、wx存储恢复；业务模块Node测试，wx接口仅测试替身且明确标注；官方开发者工具能导入，缺AppID/真机不得宣称发布成功。 |

每个应用仅使用合成验收数据，无外部账号、付费服务、生产接入。选择标准库/原生实现以测试语言适配，不为框架数量而添加依赖。应用目录 examples/multistack/{cpp_inventory,python_expenses,web_notes,java_booking,wechat_expenses}。

## 同一个Skill，独立执行

每个执行者必须实际读取platform-orchestration Skill和原始idea，自行形成初模、领域假设、需求/验收、设计与风险驱动测试模型，保存在docs的对应应用目录。上述最小范围是统一的评估边界，不给预制实现或预期代码。

先设计测试点再写用例；每例含ID、需求、类型、风险、输入、步骤、预期、自动化方式。开发者单元与独立黑盒分开；Reviewer不由开发者冒充。使用当前Runtime记录真实宿主Agent身份/任务/阶段/结果。技术栈工具缺失是NOT_AVAILABLE，不是PASS。

每个应用提供标准manifest.json：schema_version=1，id，stack，requirements数组，commands对象（build/unit/integration均为argv列表，可缺未就绪阶段），native_validation字符串说明，entrypoint字符串；argv支持{python}/{node}/{java}/{javac}/{cxx}/{root}/{app}/{build}占位符。禁止shell字符串，编译产物只能写{build}（位于.rd-platform/build下），不入Git。

源码完整、构建可重放、真实测试结果、独立review、发布包和已知限制必须分别交付。原生微信运行验证、真机、外部发布与长稳不以Node或本地模拟替代。
