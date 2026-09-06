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
- TASK-V3-011..014：真实 CI 暴露的 JSON 结构预算、Java 8 干净构建、Windows GNU 链接和跨 OS MCP 启动配置缺陷，逐项修复并独立重测、评审；保留失败历史，见 [CI 缺陷闭环](ci-execution.md)。
- TASK-V3-015：修复旧 Windows 安装器复制本机状态/缓存的风险；固定已检查的 Git 提交、精确公开模板例外、拒绝覆盖与链接路径，并对真实提交完成一次正常全新安装。初次真实安装的 false positive 和后续修复仍保留，见 [真实安装验证](install-real-validation.md)。

## 已观察事实

满容量读取基准：100 个项目、100000 工件版本、1000000 事件，129.7199 秒，数据库 294764544 字节，读取错误 0。批量 SQL 生成的合成数据不等于 Runtime 写入性能。独立 Tester 对终态摘要与数据库精确计数进行了复核；详见 [性能验证](performance-validation.md) 和 [独立 QA](completion-qa.md)。

Python 独立执行已得到 37/37 CURRENT/PASS，7/7 RTM COMPLETE。真实 Reviewer `/root/v3_python_gate_review` 已逐项检查并登记 G0–G8 的实际 `DECIDED/PASS/CURRENT`；G9–G11 仍 `NOT_EVALUATED`，`recommend_release=false`。finalize 实际退出 0，返回 `G0_G8_COMPLETE_G9_PENDING`。详见 [Python 独立评审](python-lifecycle/independent-review.md) 和[实际终态摘要](evidence/python-lifecycle-finalization.json)；不是以测试 PASS 代替 Gate，也没有代签人工验收。

独立审查已经触发真实 Runtime review FAIL → retry 新 attempt → 修复 → unit → integration → review。初始失败、脚本 fixture 错误和最终修复分别保留在 [平台审查](completion-review.md)、[独立 QA](completion-qa.md)、[导出 QA](project-export-qa.md) 和 [test-run QA](test-run-validation.md)，不删除历史让看板变绿。

## 当前质量结果

源码提交 `62c153e` 的最新本机 Runtime 回归：200 tests，199 PASS、1 平台条件 skip，0 FAIL，103.594 秒。上一修复提交 `ba17e35` 的 Windows 平台回归 115/115 PASS（包含 9 项真实临时克隆安装测试），105.712 秒；独立 V3 回归 59 tests，58 PASS、1 平台条件 skip，0 FAIL，51.664 秒。第三轮修复另有独立 20/20 专项回归和真实 WSL C++ 三阶段通过。旧任务看板示例回归 19/19 PASS；平台校验器曾实际执行 runtime health，结果为 `PASS (TEMPLATE MODE)`、`Evaluated Gates: NONE`，不是项目 Gate 通过。当前在线结果见 [CI 执行记录](ci-execution.md)。

平台项目 `project-908e903738184820b14264adac92adda` 的六个能力任务、四个 CI 修复任务及安装器任务均已经过实际 implementation/unit/integration/review，当前为 DONE；加上五个上轮任务共 16 个 DONE。下面是六个能力任务及安装器的真实独立 review Run；四个 CI 修复任务见 [CI 独立审查](ci-fix-review.md)。失败 attempt 和修复记录保留在原 Runtime。

| Task | 当前 attempt | 独立 review PASS Run |
| --- | ---: | --- |
| TASK-V3-005 | 2 | `run-bab9e70580c44cebbb25ad9d2a086a16` |
| TASK-V3-006 | 2 | `run-573ea0df5e8247aa91109d80a2791567` |
| TASK-V3-007 | 2 | `run-3a04b6b730d54b65b07248309e758eef` |
| TASK-V3-008 | 3 | `run-fc7d10f61ec844d58869734e26e019b4` |
| TASK-V3-009 | revision 2 / attempt 1 | `run-cf53be71a6e64fc7a3ed61c58c667d25` |
| TASK-V3-010 | 1 | `run-b81a6a129e2945eca9cb0791f13dc00e` |
| TASK-V3-015 | revision 3 / attempt 2 | `run-177f1e06e28745f1be954b63d9170efc` |

README 的最终测试脚本另通过独立 4/4 复核，临时浅克隆 fixture 不依赖宿主 origin URL 或本地远端分支引用。任务 DONE 表示上述本机模块质量闭环，不意味着 8 小时观察或人工验收已完成。

已实际提交并推送到 GitHub 的源码：`a55e3ce`（六项能力及双语指南）、`ba17e35`（首次 CI 修复）、`62c153e`（原生 Windows C++ 链接及跨 OS 测试输入修复）。首次和第二次 CI 均出现真实 FAIL，未覆盖或删除；第三次结果以 [CI 执行记录](ci-execution.md) 为准。没有合并 `main`、创建生产 Release 或部署到外部环境。

第三次 [GitHub Actions 34031461586](https://github.com/leongibhub/codex-rd-platform/actions/runs/34031461586) 已在 `62c153e` 源码上实际全部通过：Windows/Linux Runtime/platform 与 Windows/Linux 五应用声明阶段，4/4 jobs SUCCESS。README 后续执行审查另外发现 single-branch 续作、身份措辞和旧安装器复制问题；当时转入 Task009 revision 2 / Task015 补齐，未把该 CI 结论沿用到尚未提交的安装器修复。

后续 `c3eb271` 已实际提交/推送，其 [CI 34032544002](https://github.com/leongibhub/codex-rd-platform/actions/runs/34032544002) 也为 SUCCESS。但该提交在真实安装时被公开知识模板误拦截，不能把 CI 通过当作安装通过。修复 `527dae1` 已实际提交/推送，并在独立临时目录实际完成固定提交获取、正常 setup、新建 venv、依赖安装、pip check 和真实 MCP 健康检查，退出 0；对应 [CI 34032990521](https://github.com/leongibhub/codex-rd-platform/actions/runs/34032990521) 另行核验，最终结果见下方。安装器第三修订中的一次 QA CRLF/LF 夹具失败保留，修复夹具后重走完整质量链，不借用旧 PASS。

安装器最终独立 unit 12/12、integration 10/10、review 22/22 实际通过；Reviewer 另外只读复核真实安装目标，确认 exact HEAD、depth-one、无源 remote/状态库/私有文件、真实 venv 和 MCP 校验结果。README 新的 5 项独立检查包含真实 Git 三种起始状态及 tester 身份语义，不再只检查命令字符串存在。以上完成的是可验证的本机交付和文档路径，不批准生产发布或整套最终愿景。

最终代码 `527dae1` 的 [CI 34032990521](https://github.com/leongibhub/codex-rd-platform/actions/runs/34032990521) 随后已实际完成，4/4 jobs SUCCESS：Windows Runtime 200（1 skip）、platform 128、独立 V3 69、adapter 4；Ubuntu Runtime 200（5 skip）、platform 119（14 skip）、独立 V3 69（10 skip）、adapter 4，均无失败/错误；两 OS 的五应用声明阶段通过。准确范围见 [最终代码 CI 摘要](evidence/ci-validation-final-code.json)。后续提交只同步文档与事实索引，不把它们虚构为该次已完成 CI 的输入。

最终双语安装段还经过独立 Reviewer 的只读小范围复核，结论 scope PASS、无 P0–P2；README 合同 5/5 再次通过，当前平台校验也实际为 TEMPLATE PASS/MCP EXECUTED/Gates NONE。主安装路径仍为干净 clone、本仓 Git 身份配置及 setup；固定提交 helper 是有明确前提的可选路径，不能拿来搬迁私有本机状态。

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
