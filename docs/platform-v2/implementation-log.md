# V2 实施台账

- Change ID: CR-V2-001
- 来源：现状审计后用户要求直接修改并提交GitLab。
- 影响：新增本地运行面/看板/需求发现/报告/执行适配器；保留原template、MCP、校验契约。
- 实施授权：OBSERVED（本会话用户明确请求）；人工最终验收：PENDING。
- 初始HEAD：a2c766cd9aa411f0798fa4e1adb6f759f0ba849c。
- 远端：用户已补充并确认 https://github.com/leongibhub/codex-rd-platform ，因此推送现有GitHub origin，不新建GitLab或替换远端。
- 决定：按独立文件所有权并行（用户AGENTS要求）；保持现有开发目录，使用新开发分支，避免迁走用户正在查看的仓库。
- 下列为中间检查点，最终结果见末尾，保留历史等待/失败状态。
- TASK-V2-001：已实现，主审7项发现已修复，13项开发回归通过；待完整独立Review。
- TASK-V2-002：已实现，HTTP/CLI/表单问题修复；实际浏览器创建/暂停/恢复可见；待完整独立Review。
- TASK-V2-003：已实现，10项回归；模块质量与发布证据分开；待完整独立Review。
- TASK-V2-004：普通配置回归通过，独立Review发现多行TOML定位问题，修复中。
- TASK-V2-005：执行器基本7项回归通过，但独立Review发现进程树/脱敏/预算问题，不能据此放行；专门修复中。
- 独立系统测试：8项通过；全量复跑发现Windows子进程编码差异，CLI已统一UTF8，待最终全量复验。
- 小应用演练：真实developer实现；独立tester单元8/8与SPEC-only黑盒6/6通过；review活动中，尚未DONE。
- 本轮范围：V2本地可运行基础；任意应用完全自主开发和长周期NFR仍需后续阶段，不能由演练冒充。

## 最终本机验证检查点

- TASK-V2-001–005：本轮实现、独立测试及代码复审通过。最终回归72项V2 + 98项原平台/配置 + 19项小应用 = 189项，全部exit 0；详见delivery-report.md。
- 两名独立Reviewer最终均给出限定范围PASS；首轮和残留FAIL保留在application-review.md和execution-rereview.md。
- 小应用：attempt 3，11项单元 + 8项独立黑盒，最终review run-a9d2ae752d8549efbad49e49febe60f6 PASS；任务DONE/4，两条真实历史缺陷由内核在新轮独立review通过后关闭。
- 执行器修复：attempt 2，26项单元/配置 + 8项独立系统测试，最终review run-15569ccf32c14ac598a3c922da4b1370 PASS；任务DONE/4。先前测试脚本编码FAIL及BUG-V2-015保留。
- 浏览器专用控件任务仍READY/0，不是假业务成果，不能为了全绿而改DONE。
- 报告实际返回MODULE_QUALITY PASS，但traceability PARTIAL、release NO_RELEASE_EVIDENCE、deployment/human_acceptance NOT_EXECUTED；此边界符合当前范围。
- 用户授权源代码提交与远端推送，不等于授权上线或最终验收。Git提交/推送结果以实际Git记录为准，不在这里提前签成功。

## Git交付证据

- 实现提交：89261ebaf361554439622c0e377ddaedefeb22f1。
- 已执行 `git push -u origin codex/platform-v2-runtime`，exit 0。
- `git ls-remote --heads origin refs/heads/codex/platform-v2-runtime` 返回相同完整SHA；当时工作树干净。
- 提交后再次执行validator为TEMPLATE MODE PASS、Evaluated Gates NONE、RUNTIME CHECK EXECUTED，无dirty提示。
- 此记录作为后续文档提交保存，不改写已经验证的实现提交；未创建PR、合并main或生产发布。
