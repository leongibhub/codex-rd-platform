# 平台就绪性修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Git 基线、MCP SDK v2 兼容、平台自检、Gate/RTM 治理和 setup 可靠性，使平台能可信地报告模板模式就绪状态。

**Architecture:** 将平台检查拆为纯静态契约层和真实 MCP stdio 运行时层；`validate_platform.py` 只负责 CLI 编排，`platform_validation.py` 负责可单测的静态规则，`mcp_health_check.py` 负责受限子进程健康检查。生命周期使用 manifest 中的模板/活动模式和唯一 Gate Register 契约，避免模板默认文本被误认为项目证据。

**Tech Stack:** Python 3.11+、Python `unittest`、MCP Python SDK 2.x、PowerShell、TOML、Markdown、Git。

**Spec:** `docs/superpowers/specs/2026-08-22-platform-readiness-repair-design.md`

## Global Constraints

- 不启动产品项目，不创建产品需求或项目 Gate 结论。
- MCP 依赖必须满足 `mcp>=2.0.0,<3.0.0`，HTTP 客户端必须满足 `requests>=2.31.0,<3.0.0`。
- `company_context` 必须精确暴露设计文档列出的 8 个工具。
- 密钥、Token、Cookie、Authorization 值不得进入 Git、测试输出或异常文本。
- 默认自检必须执行真实 stdio 健康检查；`--static-only` 必须明确标记运行时检查未执行。
- Gate 状态仅允许 `PASS | FAIL | BLOCKED`；模板文本不能作为证据。
- 所有生产代码变更必须先有能因当前缺陷正确失败的测试。
- 每个提交必须引用 `BUG-001`、`TASK-001` 和实际测试命令。

---

## 文件职责图

| 文件 | 单一职责 |
|---|---|
| `scripts/platform_validation.py` | manifest、Agent、Skill、Git、Gate 模板和 RTM 的纯静态验证 |
| `scripts/mcp_health_check.py` | 解析受信任 MCP 配置，启动 stdio 子进程并验证 8 个工具 |
| `scripts/validate_platform.py` | 解析 CLI 参数、组合检查、打印状态和返回退出码 |
| `tools/mcp/company-context/server.py` | 定义 MCPServer 和 8 个公司上下文工具 |
| `scripts/setup.ps1` | Windows 前置检查、虚拟环境、依赖、知识目录和完整自检 |
| `tests/platform/*.py` | 单元、契约和 stdio 集成测试 |
| `templates/gate-register-template.md` | 活动项目 Gate Register 的唯一标准模板 |
| `docs/08-project-management/gate-management.md` | Gate 状态、评估和证据治理规则 |
| `docs/03-requirements/requirement-traceability-matrix.md` | 一行一个 REQ/NFR 的端到端追踪契约 |
| `docs/platform-maintenance/*` | BUG-001/TASK-001/ADR 和实际验证证据，不污染产品项目模板 |

---

### Task 1: 建立平台维护追踪记录

**Files:**
- Create: `docs/platform-maintenance/BUG-001-platform-self-check-false-positive.md`
- Create: `docs/platform-maintenance/TASK-001-platform-readiness-repair.md`
- Create: `docs/platform-maintenance/ADR-001-native-mcp-v2.md`
- Create: `docs/platform-maintenance/ADR-002-runtime-mcp-validation.md`
- Create: `docs/platform-maintenance/ADR-003-relative-mcp-launch.md`
- Modify: `docs/08-project-management/issue-register.md`
- Modify: `docs/08-project-management/decision-log.md`

**Interfaces:**
- Consumes: 已批准设计、缺陷复现输出、基线提交 `7b7198f`。
- Produces: 后续提交统一引用的 BUG/TASK/ADR 事实记录。

- [ ] **Step 1: 创建维护记录目录和五份证据文档**

每份文档必须包含 `Record Type: PLATFORM_MAINTENANCE`。BUG-001 记录已观察到的 `ModuleNotFoundError`、validator 假阳性和 Git 基线问题；TASK-001 列出本计划八个任务和验收条件；三个 ADR 分别记录原生 MCP v2、真实 stdio 健康检查和相对启动路径决策。所有测试状态先写 `NOT EXECUTED`，不能预填 PASS。

