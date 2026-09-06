# 当前架构与详细设计观察

Document State：BASELINED（本次源码观察）。这是已有实现的当前描述，不是声称本次重新设计或开发应用。原始来源为原应用design.md及当前源码，实际路径/提交/blob/SHA-256由prepare写入source-baseline.json。

HLD/系统架构：一个本地Python标准库进程接收CSV文件路径，读取文件，完整验证输入，再一次性输出JSON；失败统一写stderr。外部只有文件系统、stdout/stderr和进程退出码。无数据库、服务端或外部账号集成。

组件与LLD：argparse入口处理路径数；main以utf-8-sig打开文件；analyze_csv由csv.DictReader解析；_validate_header核对列名；_parse_date验证正则格式及日历日期；_parse_amount验证Decimal/有限性/非负值/有效位和指数。所有行通过后，根据指数跨度和行数计算显式Decimal上下文精度，按类别汇总并排序；json_result将金额转换为字符串，再输出一次JSON。

数据设计：日期仅为输入合法性检查；category去首尾空白后作为键；amount为Decimal；JSON键为categories和total。CSV缺/多字段明确失败，不做静默丢弃或自动修复。输出不强制货币/小数位/禁止科学计数，避免引入未授权语义。

部署/故障设计：在已具备的本机Python运行原CLI；本次不安装依赖或部署服务。可读失败包括不存在文件、编码/CSV/业务错误和命令参数错误；无合法输入时不返回成功JSON。资源上限来自原规格，测试覆盖阈值而不定义性能SLA。

安全与隔离：harness使用argv数组和shell=False，输入为自有目录的合成数据；禁止把应用目录作为输出目录。禁止将任意用户shell文本当命令执行。构建缓存显式位于隔离build/pycache；应用文件读取前后比较摘要。该执行器不是恶意程序沙箱，也未验证网络隔离。

ADR-PLC-001：继承现有源码与Git提交，记录EXISTING_SOURCE_BASELINE，不用空壳或新演示替代。ADR-PLC-002：用公开Runtime API保存版本化事实，真实Tester执行，真实Reviewer决定；脚本没有生成审批的能力。ADR-PLC-003：原DRAFT语义在本次自测中固定为BASELINED输入，明确区分当前解释与人类批准。

架构审查：独立Reviewer需要核对当前函数、边界、错误路径、资源约束与规格一致，并核对harness只操作所属目录。该事实未登记前为PENDING。
