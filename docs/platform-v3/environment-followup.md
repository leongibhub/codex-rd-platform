# 多环境与跨 OS 独立跟进验证

执行者：`/root/v3_qa_apps`（Tester）  
执行日期：2026-09-06  
范围：只读探测本机 Windows、WSL Ubuntu 22.04、真实浏览器、微信开发者工具候选位置与 Docker/部署前提；对已具备运行时的公共接口进行一次独立跨 OS 运行。未安装任何软件、未启动 Docker、未触碰生产数据，也未改动应用源码。

本记录不是原生微信、浏览器 E2E、容器部署、Gate、发布或人工验收结论。所有输入均是独立测试现有的临时合成文件。

## 风险模型与执行用例

| 用例 | 关联需求 | 目标与风险 | 前置 / 环境 | 步骤与数据 | 预期 | 实际结果 / 状态 / 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-ENV-001 | REQ-MATRIX-PY-01..04 | Linux 解释器改变 CSV 编码、Decimal 或 CLI 退出语义 | WSL `Ubuntu-22.04`，`python3 3.10.12`，仓库挂载为 `/mnt/d` | `cd /mnt/d/codex-rd-platform && python3 -m unittest discover -s tests/independent_multistack -p test_python_expenses_blackbox.py -v`；套件自建 BOM CSV、长 Decimal、极端指数及坏输入 | 5 个公共 CLI 断言均通过，命令退出 0 | 实际退出 0；5/5 `ok`，耗时 1.566s。**PASS**。终端输出为本项证据。 |
| TC-ENV-002 | REQ-MATRIX-JAVA-06 | Linux 端缺 Java 时误称 Java CLI 可跨 OS 执行 | 同一 WSL | 读取 `java -version`、`javac -version` 与 `apt-cache policy openjdk-17-jdk`，不安装 | 若缺失，明确记录不能编译/执行及可修复条件 | `java`、`javac` 均 `command not found`；`openjdk-17-jdk` 未安装、候选 `17.0.18+8-1~22.04.1`。Java 公共 CLI **NOT_EXECUTED**。 |
| TC-ENV-003 | REQ-MATRIX-WEB-07；REQ-MATRIX-WECHAT-005 | Linux 缺 Node 时误称 Node business/Page adapter 已跨 OS 验证 | 同一 WSL | 读取 `node --version`、`apt-cache policy nodejs`；不安装 | 只有可运行的 Node 才运行 `node --test` | `node` 为 `command not found`；Ubuntu 22.04 默认候选为 `12.22.9`，不足以作为当前 `node --test` 套件的已验证运行时。Web business-module 与 fake-wx Page-adapter **NOT_EXECUTED**。 |
| TC-ENV-004 | REQ-MATRIX-CPP-06 | 将 Windows-host wrapper 当作 Linux-native 验证 | 同一 WSL，`g++ 11.4.0` | 读取 `g++ --version` 与 `cpp_inventory/verify.py` 的 WSL 调用 | 识别是否可从 Linux 直接复用既有 driver | `/usr/bin/g++` 11.4.0 可用；但 driver 第 27、48 行硬编码 `wsl.exe`，从 Linux 直接调用会递归/不可用。本轮未伪造 Linux C++ 测试，**NOT_EXECUTED**。 |
| TC-ENV-005 | REQ-MATRIX-WEB-01..07 | 误把“安装的浏览器”当成已完成用户流或浏览器兼容 | Windows；受控自动化表面实际列出 Edge 用户配置文件会话 | 枚举受控浏览器会话与固定安装路径文件版本；未导航/未读取网页内容 | 给出真实浏览器可用性，明确不代替 E2E | 受控 Edge 会话存在；`msedge.exe` ProductVersion `151.0.4129.107`，Chrome `152.0.7977.77`。浏览器功能/E2E **NOT_EXECUTED**。 |
| TC-ENV-006 | REQ-MATRIX-WECHAT-001..05；NFR-MATRIX-WECHAT-001 | 未探测就断言微信原生工具不存在 | Windows PATH、六个常见 `cli.bat` 固定路径、三处卸载注册表根 | `Get-Command`；`Test-Path` 六候选；按“微信.*开发 / WeChat.*Dev”查卸载项；仅在找到 CLI 时才执行 `--help` | 发现工具时只读取版本/help；否则限定探测范围说明原生测试不能运行 | PATH、六候选路径、卸载表匹配均无结果，因此没有可调用 CLI、也无 `--help` 可执行。该结果仅表示**已探测位置未发现**，不声称全磁盘或非标准安装绝对不存在；原生导入/IDE/真机 **NOT_EXECUTED**。 |
| TC-ENV-007 | 部署前提（无应用部署需求） | Docker 客户端存在被误述为容器运行/部署成功 | Windows Docker Desktop client；WSL Ubuntu | `docker version --format '{{json .Client}}'`、`docker context ls`、WSL `docker version`，以及仓库 deployment descriptor 文件清单 | 只有 daemon 与描述符都存在时才允许进一步部署验证 | Windows client `29.5.3`、context 为 `desktop-linux`；连接 `npipe:////./pipe/dockerDesktopLinuxEngine` 失败（pipe 不存在）。WSL 无 `docker`，提示未启用 Docker Desktop WSL integration；未找到 Dockerfile/compose/deployment descriptor。部署/容器测试 **NOT_EXECUTED**。 |

