# Self-Test 小应用：本地任务 API

- Record ID: DES-EXAMPLE-001
- 类型：平台开发演练，不是客户产品或人工验收。
- 背景：验证真实Agent实现、独立测试/审查与平台事件链，不使用商业数据或外部服务。
- Scope：本机单进程HTTP API、SQLite任务持久化、viewer只读、editor可增改删。
- 非目标：真实登录/多租户、互联网部署、压力极限、72小时稳定性、安全认证。

## REQ-EXAMPLE-001 接口

`examples.task_board.app.create_server(db_path, port=0)`返回绑定127.0.0.1的ThreadingHTTPServer；脚本可CLI启动。GET /health -> 200 {"status":"ok"}。

GET /tasks -> 200 {"tasks":[{"id":int,"title":str,"done":bool}]}；POST /tasks {"title":str} -> 201 task；PATCH /tasks/{id} {"done":bool} -> 200 task；DELETE /tasks/{id} -> 204。

GET允许viewer；POST/PATCH/DELETE必须请求头X-Role: editor，否则403。此为仅用于测试角色边界的受信header演示，绝不能称为真实身份认证。

## REQ-EXAMPLE-002 边界

title去首尾空白后1..120字符，缺失/null/非字符串/空/超长400；done仅bool，整数0/1或字符串拒绝400；未知id404，未知path404；无效JSON和非object400；最大body16KiB，超出413。参数化SQL，动态输出JSON。

## REQ-EXAMPLE-003 持久与恢复

每个请求独立SQLite事务与连接，重开服务同DB任务保留；删除/修改只影响目标id；不读取外部文件。server主程序端口可选，默认8030；不附任何实际秘密。

## 验收与测试模型

风险：越权写、无效输入入库、资源不存在误成功、持久化丢失。Developer写unit测试；独立tester仅根据本SPEC通过HTTP测正常/异常/边界/权限/恢复，不从实现推导预期；独立reviewer审源码。模块完成不代表release，批准/发布/结项为演练外人工条件。
