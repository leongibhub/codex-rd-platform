# TASK-V3-009 README 独立 QA

执行者：`/root/v3_qa_apps`（independent Tester）  
日期：2026-09-06  
范围：`README.md` 与 `README.en.md` 的可执行文档契约、公开 CLI 路由可发现性、分支/依赖路径一致性，以及本地宿主/原生能力边界。本文不是在新机器执行全局 setup、fresh-clone E2E、浏览器/原生微信验收、CI 在线运行或后台模型服务验证。

## 风险模型和方法

测试依据 `TASK-V3-009` 的中英文可执行使用说明目标、`NFR-V3-004`（本地受信任 CLI/安全边界）和 `NFR-V3-005`（可审计事实而非文档推断）。测试资产为 [test_readme_contract.py](../../tests/platform/test_readme_contract.py)，不改 README、Runtime、setup 或任何全局配置。

| 用例 | 类型 / 风险 | 步骤与预期 | 实际结果 | 状态 |
| --- | --- | --- | --- | --- |
| TC-V3-README-001 | DOCUMENTATION / 断链导致使用者无法到达声明材料 | 解析中英文 README 中所有相对 Markdown 链接（跳过 URL、邮件和纯 anchor），以仓库根目录解析 | 两份 README 的本地链接均解析为存在文件 | PASS |
| TC-V3-README-002 | CLI CONTRACT / 文档路由已删除或参数不可发现 | 运行真实 `python -m rd_platform --help`；对 `lifecycle-report`、`project-export`、`test-run` 分别运行 `--help` | 顶层实际包含 snapshot、lifecycle、collection、report/export、test-run、stack-probe、run；子命令显示 `--project-id`、`--output-dir`、`--case-version` 等承诺参数 | PASS |
| TC-V3-README-003 | COMPATIBILITY / clone 分支、setup 或依赖路径误导使用者 | 验证 `scripts/setup.ps1`、`scripts/validate_platform.py`、受限 requirements 存在；只读读取 origin URL 和已登记远程特性分支；比对两份 README | origin 为 `https://github.com/leongibhub/codex-rd-platform.git`，本地 remote ref 含 `origin/codex/platform-v3-lifecycle`；两份 README 均给出同一 clone branch、requirements、setup 和 Python 3.11+ 前置条件 | PASS |
| TC-V3-README-004 | SAFETY / 将 Codex prompt 误写为后台模型服务，或将 Node adapter 误写为原生微信证据 | 比对两种语言的 Skill/host、`NOT_AVAILABLE` 和 native-WeChat 表述 | 中文明确“不是自动调用模型的云服务”及“Skill 是工作方法约束而不是服务启动器”；英文明确 not a model-calling cloud service / not a service launcher；两份都说明 WeChat native `NOT_AVAILABLE`、Node fake-wx 不替代原生 | PASS |

## 实际执行证据

| 阶段 | Runtime run | 实际命令与结果 |
| --- | --- | --- |
| unit | `run-e39b139793a34a70965cb5c163e22d60` | `.venv\Scripts\python.exe -X utf8 -m unittest tests.platform.test_readme_contract -q`；退出 0，4/4 PASS，0.640s 命令内耗时。 |
| integration | `run-46c756aebc3a47658a7b7db1d5107e72` | `.venv\Scripts\python.exe -X utf8 -m unittest tests.independent_multistack.test_v3_adapter_blackbox -q`；退出 0，4/4 PASS，1.114s 命令内耗时。该 suite 以隔离 DB 覆盖 loopback lifecycle 读取/输入拒绝、HTTP command 403、stack-probe 不建 DB、受控 lifecycle CLI 错误和不推荐发布的报告投影。 |

任务 `task-9046486dcff54b89b6cec5c3c2e1e387` 当前为 `READY/review`（3/4 checks）；本 Tester 未运行 review phase。

## CI fixture correction: host Git state is not a README contract

`TC-V3-README-003` 原先读取执行宿主的 `origin`，并硬断言它必须是官方 GitHub URL 且本地必须已存在 `origin/codex/platform-v3-lifecycle`。该断言会在 fork、PR checkout、无 `origin` checkout 或 shallow single-branch clone 中拒绝同一份正确 README；它观察的是 CI/宿主 checkout 状态，而不是 README 向使用者承诺的 clone URL、branch 或仓库文件。

这是 `BUG-QA-README-001`，分类为 `TEST_SCRIPT` fixture 问题，未改 README 或产品源码。修订后的 TC-003 保留两份 README 的官方 clone URL、feature branch、existing-clone commands、setup/dependency/Python 前置条件和实际仓库文件校验；同时在临时本地 Git source 上实际创建 `--depth 1 --single-branch --branch main` clone。该 clone 可观察到 `is-shallow-repository=true`，其 `origin` 为临时 file URI 而非官方 URL，且 `origin/codex/platform-v3-lifecycle` remote ref 为空——旧断言在此真实兼容场景会是 RED，新 README-contract 断言不再依赖这些宿主细节。

修正后实际执行：`.venv\Scripts\python.exe -X utf8 -m unittest tests.platform.test_readme_contract -v`，4/4 PASS，1.216s。此结果只证明可移植的文档契约检查；GitHub Actions 在线运行、网络 clone 和 fresh-install E2E 仍为 `NOT_EXECUTED`。

## 限制与未执行项

- 未运行 `setup.ps1`、`install-to-D.ps1` 或任何会创建 venv、安装依赖、写 MCP config/环境变量、复制/覆盖文件的全局/持久操作。
- 未在干净机器、网络 clone、无缓存依赖或新 Codex 客户端上执行 fresh-clone E2E；因此文档命令的本地路径/CLI 一致性 PASS 不等于全新安装成功。
- 未执行 README 中的真实浏览器交互、微信 Developer Tools/真机/发布、云 Agent/daemon、在线 GitHub Actions、生产部署或批准；这些能力保持 README 所述 `NOT_AVAILABLE` 或 `NOT_EXECUTED` 边界。
- integration 没有并入 `test_project_export_independent`，因为当时其 freshness 契约修复未被声明为本阶段已冻结输入；已执行的 adapter suite 是 4 项可观察路由 smoke，不能替代完整 export 重测。

未发现产品文档/CLI 失配缺陷，故没有产品 BUG。所有 PASS 均受以上实际命令和范围限制。
