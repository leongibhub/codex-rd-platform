# GitHub Actions 实际执行与缺陷闭环

变更 CR-V3-002；不是发布或人类验收记录。

## 首次真实运行

- 已推送源码：`a55e3ce21907d25e64bde5fbac5e188b81e8d892`，分支 `codex/platform-v3-lifecycle`。
- 实际 [GitHub Actions run 34029576291](https://github.com/leongibhub/codex-rd-platform/actions/runs/34029576291)，2026-09-06T11:12:36Z 创建。
- 首次 multistack 作业使用真实 Python 3.13、Node 22、Temurin JDK 8；不是仅解析 YAML。修复后的两个 job 都显式配置同一工具基线。

| Bug | 实际失败 | 归因与修复任务 | 当前验证状态 |
| --- | --- | --- | --- |
| BUG-CI-001 | Ubuntu Runtime `test_deep_host_json_is_value_error_without_write`：5000 层 JSON 未抛 ValueError；179 tests，1 failure、4 skips | Store 依赖 Python 编码器的递归阈值，跨平台不一致；TASK-V3-011 明确结构预算 | 修复与独立重测中，未关闭 |
| BUG-CI-002 | Ubuntu Java build exit 2：`javac: directory not found: .../classes` | JDK 8 的 `-d` 根目录必须存在；已有本地 build cache 掩盖干净构建缺陷；TASK-V3-012 | 修复与全新工作区重测中，未关闭 |
| BUG-CI-003 | Windows C++ build PASS，但执行 unit 返回 `3221225785` / `0xC0000139` | 原生程序的 GNU DLL 解析不匹配待在线验证；同时原工具探测对 Windows native C++ 误报不可用；TASK-V3-013 | 修复与独立重测中，未关闭 |
| BUG-CI-004 | Windows Runtime 179 tests（1 skip）PASS，随后 platform 114 tests 有 4 FAIL：MCP 配置仍指向原机器 `D:/codex-rd-platform`，不在 CI checkout 的 `.venv` 内 | CI 需真实 repo venv 与配置重写；重写器此前固定 Windows 路径，TASK-V3-014 同步补齐 native POSIX 路径，保留严格 containment | 修复与独立重测中，未关闭 |

原始失败 job：Linux Runtime `101476522763`、Linux multistack `101476522773`、Windows multistack `101476522626`、Windows Runtime/platform `101476522725`。四个 job 最终均为 FAILURE。Linux C++ build/unit/integration 和 Python build/unit 已实际 PASS；失败后没有运行的阶段不记为 PASS。CI 上传了真实失败日志，未通过 retry/skip/continue-on-error 消除失败。

## 独立性与任务交接

| Task | Runtime task ID | Developer | Tester | Reviewer |
| --- | --- | --- | --- | --- |
| TASK-V3-011 | `task-53affd29dde44db7bd0f82ca99673706` | `/root/v3_lifecycle` | `/root/v3_qa_platform` | `/root/v3_review_runtime` |
| TASK-V3-012 | `task-9fe93a6e2e9e484a8db6c886854ce134` | `/root/v3_skill_forward` | `/root/v3_qa_apps` | `/root/v3_review_runtime` |
| TASK-V3-013 | `task-ef5124d4909940758962ca113a8854b4` | `/root/v3_models` | `/root/v3_qa_apps` | `/root/v3_review_runtime` |
| TASK-V3-014 | `task-a6e58b30639347709ac8067ecb9a3fcb` | `/root/v3_query` | `/root/v3_qa_platform` | `/root/v3_review_runtime` |

修复候选的 TASK011/012/014 已完成独立本机测试和评审；TASK013 的独立 OS 测试输入已修订，当前要求各 CI runner 真实验证本 OS 的 JAVA_HOME 路径，不要求原生 Windows CI 先安装 WSL。它通过 public modify 成为 revision 2，旧 WSL 验证没有被抹去或冒充新输入证据。revision 2 的独立 unit 18/18 和 integration 2/2 已实际 PASS，等待其独立评审。

另保留两个 TEST_SCRIPT 失败：TASK012 首次 unit `run-3bc7d50bf08f44ceb9578409b206da7d` 为隐藏 Windows 进程中中文 `mklink` 输出错误解码，并非 Java 产品缺陷或已证实的 Mock 干扰；TASK014 首次 integration `run-db0d478ee2e44510bd341eaefe6d02cc` 为 Tester 新夹具 SyntaxError、产品断言未执行。两者均正常 retry，重新从 implementation、unit、integration 到 review；未把先前 PASS 直接复制到新 attempt。

首次运行记录永久保留。只有实际修复提交、独立复核和新 CI 结果均已发生后，才能补记当前通过并关闭对应 Bug。将既有应用 manifest/源码纳入本次修复会产生新的源摘要；历史五应用执行结果仍是旧摘要的观察，不能自动沿用为当前证据。

## 第二轮：保留未解决问题

实际 [run 34030786796](https://github.com/leongibhub/codex-rd-platform/actions/runs/34030786796) 对应修复提交 `ba17e3524c41c75b17219b4a7c71a6d2b4e35631`。

- Ubuntu multistack job `101479775168`：SUCCESS，五应用声明阶段均真实执行；Java 8 从干净目录构建问题已通过在线复验。
- Ubuntu Runtime 198 tests：PASS，5 个 OS 条件 skip；MCP 的 repo-local POSIX 配置和 stdio health 未失败。随后平台 106 tests 有 1 ERROR、2 skips：测试脚本模拟 WSL 时仍对真实 Linux root 做 Windows 盘符映射。修复该测试输入，不修改或跳过产品断言。
- Windows multistack job `101479775294`：GNU DLL 目录配置步骤 PASS，但 C++ unit 仍为同一个 `0xC0000139`。仅调整 PATH 没有消除问题，BUG-CI-003 未关闭。
- Windows Runtime/platform job `101479775360`：SUCCESS，2026-09-06T11:46:02Z 完成；真实 repo-local venv、配置重写和 MCP health 已通过在线复验。
- TASK013 因真实在线失败重新修改为 revision 3：原生 Windows 两个 C++ 程序静态链接 `libstdc++`/`libgcc`，避免这两个运行库受其他 PATH 项的 DLL 影响；不修改 Linux/WSL 链接方式，也不声称已查明具体冲突 DLL。

当前 Windows 本机完整回归为 Runtime 198 tests（197 PASS、1 skip）、平台 115/115 PASS、独立 V3 59 tests（58 PASS、1 skip）。这些本机结果不代替第三轮 hosted CI。

revision 3 的独立 unit `run-aca565e9486d425b8091808dddcbbec2` 为 20/20 PASS；public C++ CLI integration `run-f57cbdee42a142c8a2f2bd8bf87c14b4` 为 build PASS、unit 5/5、integration 3/3，实际使用 WSL。独立 review `run-f61445255fd3489f9c8c4cb7419c1ea7` PASS，模块登记 DONE；hosted Windows 原生复验仍待第三轮 CI，不以模块状态替代。

## 第三轮：四作业全部通过

实际 [run 34031461586](https://github.com/leongibhub/codex-rd-platform/actions/runs/34031461586) 对应源码 `62c153e8a14425ce4aa3146519129521ded25af5`，最终 `completed / success`。观察来自 GitHub Jobs API 和真实 job 日志；归档摘要见 [ci-validation.json](evidence/ci-validation.json)。未提交或后续变更不继承本次通过。

| 作业 | 实际结果 | 观察范围 |
| --- | --- | --- |
| Ubuntu multistack `101481628280` | SUCCESS，11:52:38Z 完成 | 五应用 manifest 声明阶段；C++ unit 5、integration 3 |
| Windows multistack `101481628347` | SUCCESS，11:53:22Z 完成 | 原生 Windows GNU C++ 实际运行成功；五应用声明阶段 |
| Ubuntu Runtime/platform `101481628451` | SUCCESS，11:56:49Z 完成 | Runtime 200（5 skip）、platform 106（2 skip）、独立 V3 59、adapter blackbox 4；无失败或错误 |
| Windows Runtime/platform `101481628416` | SUCCESS，12:01:46Z 完成 | Runtime 200（1 skip）、platform 115、独立 V3 59、adapter blackbox 4；无失败或错误 |

以上时间均为 2026-09-06 UTC。BUG-CI-001..004 已有实际修复提交、独立复核及新在线回归，可在本次限定范围关闭；第一、二轮失败完整保留。第三轮原生 Windows C++ 的 `0xC0000139` 不再复现，但不据此声称已经定位某个具体冲突 DLL。

CI 使用真实 Python 3.13、Node 22 和 Temurin JDK 8。Python manifest 仅 build/unit，Web 仅 Node unit，微信是 Node domain/fake-wx unit/integration；它们不构成缺失集成阶段、真实浏览器、微信 IDE/真机、生产部署或人工验收的通过证据。不同 OS 的测试集及 skip 条件不同，不把矩阵测试计数相加为唯一业务 Case 总数。

## README 与安装器修复后的最终代码验证

`c3eb271` 的 [run 34032544002](https://github.com/leongibhub/codex-rd-platform/actions/runs/34032544002) 实际 SUCCESS，但真实安装仍发现公共知识模板误拦截。该发现进入 BUG-INSTALL-002，不能用该次 CI 关闭安装缺陷。其后修复为 `527dae1b7f75d6b526682d1c5a6407c1b3fc6a53`，并取得 [正常完整安装 PASS](install-real-validation.md) 以及新的独立质量链；QA CRLF/LF 夹具 FAIL/重试仍保留。

最终代码 [run 34032990521](https://github.com/leongibhub/codex-rd-platform/actions/runs/34032990521) 对应 `527dae1`，4/4 作业 SUCCESS，2026-09-06T12:32:02Z 为最终成功状态。实际 Jobs API 和 job 日志摘要见 [ci-validation-final-code.json](evidence/ci-validation-final-code.json)。

| 平台 | Runtime | Platform | Independent V3 | Adapter black-box |
| --- | --- | --- | --- | --- |
| Windows | 200 tests，1 skip，0 fail/error | 128/128 PASS | 69/69 PASS | 4/4 PASS |
| Ubuntu | 200 tests，5 skips，0 fail/error | 119 tests，14 skips，0 fail/error | 69 tests，10 skips，0 fail/error | 4/4 PASS |

Windows 专用安装器/链接测试在 Ubuntu 标注 skip，不冒充执行；Windows job 实际执行这些用例。两 OS 的五应用声明阶段也均实际通过。后续仅 README/报告等文档提交以本段明确的代码 SHA 为验证基准，文档自身另做链接/CLI/使用步骤检查，不声称未来提交已经包含在该 CI 中。
