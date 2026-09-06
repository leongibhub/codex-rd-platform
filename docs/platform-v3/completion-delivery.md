# V3 后续交付记录

变更：CR-V3-002；基线：2d77904；分支：codex/platform-v3-lifecycle。

用户指出此前“未完成的最终愿景边界”中存在可以继续完成的工程工作。本轮实际继续实现，并将中文 README.md 与独立英文 README.en.md 作为同等完整的使用指南。本记录持续更新；模块通过不等于所有外部验收完成。

## 本轮交付范围

- TASK-V3-005：受预算限制的真实 SQLite 容量/长稳工具，独立输出、进度/终态、延迟和资源样本、setup/采样中断处理。
- TASK-V3-006：Windows/Linux CI、真实 Java 8 基线、C++ 原生 Linux/Windows 编译器路径。
- TASK-V3-007：全量报告与只读项目导出；超过 500 条无遗漏；外部执行证据变动后撤销当前 PASS，保留历史观察。
- TASK-V3-008：对既有 Python 应用进行需求级 Self-Test；不重建应用。4 REQ、3 NFR、37 个实际用例与独立评审/阶段推进。
- TASK-V3-009：双语安装、Skill 提示、续作、运行台、控制、CLI、五栈测试、证据、备份和故障说明。
- TASK-V3-010：基线 Case → 固定 argv → 真实执行 → 证据登记/缺陷；版本/来源失效和中断不成为 PASS；目录句柄避免 cwd 与结果路径的链接竞争。

## 已观察事实

满容量读取基准：100 个项目、100000 工件版本、1000000 事件，129.7199 秒，数据库 294764544 字节，读取错误 0。批量 SQL 生成的合成数据不等于 Runtime 写入性能。独立 Tester 对终态摘要与数据库精确计数进行了复核；详见 [性能验证](performance-validation.md) 和 [独立 QA](completion-qa.md)。

Python 独立执行已得到 37/37 CURRENT/PASS，7/7 RTM COMPLETE。真实 Reviewer `/root/v3_python_gate_review` 已逐项检查并登记 G0–G8 的实际 `DECIDED/PASS/CURRENT`；G9–G11 仍 `NOT_EVALUATED`，`recommend_release=false`。finalize 实际退出 0，返回 `G0_G8_COMPLETE_G9_PENDING`。详见 [Python 独立评审](python-lifecycle/independent-review.md) 和[实际终态摘要](evidence/python-lifecycle-finalization.json)；不是以测试 PASS 代替 Gate，也没有代签人工验收。

独立审查已经触发真实 Runtime review FAIL → retry 新 attempt → 修复 → unit → integration → review。初始失败、脚本 fixture 错误和最终修复分别保留在 [平台审查](completion-review.md)、[独立 QA](completion-qa.md)、[导出 QA](project-export-qa.md) 和 [test-run QA](test-run-validation.md)，不删除历史让看板变绿。

## 当前质量结果

最终本机 Runtime 回归：179 tests，178 PASS、1 平台条件 skip，0 FAIL；独立 V3 回归：46 tests，45 PASS、1 平台条件 skip，0 FAIL。Windows 平台回归 114/114 PASS（包含 9 项真实临时克隆安装测试），163.606 秒；旧任务看板示例回归 19/19 PASS；平台校验器为 `PASS (TEMPLATE MODE)`、实际 runtime health 已执行、`Evaluated Gates: NONE`。CI 在线结果仍待本轮 push 后核验。

平台项目 `project-908e903738184820b14264adac92adda` 的六个新任务当前均为 DONE、4/4 质量检查通过。下面是各自的真实独立 review Run；失败 attempt 和修复记录保留在原 Runtime。

| Task | 当前 attempt | 独立 review PASS Run |
| --- | ---: | --- |
| TASK-V3-005 | 2 | `run-bab9e70580c44cebbb25ad9d2a086a16` |
| TASK-V3-006 | 2 | `run-573ea0df5e8247aa91109d80a2791567` |
| TASK-V3-007 | 2 | `run-3a04b6b730d54b65b07248309e758eef` |
| TASK-V3-008 | 3 | `run-fc7d10f61ec844d58869734e26e019b4` |
| TASK-V3-009 | 1 | `run-e8ff4871967445a9bc5c22e158b4136f` |
| TASK-V3-010 | 1 | `run-b81a6a129e2945eca9cb0791f13dc00e` |

README 的最终测试脚本另通过独立 4/4 复核，临时浅克隆 fixture 不依赖宿主 origin URL 或本地远端分支引用。Git 提交/推送与 GitHub Actions 结论将在实际发生后补入，不把生成 workflow 视作在线执行。任务 DONE 表示上述本机模块质量闭环，不意味着 8 小时观察、云端 CI 或人工验收已完成。

提交检查未发现数据库、压缩包、`.env`、cache 或常见凭据格式。普通 `git diff --check` 会报告 QA Markdown 的有意双空格换行，以及摘要锁定的独立评审文件末尾空行；保持不可变证据原字节，用仅排除这两种空白规则的检查验证其余格式，未为格式清理修改证据摘要。

## 8 小时真实读路径观察：RUNNING

- 输出目录：`.rd-platform/benchmark-soak-8h-20260906-1`（Git 忽略）。
- 容量准备：`perf-694ad2c9fbec4fb29fe2de8ae911ae42`，已真实 PASS，131.7802 秒。
- 长稳 Run：`soak-9241634446774e1291126d1cc1c2a53b`，目标 28800 秒、间隔 5 秒。
- 运行代码 SHA256：`E482F1E2DD6A5A7AB42736AE227DB56B8B5D12F2D6C1D5FA1F3293F78BEDBC9A`。开始后为未来 setup 中断加入了修复，已运行进程不假称被热更新。
- 同 run checkpoint 是当前观察，terminal 才是终态；没有 terminal 不宣称 8h PASS。机器退出/休眠/进程结束会影响实际验证时长和结论。
- 当前线程已建立每 30 分钟检查的跟进，仅在完成、失败或需要操作时通知，并补记实际结果。

此验证仅覆盖 SQLite 公开只读查询，不能推导全系统稳定性、写入一致性、Web 用户流、生产负载或客户验收。

## 仍须分别完成的事项

代码能力与环境事实不混淆：云端模型常驻调度服务、真实认证审批适配器、通用环境部署/回滚执行器仍是具体工程待办，不能仅称为环境限制；当前受支持的执行方式是 Codex 宿主实际派发 Agent。微信 IDE/真机及真实生产目标需要相应环境；G9–G11需要具体项目的真实验收、批准和交付事实。这些没有被本轮本机模块测试代替。

上轮 [delivery-record.md](delivery-record.md) 是历史快照。新的已完成能力与验证应读取本记录和上述报告，不能继续把已执行的容量基准、完整报告/导出、原生 Linux C++ 路径列成完全未做。
