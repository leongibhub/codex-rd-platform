# TASK-V3-019 — Linux 原生安装

- 任务：TASK-V3-019
- 需求：REQ-V3-019
- 设计：[DES-V3-003 / CR-V3-003](completion-execution-design.md)
- 状态：实现记录；不是独立测试、Gate 或人工验收结论。

## 前置条件

Linux 主机需具有 Git、Python 3.11 或更高版本，以及当前仓库的本地
`user.name` 和 `user.email`。安装脚本会在创建 `.venv` 前检查身份；这只
用于 Git 可追溯性，不是人工审批证明。

```bash
git config user.name "Your Name"
git config user.email "you@example.invalid"
./scripts/setup.sh --python-command python3.11
```

默认 Python 命令为 `python3`。在已经完成依赖安装、只需重新生成配置和健康
检查时，可使用：

```bash
./scripts/setup.sh --skip-dependency-install
```

脚本只在当前 checkout 创建或复用 `.venv` 和 `knowledge/local`，不删除已有
数据，不调用特权命令，不写全局 Git 配置，也不改全局 Python 环境。新建 venv
使用 `--copies`，避免解释器符号链接指向宿主 Python；复用时会验证解释器解析后
仍位于当前 checkout 的 `.venv` 内且版本为 Python 3.11+。不安全或过时的既有
venv 会失败并保留原状，须由操作者明确修复。它将通过当前 OS 的
`.venv/bin/python` 运行 `write_local_config.py`，再执行完整
`validate_platform.py`，后者会启动受信任的 MCP stdio 服务并校验 health。

失败时不会打印 `Setup complete.`；保留 checkout 与已存在的诊断数据，修正
前置条件后可重复运行。

## 验证范围

`tests/platform/test_linux_setup.py` 覆盖脚本安全契约，并在有 WSL 时建立
隔离 Git fixture，实际运行 Linux bash：缺失 Git 身份必须在创建 venv 前失败；
fixture 的本地 Git identity 仅用于测试，绝不表示人工批准。成功路径必须在
Python 3.11+ Linux 主机执行，且以 `PLATFORM VALIDATION: PASS` 的实际输出为准。
当前不把静态断言或低版本 Python 的失败路径当作 MCP health 通过证据。
