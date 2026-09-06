# 本次要求与验收基线

Document State：BASELINED；不是 APPROVED。四条 REQ 保留原始 DRAFT 规格 ID；本次只将其作为固定测试输入。三个 NFR 从既有规格约束拆分，属于用户授权核对范围内的当前解释，不声称获得历史批准。原来源为 `docs/platform-v3/apps/python_expenses/specification.md` 和 `initial-model.md`。

| ID | 可观察验收 | 输入与边界 |
| --- | --- | --- |
| REQ-MATRIX-PY-01 | 接受有效 UTF-8/BOM、任意三列顺序；错误表头或字段数失败 | date/category/amount 恰三列；真实中文、真实 BOM；缺/多/重复表头、缺/多字段、非法 UTF-8 |
| REQ-MATRIX-PY-02 | 有效数据输出排序类别和总额；所有金额为精确十进制字符串 | 0.10+0.20=0.30；跨类别总额2.30；零值；长整数加2不舍入 |
| REQ-MATRIX-PY-03 | 空文件/仅表头、坏或空日期、空类别、坏金额、负值和非有限值退出1 | 不返回部分成功 JSON；NaN、sNaN、Infinity、-Infinity 均拒绝 |
| REQ-MATRIX-PY-04 | 数据/文件错误退出1，stdout空且stderr以error:开头；缺/多参数退出2 | 不存在文件、无效CSV、缺参数、多参数 |
| NFR-MATRIX-PY-001 | 已支持范围内分类和总額精确，JSON金额类型为字符串 | 原REQ-02质量属性拆分；0.10+0.20、超过28位整数相加、跨类别 |
| NFR-MATRIX-PY-002 | 最多1000有效位、指数[-1000,1000]、100000行；上下限内精确接受，超限拒绝 | 1000/1001位、±指数1000/1001、100000/100001行；没有新增耗时或内存SLA |
| NFR-MATRIX-PY-003 | 成功和失败CLI均不改输入；自测缓存/输出留在指定构建目录，原源码文件清单和摘要不变 | 真实SHA-256前后对比；只证明本机观察，不声称完成网络隔离监控 |

接口：`python expense_analyzer.py INPUT.csv`；成功 stdout 是一行 JSON，stderr空，退出0；日期严格YYYY-MM-DD并为真实日历日期。金额字符串未规定禁止科学计数法，测试不得额外加入该限制。

数据与安全：只生成显式标识的合成输入，不使用客户账单、账户、凭据或生产路径。输出JSON不携带凭据；失败不输出部分成功对象。本工具无用户鉴权界面，测试不宣称身份认证。

中央RTM：隔离运行的 lifecycle 数据库才是本项目的实际状态源；仓库模板RTM不填充。脚本导出 requirement-coverage.json，保留每条REQ/NFR对应的case、具体版本、execution和evidence；某个相邻用例通过不能填补未执行需求。

需求审查：需要真实独立 Reviewer 对以上来源、解释、遗漏/歧义和验收可测性给出记录。review-contract.md 规定输入和证据格式；没有记录时为PENDING。