- [ ] **Step 2: 更新 Issue Register 和 Decision Log**

Issue Register 增加 BUG-001，状态 `OPEN`；Decision Log 增加 ADR-001 至 ADR-003，状态 `ACCEPTED_FOR_IMPLEMENTATION`，并链接设计文档。

- [ ] **Step 3: 验证文档没有伪造证据**

Run:

```powershell
rg -n "PASS|CLOSED|deployment succeeded|customer accepted" docs\platform-maintenance
```

Expected: 只允许在规则说明或验收条件中出现；执行结果字段仍为 `NOT EXECUTED`，BUG-001 仍为 `OPEN`。

- [ ] **Step 4: 提交追踪记录**

```powershell
git add docs/platform-maintenance docs/08-project-management/issue-register.md docs/08-project-management/decision-log.md
git commit -m "docs(platform): record readiness repair traceability" -m "Bug: BUG-001`nTask: TASK-001`nTests: NOT EXECUTED (records only)"
```

---

### Task 2: 用 TDD 建立 manifest 契约

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/platform/__init__.py`
- Create: `tests/platform/test_manifest_contract.py`
- Create: `scripts/platform_validation.py`
- Modify: `platform-manifest.json`

**Interfaces:**
- Consumes: `.codex/agents/*.toml` 的 `name`、`.agents/skills/*/SKILL.md` 的 frontmatter。
- Produces: `ValidationIssue`、`load_manifest(root)`、`collect_agent_ids(root)`、`collect_skill_ids(root)`、`validate_manifest_contract(root)`。

- [ ] **Step 1: 写 manifest RED 测试**

```python
import unittest
from pathlib import Path

from scripts.platform_validation import (
    collect_agent_ids,
    collect_skill_ids,
    load_manifest,
    validate_manifest_contract,
)

ROOT = Path(__file__).resolve().parents[2]