## 实际环境观察

### Windows

- `wsl.exe`：`C:\WINDOWS\system32\wsl.exe`，文件版本 `10.0.26100.8972`。
- `node.exe`：`C:\Program Files\nodejs\node.exe`，实际 `node --version` 为 `v22.21.0`。
- Windows Python launcher：默认 `3.13` 为 `C:\Program Files\Python\python.exe`；另有 Astral CPython `3.12.12`。本次跨 OS Python 用的是 WSL 的 `python3`，不是 Windows 解释器。
- 受控浏览器表面实际列出 Edge（用户配置文件“用户配置 1”）及一个已打开的仓库标签页；未读取标签页内容。固定安装路径还确认 Edge 和 Chrome 二进制存在，版本见 TC-ENV-005。
- Docker Desktop 的 client 存在，但 daemon 不可连接；不代表本机可运行容器。

### WSL Ubuntu 22.04

`wsl.exe -l -v` 观察到默认发行版 `Ubuntu-22.04`、WSL version 2（另有停止状态的 `docker-desktop`）。实际命令启动后读取到：

- OS：Ubuntu `22.04.5 LTS` (Jammy)。
- `python3`：`Python 3.10.12`；TC-ENV-001 已实际通过。
- C++：`g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`，但现有 C++ 验证驱动是 Windows→WSL 适配器而非 Linux-native driver。
- Java：无 `java` / `javac`。可修复条件是通过受控包管理安装一个同时提供二者的 JDK，例如当前仓库可见候选 `openjdk-17-jdk 17.0.18+8-1~22.04.1`，再以 Linux `javac` 从源码构建到 Linux 临时 build 目录并运行 Java CLI；本次未安装，故不可声称 Java 跨 OS PASS。
- Node：无 Linux `node`。Ubuntu 默认 `nodejs 12.22.9` 不是当前 `node --test` 套件的充分、已验证运行时；需要由环境维护者提供并验证可执行 `node --test` 的 Node 18+ 运行时后，才可运行 Web/WeChat 的既有 Node 测试。
- Docker：WSL 中无 `docker`，Docker Desktop WSL integration 未启用。
- 仓库从 Windows 盘以 9p 挂载到 `/mnt/d`；本次 Python 测试只创建其临时测试数据，不写应用或生产数据。

## 结论与后续条件

本轮唯一已完成的跨 OS 应用验证是 TC-ENV-001（Python 公共 CLI，WSL 5/5 PASS）。Java、Web 和 WeChat 不是失败结果，而是由于对应 Linux 运行时或原生 SDK/CLI 不可用而 `NOT_EXECUTED`。C++ Linux-native 路径同样 `NOT_EXECUTED`，因为现有 driver 明确依赖 Windows `wsl.exe`；不应将此前 Windows host 驱动的 WSL 结果重新命名为本轮 Linux 直接验证。

没有发现可归因于应用功能的新增缺陷，因此未创建 BUG。环境缺口应由环境维护者处理：配置 Linux JDK、提供 Node 18+、按需启用 Docker WSL integration，并在发现微信开发者工具的确切安装路径后执行仅版本/help 预检，之后再安排相应独立重测。
