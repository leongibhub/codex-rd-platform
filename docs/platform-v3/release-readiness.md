# V3 发布就绪性与交付边界

后续事实：源码已冻结并推送提交 `6665bc5`，见[交付记录](delivery-record.md)。以下保留提交前发布评估快照；“待固定 Git 版本”已由该记录解决，生产发布/验收限制并未因此解除。

- 文档状态：`DRAFT`
- 评估时间：`2026-09-06T17:46:40+08:00`
- 评估对象：本轮检查时仍未提交的 V3 工作区；非已标记版本、非生产环境。正在准备受控 Git 提交和交付记录，但尚无可引用的提交 SHA 或版本标签。
- 结论：**未具备发布建议条件**。这不是 G10 决定：顶层仍为 `template` 模式，未创建本项目的权威 Gate Register，也没有 G10 assessment/decision、部署、回滚演练或人工验收证据。

## 发布材料完整性检查

| 交付项 | 观察到的材料 | Evidence Status | 对发布的影响 |
| --- | --- | --- | --- |
| 设计与范围 | [V3 设计](../superpowers/specs/2026-09-06-platform-v3-design.md)、多栈验收基线 | OBSERVED | 可作为实施基线，不是批准 |
| 本地操作说明 | [README](README.md)、Harness 与五个 manifest | OBSERVED | 有本地重放路径，仍需按目标环境验证 |
| 源码与变更版本 | 本轮检查时工作区有 V3 未提交新增/修改；基线是 `9655f33`，正在准备受控提交 | OBSERVED | 在实际提交产生前，仍缺冻结 SHA/版本标签/交付变更清单 |
| 本地回归 | 协调者最终报告：V3 runtime 128 PASS / 27.223s、原平台 98 PASS / 45.022s、旧样例 19 PASS / 11.309s | OBSERVED | 是当前本地回归，不是目标环境部署或性能基准 |
| Harness 独立测试 | 初次 FAIL 保留；最终独立 Harness 11 PASS、1 NOT_EXECUTED（symlink 权限）且任务 review DONE | OBSERVED | 缺失链接能力不能写成 PASS |
| 五应用独立测试 | C++/Python/Web/Java/微信 Node 结果及五条真实 Test Execution PASS；浏览器另有实际 5 flow | OBSERVED | 微信原生范围仍未覆盖；聚合 case 不等于全需求/NFR 覆盖 |
| 五应用生命周期登记 | 每应用已有 REQ/CODE→legacy model v1 adopt→model/case v2→environment/evidence→新独立 PASS execution；v1 来源仍 `NOT_AVAILABLE`；`lifecycle-report` 为当前聚合 Case PASS、`recommend_release=false` | OBSERVED | 每项 G0 仍 IN_REVIEW、G7 candidate BLOCKED，均无 Gate decision；详见[追踪验证](live-lifecycle-validation.md) |
| Web 浏览器验证 | 内置浏览器实测创建、文本 XSS、刷新、编辑、搜索、删除均 PASS | OBSERVED | 单浏览器且未注入存储拒绝；不建立跨浏览器结论 |
| 独立审查 | [app-review](app-review.md) 保留初次 `NOT APPROVED`，随后对当前应用源码范围 `APPROVED`，REV-001..006 已解析 | OBSERVED | 范围不含微信原生、非 Windows Java 或生产运行 |
| 独立 runtime 审查 | [runtime-review](runtime-review.md) 复验 4 P1、6 P2 后，当前 scoped V3 runtime/lifecycle/harness/adapter 结论 `APPROVED` | OBSERVED | review 不是 Gate/发布/验收；symlink capability 未执行 |
| 缺陷状态 | 五应用历史 QA/review defect 已 `CLOSED`，Harness/核心历史失败保留并有重测/复审证据 | OBSERVED | 历史 FAIL 不是当前发布失败，但也不应删除 |
| Release manifest/包 | `stack-package` 可生成本地 ZIP+摘要 | OBSERVED | 生成包不是 `REL-*` 交付清单，也不是发布 |
| 安装/部署/回滚演练 | 本页与 README 提供步骤；无目标环境执行记录 | NOT_EXECUTED | 不能声明可部署或可回滚成功 |
| 已知问题与风险接受 | 限制已列出；无人工接受风险记录 | OBSERVED | 未经人明确接受，不能带 blocker/critical 风险推荐发布 |
| 客户/业务验收 | 无 | NOT_EXECUTED | G9 不可通过 |

## 当前阻碍发布建议的事项

1. 完成正在准备的受控 Git commit、变更清单和可再现环境；在实际提交产生前，不能把工作区快照称为已交付版本。
2. 若需声明设计容量目标，执行 100 项目/10 万工件版本/100 万事件的容量基准；当前没有该结果，必须保持 `NOT_EXECUTED`。
3. 对 Web 补跨浏览器与浏览器级存储拒绝测试；对微信在可用 IDE/真机完成导入、原生运行和真实存储验证。没有这些工具时，明确保持 `NOT_AVAILABLE`/`NOT_EXECUTED`。
4. 如涉及 G9–G11，提供已认证的 approval provider；当前默认拒绝人工批准登记，状态为 `NOT_AVAILABLE`。
5. 若要实际发布，创建受控 `REL-*`、交付清单、目标环境安装步骤、已知问题、回滚方案和真实操作员证据；之后才可进行 G10 assess/有权人 decide。生产部署及客户验收需要各自独立事实。

## 本地交付、安装与回滚候选步骤

这些步骤是可执行候选，不是已执行结果：

```powershell
# 固定候选提交后，先在干净副本验证工具和测试。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-probe
& .\.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_stack_harness -v
& .\.venv\Scripts\python.exe -X utf8 -m unittest tests.independent_v3.test_stack_harness_independent -v

# 为每个适用应用生成本地可核验归档；仅将 manifest 允许的源文件加入。
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\cpp_inventory\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\python_expenses\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\web_notes\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\java_booking\manifest.json
& .\.venv\Scripts\python.exe -X utf8 -m rd_platform stack-package examples\multistack\wechat_expenses\manifest.json
```

交付前记录 ZIP SHA-256、源摘要、Git SHA、运行命令、环境与操作者。若回退：先停止写入者并备份状态库，再用经审查的 Git revert 或已知版本恢复代码；V3 `lc_` 表不应由回退脚本删除。已真正进入 release 域的回滚必须额外调用并留存 `release.rollback` 事实，不能把“代码已切回”写成生产回滚成功。

## Gate 与证据分离

当前可记录的是发布准备材料的 `OBSERVED`/`NOT_EXECUTED` 状态。只有 active 项目中央 Gate Register 中、带真实可解析证据的有权决定，才允许 Gate Status 取 `PASS`、`FAIL` 或 `BLOCKED`。本页不使用 Gate Status，也不把 Harness `PASS`、ZIP 创建、看板读取或模板校验转换为 G10 `PASS`。
