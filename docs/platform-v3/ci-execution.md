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