class ManifestContractTests(unittest.TestCase):
    def test_manifest_matches_runtime_ids_and_declares_template_mode(self):
        manifest = load_manifest(ROOT)
        self.assertEqual(set(manifest["agents"]), collect_agent_ids(ROOT))
        self.assertEqual(set(manifest["skills"]), collect_skill_ids(ROOT))
        self.assertEqual(manifest["gates"], [f"G{i}" for i in range(12)])
        self.assertEqual(manifest["lifecycle_mode"], "template")
        self.assertEqual(validate_manifest_contract(ROOT), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行 RED 测试并确认失败原因正确**

Run:

```powershell
python -m unittest tests.platform.test_manifest_contract -v
```

Expected: FAIL，因为 `scripts.platform_validation` 尚不存在；建立最小模块后再次运行，应因四个 Agent ID 不一致和缺少 `lifecycle_mode` 失败。

- [ ] **Step 3: 实现最小静态验证接口**

`scripts/platform_validation.py` 先实现：

```python
from dataclasses import dataclass
from pathlib import Path
import json
import tomllib


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str


def load_manifest(root: Path) -> dict:
    return json.loads((root / "platform-manifest.json").read_text(encoding="utf-8"))


def collect_agent_ids(root: Path) -> set[str]:
    return {
        tomllib.loads(path.read_text(encoding="utf-8"))["name"]
        for path in (root / ".codex" / "agents").glob("*.toml")
    }


def collect_skill_ids(root: Path) -> set[str]:
    result = set()
    for path in (root / ".agents" / "skills").glob("*/SKILL.md"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("name:"):
                result.add(line.split(":", 1)[1].strip())
                break
    return result
```

`validate_manifest_contract` 返回 `list[ValidationIssue]`，对 Agent、Skill、G0–G11 和 `lifecycle_mode in {"template", "active"}` 分别返回稳定错误码。

- [ ] **Step 4: 修正 machine-readable manifest**

将四个连字符 Agent ID 改为 `documentation_manager`、`release_manager`、`requirement_analyst`、`product_manager`，增加：

```json
"lifecycle_mode": "template",
"minimum_python": "3.11",
"gate_register_template": "templates/gate-register-template.md",
"active_gate_register": "docs/08-project-management/gate-register.md"
```

- [ ] **Step 5: 运行 GREEN 测试**

```powershell
python -m unittest tests.platform.test_manifest_contract -v
```

Expected: 1 test PASS。

- [ ] **Step 6: 提交 manifest 契约**

```powershell
git add platform-manifest.json scripts/platform_validation.py tests
git commit -m "fix(platform): align manifest with runtime identifiers" -m "Bug: BUG-001`nTask: TASK-001`nTests: python -m unittest tests.platform.test_manifest_contract -v"
```

---

### Task 3: 用 TDD 迁移 MCP v2 并封闭本地路径

**Files:**
- Create: `tests/platform/test_company_context.py`
- Modify: `tools/mcp/company-context/server.py`
- Modify: `tools/mcp/company-context/requirements.txt`

**Interfaces:**
- Consumes: MCP SDK 2.x `MCPServer`、环境变量配置。
- Produces: `mcp: MCPServer`、`_is_approved_path(path, roots)` 和 8 个行为不变的工具。

- [ ] **Step 1: 在隔离 worktree 创建受控虚拟环境**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools\mcp\company-context\requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Expected: 依赖安装成功；此时 server 导入仍因旧 `FastMCP` 路径失败。

- [ ] **Step 2: 写 MCP 与路径安全 RED 测试**

测试通过 `importlib.util.spec_from_file_location` 加载 `server.py`，并包含以下真实断言：

```python
EXPECTED_TOOLS = {
    "get_gitlab_project", "get_project_context", "get_redmine_issue",
    "ragflow_search", "read_local_doc", "search_gitlab_issues",
    "search_local_docs", "search_redmine",
}

async def _tool_names(module):
    from mcp.client import Client
    async with Client(module.mcp) as client:
        result = await client.list_tools(cache_mode="refresh")
        return {tool.name for tool in result.tools}

def test_mcp_declares_exact_toolset(self):
    self.assertEqual(anyio.run(_tool_names, self.module), EXPECTED_TOOLS)

def test_search_does_not_read_candidate_outside_approved_root(self):
    with tempfile.TemporaryDirectory() as approved, tempfile.TemporaryDirectory() as outside:
        secret = Path(outside) / "outside.txt"
        secret.write_text("OUTSIDE_SENTINEL", encoding="utf-8")
        with patch.dict(os.environ, {"COMPANY_LOCAL_ROOTS": approved}, clear=True):
            with patch.object(Path, "rglob", return_value=[secret]):
                result = json.loads(self.module.search_local_docs("OUTSIDE_SENTINEL"))
        self.assertEqual(result["results"], [])
```

再覆盖 Redmine、RAGFlow、GitLab 未配置时返回 JSON `error`，且错误文本不含环境变量值。

- [ ] **Step 3: 运行 RED 测试**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.platform.test_company_context -v
```

Expected: ERROR/FAIL，首要原因是 `No module named 'mcp.server.fastmcp'`；迁移导入后，路径测试应因读取外部候选文件而 FAIL。

- [ ] **Step 4: 实施最小 MCP v2 迁移**

```python
from mcp.server import MCPServer

mcp = MCPServer(name="company-context", version="0.2.0")
```

依赖文件改为：

```text
mcp>=2.0.0,<3.0.0
requests>=2.31.0,<3.0.0
```

- [ ] **Step 5: 实施统一 approved-root 检查**

```python
def _is_approved_path(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    return any(
        _is_relative_to(resolved, root.resolve())
        for root in roots
        if root.exists()
    )


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
```

`search_local_docs` 在读取每个候选文件前调用该函数；`read_local_doc` 复用该函数。

- [ ] **Step 6: 运行 GREEN 与依赖检查**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.platform.test_company_context -v
.\.venv\Scripts\python.exe -m pip check
```

Expected: 全部 PASS，依赖无冲突。

- [ ] **Step 7: 提交 MCP 修复**

```powershell
git add tools/mcp/company-context tests/platform/test_company_context.py
git commit -m "fix(mcp): migrate company context to SDK v2" -m "Bug: BUG-001`nTask: TASK-001`nTests: python -m unittest tests.platform.test_company_context -v"
```

---

### Task 4: 用 TDD 建立真实 stdio 健康检查和 Codex 配置

**Files:**
- Create: `scripts/mcp_health_check.py`
- Create: `tests/platform/test_mcp_stdio.py`
- Create: `knowledge/local/README.md`
- Modify: `.codex/config.toml`

**Interfaces:**
- Consumes: `ValidationIssue`、MCP config、工作区 `.venv`、`server.py`。
- Produces: `resolve_company_context_config(root)`、`async_check_company_context(root)`、`check_company_context(root)`。

- [ ] **Step 1: 写 config 和 stdio RED 测试**

```python
EXPECTED_ENV_NAMES = {
    "COMPANY_LOCAL_ROOTS",
    "REDMINE_BASE_URL", "REDMINE_API_KEY", "REDMINE_PROJECT",
    "RAGFLOW_BASE_URL", "RAGFLOW_API_KEY", "RAGFLOW_DATASET_ID",
    "GITLAB_BASE_URL", "GITLAB_TOKEN", "GITLAB_PROJECT_ID",
}


class CompanyContextStdioTests(unittest.TestCase):
    def test_config_forwards_documented_env_and_is_required(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        server = config["mcp_servers"]["company_context"]
        self.assertEqual(server["cwd"], ".")
        self.assertTrue(server["required"])
        self.assertEqual(set(server["env_vars"]), EXPECTED_ENV_NAMES)

    def test_stdio_health_check_lists_exact_tools(self):
        issues = check_company_context(ROOT)
        self.assertEqual(issues, [])
```

`EXPECTED_ENV_NAMES` 精确包含设计中的 10 个变量名，不包含变量值。

再使用临时配置副本逐项注入以下故障，并断言稳定错误码：command 位于仓库 `.venv` 外、`cwd` 不等于仓库根、server 参数位于 `tools/mcp/company-context` 外、启动超时。超时用一个只阻塞、不写 stdout 的测试脚本触发；测试结束后断言子进程已回收。

- [ ] **Step 2: 运行 RED 测试**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.platform.test_mcp_stdio -v
```

Expected: FAIL，因为 config 缺少 `cwd`、`required`、`env_vars`，且健康检查模块尚不存在。

- [ ] **Step 3: 实现受信任配置解析**

`resolve_company_context_config(root)` 必须：

- 解析 `.codex/config.toml`；
- 将 command、args 中的 server 路径和 cwd 解析为绝对路径；
- 拒绝 command 不在 `root/.venv`、server 不在 `root/tools/mcp/company-context`、cwd 不等于 root；
- 返回 `StdioServerParameters` 所需数据，不打印 env 值。

- [ ] **Step 4: 实现真实 stdio list-tools**

核心流程使用：

```python
from mcp import Client, StdioServerParameters, stdio_client

async def _list_tools(params: StdioServerParameters):
    transport = stdio_client(params)
    async with Client(transport, mode="auto", read_timeout_seconds=5) as client:
        return await client.list_tools(cache_mode="refresh")
```

`async_check_company_context` 在 `anyio.fail_after(15)` 内核对工具集合、唯一性、非空描述和对象型 input schema；异常映射到设计中的稳定错误码。`check_company_context` 用 `anyio.run` 提供同步入口。

- [ ] **Step 5: 更新 Codex 配置和默认知识目录**

在 `company_context` 表中加入：

```toml
cwd = "."
required = true
env_vars = [
  "COMPANY_LOCAL_ROOTS",
  "REDMINE_BASE_URL",
  "REDMINE_API_KEY",
  "REDMINE_PROJECT",
  "RAGFLOW_BASE_URL",
  "RAGFLOW_API_KEY",
  "RAGFLOW_DATASET_ID",
  "GITLAB_BASE_URL",
  "GITLAB_TOKEN",
  "GITLAB_PROJECT_ID",
]
```

`knowledge/local/README.md` 明确只允许提交非敏感知识，私密目录必须通过环境变量配置在仓库外。

- [ ] **Step 6: 运行 GREEN 和重复启动测试**

```powershell
1..3 | ForEach-Object { .\.venv\Scripts\python.exe -m unittest tests.platform.test_mcp_stdio -v }
Get-Process python -ErrorAction SilentlyContinue | Where-Object Path -Like '*platform-readiness\.venv*'
```

Expected: 三次均 PASS；第二条命令无本 worktree 遗留 Python 进程。

- [ ] **Step 7: 提交 stdio 健康检查**

```powershell
git add .codex/config.toml knowledge/local scripts/mcp_health_check.py tests/platform/test_mcp_stdio.py
git commit -m "feat(validation): verify company context over stdio" -m "Bug: BUG-001`nTask: TASK-001`nTests: python -m unittest tests.platform.test_mcp_stdio -v"
```

---

### Task 5: 用 TDD 补齐 Gate 与 RTM 治理契约

**Files:**
- Create: `templates/gate-register-template.md`
- Create: `docs/08-project-management/gate-management.md`
- Create: `tests/platform/test_governance_contract.py`
- Modify: `scripts/platform_validation.py`
- Modify: `docs/03-requirements/requirement-traceability-matrix.md`
- Modify: `docs/00-project-initiation/context-baseline.md`
- Modify: `AGENTS.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: manifest `lifecycle_mode` 和 Gate/RTM 文件路径。
- Produces: `validate_gate_contract(root, manifest)`、`validate_rtm_contract(root, manifest)`。

- [ ] **Step 1: 写治理 RED 测试**

```python
class GovernanceContractTests(unittest.TestCase):
    def test_gate_template_has_all_gates_and_controlled_states(self):
        manifest = load_manifest(ROOT)
        self.assertEqual(validate_gate_contract(ROOT, manifest), [])

    def test_rtm_has_auditable_columns(self):
        manifest = load_manifest(ROOT)
        self.assertEqual(validate_rtm_contract(ROOT, manifest), [])

    def test_template_mode_does_not_require_active_gate_register(self):
        manifest = load_manifest(ROOT)
        self.assertEqual(manifest["lifecycle_mode"], "template")
        self.assertFalse((ROOT / manifest["active_gate_register"]).exists())
        self.assertEqual(validate_gate_contract(ROOT, manifest), [])
```

再用临时 manifest 将模式改为 `active`，断言缺少中央 Gate Register 时出现 `GOVERNANCE_ACTIVE_REGISTER_MISSING`。

- [ ] **Step 2: 运行 RED 测试**

```powershell
python -m unittest tests.platform.test_governance_contract -v
```

Expected: FAIL，因为 Gate 模板、治理函数和 RTM 新表头不存在。

- [ ] **Step 3: 创建唯一 Gate Register 模板**

模板包含 G0–G11 共 12 行，并包含：Gate ID、Gate Name、Gate Status、Evaluation State、Baseline、Evaluated At、Evaluator Role、Recorder、Criteria Result、Evidence IDs、Blockers/Links、Rationale、Next Action、Owner、Target Date、Human Approval Evidence。

模板顶部必须声明：`Artifact Type: TEMPLATE` 和“不得作为项目 Gate 证据”。

- [ ] **Step 4: 扩展 RTM 表头**

使用设计规定的 19 列，不创建任何虚构需求行。Coverage Rules 增加已发布需求、Closed BUG、批准 CR 和测试证据限制。

- [ ] **Step 5: 实现治理验证函数**

模板模式验证模板结构但不要求活动 Register；活动模式要求 Register 存在、G0–G11 唯一、Gate 状态受控、PASS 行证据非空。RTM 验证精确表头；活动模式再验证每个数据行的状态组合。

- [ ] **Step 6: 更新治理说明**

`AGENTS.md` 和 `gate-management.md` 明确：中央 Register 是唯一状态源；Gate/评估/文档/证据/追踪状态分别使用设计中的枚举。`context-baseline.md` 标注 `Lifecycle Mode: TEMPLATE`、`Active Project: NONE`、`Gate Evaluation: NOT_EVALUATED`。README 的首次运行说明必须解释模板模式 PASS 不代表任何项目 Gate PASS。

- [ ] **Step 7: 运行 GREEN 测试**

```powershell
python -m unittest tests.platform.test_governance_contract -v
```

Expected: 全部 PASS。

- [ ] **Step 8: 提交治理契约**

```powershell
git add AGENTS.md README.md templates/gate-register-template.md docs/00-project-initiation/context-baseline.md docs/03-requirements/requirement-traceability-matrix.md docs/08-project-management/gate-management.md scripts/platform_validation.py tests/platform/test_governance_contract.py
git commit -m "docs(governance): define gate and RTM contracts" -m "Bug: BUG-001`nTask: TASK-001`nTests: python -m unittest tests.platform.test_governance_contract -v"
```

---

### Task 6: 用 TDD 重构完整平台 validator

**Files:**
- Create: `tests/platform/test_validator_contract.py`
- Modify: `scripts/platform_validation.py`
- Modify: `scripts/validate_platform.py`

**Interfaces:**
- Consumes: `validate_manifest_contract`、`validate_gate_contract`、`validate_rtm_contract`、`validate_runtime_prerequisites`、`check_company_context` 和 Git CLI。
- Produces: `ValidationReport`、`validate_platform(root, static_only=False, strict=False)` 与 CLI 退出码。

- [ ] **Step 1: 写 validator RED 测试**

```python
class ValidatorContractTests(unittest.TestCase):
    def test_full_validation_runs_runtime_and_passes_template_mode(self):
        report = validate_platform(ROOT)
        self.assertTrue(report.ok, report.issues)
        self.assertTrue(report.runtime_executed)
        self.assertEqual(report.lifecycle_mode, "template")
        self.assertEqual(report.evaluated_gates, [])

    def test_static_only_never_claims_full_runtime_pass(self):
        report = validate_platform(ROOT, static_only=True)
        self.assertTrue(report.ok, report.issues)
        self.assertFalse(report.runtime_executed)

    def test_cli_reports_template_mode_without_gate_pass(self):
        completed = subprocess.run(
            [sys.executable, "scripts/validate_platform.py"],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PLATFORM VALIDATION: PASS (TEMPLATE MODE)", completed.stdout)
        self.assertIn("Evaluated Gates: NONE", completed.stdout)
```

增加负向测试：临时破坏 manifest Agent ID、Gate 模板和 RTM 表头时必须返回相应错误码；Git 无 HEAD 时返回 `GIT_INVALID`；mock Python 3.10 时返回 `PYTHON_VERSION_UNSUPPORTED`；mock 已安装 MCP 版本为 1.x 或 3.x 时返回 `MCP_VERSION_UNSUPPORTED`；requirements 缺失 `>=2.0.0,<3.0.0` 时返回 `MCP_REQUIREMENT_INVALID`。

- [ ] **Step 2: 运行 RED 测试**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.platform.test_validator_contract -v
```

Expected: FAIL，因为现有 validator 没有可调用报告接口，且仍输出旧 PASS。

- [ ] **Step 3: 实现运行时前置条件、ValidationReport 和 Git 检查**

`validate_runtime_prerequisites(root)` 使用 `sys.version_info`、`importlib.metadata.version("mcp")` 和 requirements 文件验证 Python >= 3.11、实际安装的 MCP 版本在 `[2.0.0, 3.0.0)`，且声明的依赖具有一致的上下界。版本解析实现为内部纯函数，并为缺包、非法版本和边界值返回稳定错误码，不新增运行时依赖。

```python
@dataclass
class ValidationReport:
    lifecycle_mode: str
    issues: list[ValidationIssue]
    warnings: list[str]
    runtime_executed: bool
    evaluated_gates: list[str]

    @property
    def ok(self) -> bool:
        return not self.issues
```

Git 检查必须使用普通 `git` 命令，不使用内置 safe-directory 绕过；要求 `rev-parse --verify HEAD` 成功，dirty 状态默认警告、`--strict` 下失败。

- [ ] **Step 4: 实现 CLI 编排**

CLI 支持 `--static-only` 和 `--strict`。完整模式组合静态问题与 MCP 运行时问题；静态模式打印 `RUNTIME CHECK: NOT EXECUTED`。任何 issue 返回 1，只有完整成功才打印完整 PASS。

- [ ] **Step 5: 运行 GREEN、负向和故障注入测试**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.platform.test_validator_contract -v
.\.venv\Scripts\python.exe scripts\validate_platform.py
.\.venv\Scripts\python.exe scripts\validate_platform.py --static-only
```

Expected: 测试全部 PASS；完整模式执行 stdio 并返回 0；静态模式返回 0 但明确标记运行时未执行和无 Gate 评估。

- [ ] **Step 6: 提交 validator**

```powershell
git add scripts/platform_validation.py scripts/validate_platform.py tests/platform/test_validator_contract.py
git commit -m "fix(validation): reject false-green platform checks" -m "Bug: BUG-001`nTask: TASK-001`nTests: python -m unittest tests.platform.test_validator_contract -v"
```

---

### Task 7: 用测试强化 Windows setup

**Files:**
- Create: `tests/platform/test_setup_contract.py`
- Modify: `scripts/setup.ps1`
- Modify: `README.md`

**Interfaces:**
- Consumes: Git、Python、requirements、完整 validator。
- Produces: `setup.ps1 -PersistLocalRoot`、`setup.ps1 -SkipDependencyInstall` 两个显式开关和可重复 setup 行为。

- [ ] **Step 1: 写 setup RED 契约测试**

```python
class SetupContractTests(unittest.TestCase):
    def test_setup_has_safe_persistence_and_exit_checks(self):
        text = (ROOT / "scripts/setup.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$PersistLocalRoot", text)
        self.assertIn("[switch]$SkipDependencyInstall", text)
        self.assertIn("if ($LASTEXITCODE -ne 0)", text)
        self.assertIn("python version must be 3.11 or newer", text.lower())
        self.assertNotIn("pip install --upgrade pip", text)
        self.assertIn("if ($PersistLocalRoot)", text)
```

- [ ] **Step 2: 运行 RED 测试**

```powershell
python -m unittest tests.platform.test_setup_contract -v
```

Expected: FAIL，因为开关和显式原生命令退出检查不存在，且仍无条件升级 pip 和持久化环境变量。

- [ ] **Step 3: 实施 setup 前置检查与显式开关**

PowerShell 参数改为：

```powershell
param(
    [string]$PythonCommand = "python",
    [switch]$PersistLocalRoot,
    [switch]$SkipDependencyInstall
)
```

脚本依次检查普通 Git 状态、Git `user.name/user.email`、Python >= 3.11、venv、受控依赖、`pip check`、知识目录和完整 validator。每次 native command 后立即检查 `$LASTEXITCODE`。只有 `$PersistLocalRoot` 才调用用户级 `SetEnvironmentVariable`。

- [ ] **Step 4: 运行 GREEN 契约测试**

```powershell
python -m unittest tests.platform.test_setup_contract -v
```

Expected: PASS。

- [ ] **Step 5: 在临时 Git clone 中连续执行两次 setup 集成检查**

```powershell
$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("codex-rd-setup-" + [guid]::NewGuid())
try {
    git clone --no-local . $tempRoot
    if ($LASTEXITCODE -ne 0) { throw "temporary clone failed" }
    & (Join-Path $tempRoot "scripts\setup.ps1")
    if ($LASTEXITCODE -ne 0) { throw "first setup run failed" }
    & (Join-Path $tempRoot "scripts\setup.ps1") -SkipDependencyInstall
    if ($LASTEXITCODE -ne 0) { throw "second setup run failed" }
}
finally {
    $resolvedTemp = [IO.Path]::GetFullPath($tempRoot)
    $resolvedBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if ($resolvedTemp.StartsWith($resolvedBase) -and (Test-Path -LiteralPath $resolvedTemp)) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}
```

Expected: 第一次安装受约束依赖并完成完整 validator；第二次复用环境且再次通过；不写用户级环境变量，不升级 pip，不产生依赖漂移。删除前必须验证临时 clone 的绝对路径仍位于系统临时目录下。

- [ ] **Step 6: 提交 setup 修复**

```powershell
git add scripts/setup.ps1 README.md tests/platform/test_setup_contract.py
git commit -m "fix(setup): fail closed on platform prerequisites" -m "Bug: BUG-001`nTask: TASK-001`nTests: python -m unittest tests.platform.test_setup_contract -v"
```

---

### Task 8: 全量验证、证据固化与独立 Gate

**Files:**
- Create: `docs/platform-maintenance/TC-001-platform-automated-validation.md`
- Create: `docs/platform-maintenance/TC-002-codex-restart-validation.md`
- Create: `docs/platform-maintenance/test-evidence-2026-08-22.md`
- Create: `docs/platform-maintenance/review-evidence-2026-08-22.md`
- Modify: `docs/platform-maintenance/BUG-001-platform-self-check-false-positive.md`
- Modify: `docs/platform-maintenance/TASK-001-platform-readiness-repair.md`

**Interfaces:**
- Consumes: Tasks 1–7 的提交与测试。
- Produces: 可审计的自动化证据、独立测试结论、独立审查结论和重启后人工验证步骤。

- [ ] **Step 1: 运行完整自动化测试**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\validate_platform.py
git diff --check
git status --short --branch
```

Expected: 所有自动化测试 PASS、`pip check` 无冲突、完整 validator 返回 0、无 whitespace error。若任何命令失败，BUG-001 保持 OPEN。

- [ ] **Step 2: 运行安全与泄密扫描**

```powershell
git grep -n -I -E "sk-[A-Za-z0-9_-]{16,}|glpat-[A-Za-z0-9_-]{10,}|BEGIN [A-Z ]*PRIVATE KEY"
```

Expected: 无匹配。不得打印用户环境变量值。

- [ ] **Step 3: 固化实际证据**

`test-evidence-2026-08-22.md` 记录每条命令、开始/结束时间、退出码、测试数量、失败数量、分支、`git rev-parse HEAD` 返回的精确提交和原始输出文件位置。只有实际执行成功的命令写 PASS；重启 Codex 验证保持 `NOT EXECUTED`。

- [ ] **Step 4: 独立 tester 验证**

Tester 必须重新运行完整测试、stdio 连续启动、setup 两次、路径边界和负向故障注入；结论写入测试证据。开发 Agent 的结果不能替代该结论。

- [ ] **Step 5: 独立 reviewer 审查**

Reviewer 检查设计符合性、MCP 子进程安全、配置路径、manifest、Gate/RTM、秘密处理、测试真实性和回归风险。所有 P0/P1 必须修复后重测重审；P2/P3 明确处置。

- [ ] **Step 6: 更新 BUG/TASK 状态并提交证据**

仅当自动化测试和独立审查实际通过时，BUG-001 改为 `RESOLVED_PENDING_RESTART`，TASK-001 改为 `IMPLEMENTED_PENDING_RESTART`。TC-002 保持 `NOT EXECUTED`，直到用户重启 Codex 并观察运行时工具。

```powershell
git add docs/platform-maintenance
git commit -m "test(platform): record independent readiness evidence" -m "Bug: BUG-001`nTask: TASK-001`nTests: python -m unittest discover -s tests -v"
```

- [ ] **Step 7: 合并前验证**

```powershell
git status --short --branch
git log --oneline --decorate main..HEAD
git diff --stat main...HEAD
```

Expected: 工作区干净；分支只包含设计、计划、修复和证据提交。

---

## 合并与重启后验收

实施分支通过独立 tester/reviewer 后，由主 Agent 按 `finishing-a-development-branch` 流程非快进合并回 `main`。合并后用户需要：

1. 关闭并重新打开 Codex 的 `D:\codex-rd-platform` 工作区；
2. 确认 `company_context` MCP 已加载；
3. 运行 MCP 工具列表并观察精确 8 个工具；
4. 将 TC-002 的浏览器/终端可见证据反馈给主 Agent。

在重启证据出现前，平台状态只能是 `IMPLEMENTED_PENDING_RESTART`，不能宣称会话级 MCP 已恢复。
