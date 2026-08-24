# TC-001: 平台自动化与独立验证

- Record Type: PLATFORM_MAINTENANCE
- Test Case ID: TC-001
- Linked BUG: [BUG-001](BUG-001-platform-self-check-false-positive.md)
- Linked Task: [TASK-001](TASK-001-platform-readiness-repair.md)
- Execution Result: PASS
- Evidence Status: VERIFIED
- Execution Scope: 自动化、MCP stdio、setup、路径边界、安全模式扫描和 Git 完整性；不包含 Codex 重启后的会话工具可见性。
- Evidence Record: [EVD-T8-TEST-20260822](test-evidence-2026-08-22.md)

## Objective

在可追溯的提交上验证 BUG-001 修复的自动化和独立测试范围。通过本用例不代表项目 Gate、发布、部署、外部服务调用或 Codex 重启后的工具可见性已经完成。

## Preconditions

1. 目标工作树为 `D:\codex-rd-platform\.worktrees\platform-readiness`。
2. 使用仓库 `.venv` 和受信任的 `.codex/config.toml`。
3. 外部 Redmine、RAGFlow、GitLab 调用不在本用例范围内，状态为 `NOT_EXECUTED`；不记录或推断任何凭据值。

## Procedure and Expected Results

| Step | Exact command / procedure | Expected result |
|---|---|---|
| 1 | `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` | 全量自动化测试退出码为 0。 |
| 2 | `.\.venv\Scripts\python.exe -m pip check` | 输出 `No broken requirements found.`，退出码为 0。 |
| 3 | `.\.venv\Scripts\python.exe scripts\validate_platform.py` | 输出模板模式验证通过、`Evaluated Gates: NONE` 和 `RUNTIME CHECK: EXECUTED`；不形成项目 Gate 结论。 |
| 4 | `.\.venv\Scripts\python.exe scripts\validate_platform.py --static-only` | 输出 `RUNTIME CHECK: NOT EXECUTED`，退出码为 0；此步骤不是完整运行时验证。 |
| 5 | 运行受信任配置的实际 stdio 健康检查三次。 | 每次精确列出下方 8 个工具、无问题，且清理后 Python 进程数为 0。 |
| 6 | 在同一 PowerShell 进程的安全临时 clone 中运行 `scripts\setup.ps1`、`-SkipDependencyInstall` 和 validator-failure 负向路径。 | 成功/跳过路径分别成功且恢复调用方 cwd；失败路径退出 1、不打印完成标记且恢复 cwd；freeze、用户变量边界和安全清理满足证据记录。 |
| 7 | `git grep -n -I -E "sk-[A-Za-z0-9_-]{16,}|glpat-[A-Za-z0-9_-]{10,}|BEGIN [A-Z ]*PRIVATE KEY"`；`git diff --check`；`git fsck --no-reflogs` | 秘密扫描无匹配（底层 grep 退出 1 是预期 no-match）；diff 和 fsck 退出 0。 |

## Required stdio Tool Set

验证的服务器注册工具必须精确为以下 8 项：

1. `get_gitlab_project`
2. `get_project_context`
3. `get_redmine_issue`
4. `ragflow_search`
5. `read_local_doc`
6. `search_gitlab_issues`
7. `search_local_docs`
8. `search_redmine`

## Executed Results

| Execution | Target | Started / Ended (Asia/Shanghai) | Exit / count | Result | Raw evidence |
|---|---|---|---|---|---|
| Initial independent test | `2d3ae0a90fdf73d6e2f0494d7c02f18c5b0c2543` | 21:55:19–21:56:20 | 0; 94 tests, 0 failures | PASS | [01-full-unittest](evidence/2026-08-22/01-full-unittest.txt) |
| Initial stdio contract, three runs | `2d3ae0a` | recorded in raw log | 0; 3 × 10 tests | PASS; exact tool contract and zero residual repository `.venv` Python processes | [04-mcp-stdio-repeat](evidence/2026-08-22/04-mcp-stdio-repeat.txt) |
| Initial negative/boundary suite | `2d3ae0a` | 22:02:22–22:06:45 | 0; 55 tests, 0 failures | PASS | [06-boundary-negative](evidence/2026-08-22/06-boundary-negative.txt) |
| Independent retest | `ce9ca0e2162b6612deb03209de1130330ae4c14b` | 22:47:52–22:48:59 | 0; 100 tests, 0 failures | PASS | [10-full-unittest-retest](evidence/2026-08-22/10-full-unittest-retest.txt) |
| P2 directed contracts | `ce9ca0e` | 22:51:48–22:52:28 | 0; 5 tests, 0 failures | PASS | [15-five-p2-directed-contracts-final](evidence/2026-08-22/15-five-p2-directed-contracts-final.txt) |
| Correct-layout external junction | `ce9ca0e` | 22:49:54–22:49:55 | 0; 1 probe | PASS; `MCP_COMMAND_UNTRUSTED` | [13-correct-layout-junction-probe](evidence/2026-08-22/13-correct-layout-junction-probe.txt) |
| Full/static validator | `ce9ca0e` | 22:53:21–22:53:24 | 0; 2 commands | PASS; full runtime executed, static runtime not executed | [16-validator-full-static-retest](evidence/2026-08-22/16-validator-full-static-retest.txt) |
| Real stdio health, three runs | `ce9ca0e` | 22:53:41–22:53:45 | 0; 3 runs, 0 issues | PASS; exact eight tools and zero residual Python processes | [17-stdio-health-three-runs](evidence/2026-08-22/17-stdio-health-three-runs.txt) |
| Same-process setup / failure / cleanup | `ce9ca0e` | 22:58:03–23:00:28 | see evidence | PASS for the recorded success, skip, failure, cwd, freeze, variable-boundary and cleanup assertions | [19-same-process-clone-setup-final](evidence/2026-08-22/19-same-process-clone-setup-final.txt) |
| Final independent regression | `5b422d0` | NOT_AVAILABLE — timestamps not retained | 0; 103 tests, 0 failures, 0 errors, 0 skipped; runner 83.216 s | PASS; final tester also observed 9/9 manifest-path matrix fail-closed, full/static validation, stdio 3/3, and environment/integrity checks. Literal invocations for those additional checks were not retained. | [25-final-independent-retest](evidence/2026-08-22/25-final-independent-retest.md) |

## Exclusions and Pending Verification

- [TC-002](TC-002-codex-restart-validation.md) remains `NOT_EXECUTED`.
- Redmine, RAGFlow and GitLab external calls remain `NOT_EXECUTED`.
- This maintenance record has no active project Gate Register, RTM data row, acceptance or release conclusion because the manifest remains in template mode.
