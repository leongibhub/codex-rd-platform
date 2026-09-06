# V2 本地运行基础交付报告

- Change：CR-V2-001；设计：DES-V2-001；任务：TASK-V2-001–005。
- 日期：2026-09-06；环境：Windows、仓库Python虚拟环境、SQLite、本机浏览器。
- 范围：可见的本地宿主协作运行基础，不是整套自主SDLC平台的最终验收。
- Git基线：a2c766cd9aa411f0798fa4e1adb6f759f0ba849c；开发分支：codex/platform-v2-runtime。
- 用户确认目的地：https://github.com/leongibhub/codex-rd-platform 。仅提交开发分支，不合并main。

## 本次交付

保留现有Agent职责、生命周期文档、MCP和校验器，新增持久化任务/运行/事件/缺陷内核、中文实时看板、可信CLI命令执行器、需求初模及草案导出、模块测试报告和宿主编排Skill。内核在独立测试和review均通过之前不允许模块DONE；修改、重试和取消不会复用过期证据。

看板使用实际宿主Agent身份和运行记录。当前对接是由Codex宿主调度并回写，不是后台模型守护服务；仅登记名称并不会启动模型。若记录始于执行中途，输入/证据明确注明检查点，不伪造原始开始时间。

## 最终回归证据：189项通过

以下三组互不重复，均为当前实现后的真实执行，不把历史失败删除或计入最终PASS。

| 范围 | 命令（均使用 `.venv/Scripts/python.exe -X utf8`） | 结果 |
| --- | --- | --- |
| V2运行时 | `-m unittest discover -s tests/runtime -t . -q` | 72 tests，18.919s，OK，exit 0 |
| 原平台无安装回归及配置修复 | `-m unittest tests.platform.test_company_context tests.platform.test_governance_contract tests.platform.test_manifest_contract tests.platform.test_validator_contract tests.platform.test_mcp_stdio tests.platform.test_config_rewrite -q` | 98 tests，37.793s，OK，exit 0 |
| 小应用单元和HTTP黑盒 | `-m unittest examples.task_board.test_unit examples.task_board.test_blackbox -q` | 19 tests，11.330s，OK，exit 0 |

原始结束摘要：

```text
Ran 72 tests in 18.919s
OK

Ran 98 tests in 37.793s
OK

Ran 19 tests in 11.330s
OK
```

98项中配置拒绝用例有预期的 `rewritten config does not match the exact intended launch change` stderr；最终测试进程仍exit 0。另执行 `scripts/validate_platform.py`，结果 `PLATFORM VALIDATION: PASS (TEMPLATE MODE)`、`Evaluated Gates: NONE`、`RUNTIME CHECK: EXECUTED`，工作树dirty提示符合提交前事实。`node --check`、Skill quick_validate及diff whitespace检查通过。

独立QA另外真实执行小应用11项单元/8项黑盒、执行器配置26项/系统8项。这些与上述回归重叠，**不再累加总数**。详细责任人、Run ID及输出见[独立测试](independent-test.md)、[小应用黑盒](example-blackbox.md)。

## 需求—实现—验证索引

这是本次维护增量的追踪索引，不填充或冒称激活原模板项目RTM。

| 需求 | 实现 | 自动验证 |
| --- | --- | --- |
| REQ-V2-001、002 | runtime/store | test_runtime、test_system：恢复、事务、并发、依赖 |
| REQ-V2-003、004 | runtime/reporting | 独立角色、四阶段、FAIL/retry、过期证据、SKIPPED不PASS |
| REQ-V2-005 | runtime | 控制事件、阶段分配、版本与传递依赖失效 |
| REQ-V2-006 | web/static/cli | test_web、test_system及browser-verification真实UI记录 |
| REQ-V2-007 | discovery | test_discovery：事实/推断、必答校验、DRAFT/PARTIAL导出 |
| REQ-V2-008 | runner/_process_tree/reporting | test_runner、test_reporting及真实命令到报告集成 |
| REQ-V2-009 | web/cli/store | 严格JSON、Origin/Host、体积/超时、输出转义、无HTTP执行 |
| REQ-V2-010 | write_local_config/README | test_config_rewrite及98项原平台回归 |

审查证据见[应用与内核审查](application-review.md)、[执行器首轮失败](execution-review.md)、[修复证据](execution-fix-report.md)、[执行器复审](execution-rereview.md)。历史FAIL保留，最终结论以各报告最新有署名的检查点为准。未执行的测试绝不换算为PASS。

## Self-Test结论与限制

真实小应用从独立SPEC开始，经历开发、单元、HTTP黑盒、review失败、修复、再次独立测试。它证明当前模块工作流可用，而不是已经完整跑通用户要求的Idea到Release/Close全部阶段。

最终实际Run记录：小应用attempt 3在`run-a9d2ae752d8549efbad49e49febe60f6`独立review PASS后DONE/4，两条历史缺陷CLOSED；执行器修复attempt 2在`run-15569ccf32c14ac598a3c922da4b1370`独立review PASS后DONE/4。报告仍返回`NO_RELEASE_EVIDENCE`和`PARTIAL`完整追踪状态，未把模块完成冒充产品发布。

- 当前模块回归结论：PASS；开发分支可供本机试用。
- 生产发布建议：DO_NOT_RELEASE。X-Role样例不是认证；平台只面向可信本地宿主，不可直接公网开放。
- 人工验收、生产部署、正式发布/结项：NOT_EXECUTED或PENDING，未创建虚假Gate。
- 9项安装测试本轮未执行，避免安装修改；POSIX进程树实机、跨浏览器、负载极限、长稳、安全认证、真实灾难恢复未执行。
- 运行库 `.rd-platform/` 不入Git，避免上传个人任务和执行输出。使用说明及备份恢复见[README](README.md)。

## 后续路线（尚未实施）

1. 把需求、设计、代码、测试模型、用例、缺陷、发布建成统一版本化实体及完整RTM关系；保留原G0–G11并提供显式迁移。
2. 接入宿主执行适配器、能力权限、租约/取消与恢复，让状态自动来自真实Agent生命周期。
3. 从风险/功能树生成测试模型，再生成结构化可自动化用例；增加环境隔离与缺陷分类/定向回归策略。
4. 增加可授权部署、回滚、正式报告和验收材料；长耗时或外部环境操作必须有预算与授权边界。
5. 用第二个真实项目完整执行Idea→Release→Close，再评估全生命周期平台验收和知识复用效果。
