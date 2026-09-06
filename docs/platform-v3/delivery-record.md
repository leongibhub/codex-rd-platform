# V3 本地源码交付记录

日期：2026-09-06。范围：`CR-V3-001`、`DES-V3-001`、`TASK-V3-001..004`。

## 已执行的 Git 交付

- 实施提交：`6665bc5a5c4c441b523f9249dd860b7695daec72`。
- 分支：`codex/platform-v3-lifecycle`；基线：`9655f33d645e2169d451d79f3667778733897390`。
- 授权目标：`https://github.com/leongibhub/codex-rd-platform.git`，用户已明确将此前“GitLab”目标澄清为此 GitHub 仓库。
- 实际执行 `git push -u origin codex/platform-v3-lifecycle` 成功；随后 `git ls-remote --heads origin codex/platform-v3-lifecycle` 返回上述 SHA。
- 未修改 main、未创建或合并 PR、未创建生产 Release；数据库、缓存、运行输出和 ZIP 不入 Git。
- 本记录随后以独立文档提交补充实施提交，不改变已验证产品源码。其最新提交号由 Git 历史确定，避免自引用提交 SHA。

## 完成情况

| 项目 | 实际结果 |
| --- | --- |
| 本轮 10 个 V3 实施任务 | DONE，各有独立 implementation/unit/integration/review 当前 4/4 检查；76 条真实历史 Run 元数据保留 |
| 冻结后回归 | Runtime 128 PASS；原平台 98 PASS；旧样例 19 PASS |
| 最后提示文案修改后的窄回归 | adapter/report 8 PASS；`node --check rd_platform/static/app.js` PASS；独立窄审查 APPROVED |
| 原平台校验 | 提交后 `validate_platform.py` PASS (TEMPLATE MODE)，Evaluated Gates: NONE，工作树干净 |
| Skill 格式校验 | `quick_validate.py .agents/skills/platform-orchestration` PASS |
| Skill 行为实战 | 五栈实际开发/独立测试/修复/复审；另有已有 Python 应用 verification-only 9 例 current PASS 和新版路由 GREEN，未重建应用 |
| 五项目模型迁移 | 原始来源缺失的 v1 保留；明确 adopt model v2、case v2 后重新执行，各声明 suite PASS |
| 本地源码归档 | 五个 `stack-package` 实际 PASS，ZIP/source/file SHA-256 已记录 |
| 浏览器 | Web 便签实际用户流 PASS；8020 看板显示真实任务、Gate 未决状态和新旧执行证据 |

核验索引：[范围化追踪](traceability.md)、[任务历史与五包摘要 JSON](evidence/final-local-validation.json)、[独立平台测试](independent-platform-tests.md)、[独立应用测试](independent-app-tests.md)、[实际生命周期测试](live-lifecycle-validation.md)、[浏览器记录](browser-validation.md)、[运行时审查](runtime-review.md)、[应用审查](app-review.md)。测试方法/断言数量、聚合 suite 数和生命周期 Case 数属于不同口径，不混合成“总用例覆盖率”。

## 如何使用

在此仓库的 Codex 任务中直接说：

> 使用 platform-orchestration，帮我开发一个……。先自行分析需求，普通细节自行决策，关键业务分歧再问我，并把实际 Agent 工作记录到看板。

从现有应用继续时说明应用目录和目标；Skill 要求先读取真实源码和项目状态，不重建已完成部分。完整命令与备份恢复见[使用指南](README.md)。

本次本机保留：看板 `http://127.0.0.1:8020/`；Web 便签 `http://127.0.0.1:8022/`。它们只是当前前台任务启动的本地进程，不是安装为自启动的系统服务。

## 未完成的最终愿景边界

后续说明：这是本轮基线 2d77904 时的历史未完成列表；用户要求后已继续实施 CR-V3-002。已补齐项目及实际验证请读取 [后续交付记录](completion-delivery.md)，不要将本节作为当前未完成清单。

这次完成的是宿主辅助平台与五栈工程验证，不是“所有目标环境、全部 NFR 和真实项目 G0→G11 都已验收”。

- 微信开发者工具/真机不可用，只有 Node 领域和 fake-wx Page adapter 结果。
- 默认未接入已认证人工审批提供者；不伪造真人确认，不强行通过 G9–G11。
- 容量目标、长时稳定性、跨浏览器/跨 OS 全面验证、生产部署/回滚及最终业务验收未执行。
- 五应用当前报告的 `recommend_release=false`、G0/G7 无决定保持不变；完整阶段/发布/回滚契约在隔离 synthetic fixture 中验证，不能冒充真实项目结项。
- Codex 宿主实际派发 Agent；Skill/Runtime 本身不提供无人值守云端模型调度。

上述未执行边界见[能力状态](capability-status.md)和[发布就绪性](release-readiness.md)。Git 推送成功仅证明源码交付，不推导生产发布或人工验收。
