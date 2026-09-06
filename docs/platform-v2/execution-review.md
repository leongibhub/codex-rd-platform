# 执行边界独立审查

- 审查者：实际独立Agent `/root/v2_review_execution`。
- 范围：TASK-V2-004配置修复、TASK-V2-005命令执行器；只读检查及临时夹具窄复现。
- 首轮结论：FAIL / DO NOT APPROVE；P1两项、P2两项。基本7项runner单测不构成完整通过。

| ID | 等级 | 已观察问题 | 主责 |
| --- | --- | --- | --- |
| BUG-V2-003 | P1 | 父进程退出后后代仍存活：timeout0.2返回PASS，0.6秒后后代写入marker | runner |
| BUG-V2-004 | P1 | 输出截断跨secret时泄漏前缀；长度小于8的敏感值未脱敏 | runner |
| BUG-V2-005 | P2 | 无效UTF8解码后超过证据字节预算；高速输出先写入无界spool | runner |
| BUG-V2-006 | P2 | TOML多行description内假启动键被改写，真实键不变却成功 | config rewriter |

修复要求：Windows受控Job及无启动竞态、POSIX进程组约束；流式限量与脱敏；解析真实TOML词法位置和精确写后断言。修复者为 `/root/v2_execution_fixes`，不由审查者自修自签。最终复验/复审结果另记，不覆盖首轮失败历史。

审查转录不包含真实秘密或原始凭据；复现均用明确测试值。本记录不声明生产安全认证。
