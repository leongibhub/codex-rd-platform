# Java 8 干净构建修复

任务 `TASK-V3-012`，缺陷 `BUG-CI-002`，关联 `REQ-MATRIX-JAVA` / `REQ-MATRIX-JAVA-06`。本轮实现者是实际宿主 `/root/v3_skill_forward`；Runtime task `task-9fe93a6e2e9e484a8db6c886854ce134`，implementation run `run-91f23f721f1347378a52052cf3771821` 由主协调者管理。本文是开发者实施证据，不是独立 QA、Review、Gate 或发布结论。

## 事实、设计与边界

协调者提供的实际 CI 证据：run `34029576291`、Ubuntu job `101476522773`、commit `a55e3ce` 的 Java build 退出 2，`javac: directory not found: .../classes`。原 manifest 直接向不存在的 `-d .../classes` 编译；既有本机目录曾掩盖 JDK 8 的目标目录前置条件。该外部失败不被本地成功覆盖。

接受的最小设计是应用拥有构建目录创建：manifest 通过 Python `-B` 调用本目录 `build.py`，传入原 `{javac}` 和 `{build}`，检查路径后创建 `classes`，再以无 shell 的 argv 数组调用同样的六个 Java 源文件。未降低 Java 8 要求、未改任何 Java 业务源文件、未在 CI 中预建 classes。Python lifecycle harness、其 v4 SHA 及其文档未改。

构建输出必须是仓库 `.rd-platform/build` 的应用子目录。拒绝相对路径、父目录穿越、源码目录/仓库外目录、build 基目录本身，以及输出祖先或已存在 classes 树里的 symlink/junction/reparse point。空格与 shell 元字符保留为单个 argv 参数，不执行 shell。编译非零退出码原样传递；路径/启动/超时错误非零退出。此路径检查不是针对并发恶意进程的文件系统沙箱。

## 实际 RED → GREEN

本机 `stack-probe` 观察到 javac 和 Java 可用。实际版本命令输出 `javac 1.8.0_431`、`java version "1.8.0_431"`；编译器为 `C:\Program Files\Java\jdk-1.8\bin\javac.exe`。测试首先新建带空格的隔离 workspace、复制现有应用，确认 classes 不存在后调用公开 manifest executor。

最初两次本地测试资产误用了 `phases` 返回形状：分别 TypeError 和后续阶段不存在时的 KeyError；修正断言读取后再判定产品 RED。这两次资产错误不归责应用。有效 RED 为1例 FAIL、0.700s、退出1；真实 JDK 8 build 退出2、classes 不存在，后续 unit/integration 未运行。

修复后新增8项契约/集成检查全部通过，与既有 stack harness 13项合计 **21/21 PASS，7.772s，退出0**：

```powershell
& .\.venv\Scripts\python.exe -B -X utf8 -m unittest tests.runtime.test_java_clean_build tests.runtime.test_stack_harness -v
```

| 新检查 | 实际断言 |
| --- | --- |
| 干净 Java 8 manifest build/unit/integration | classes 最初不存在；三阶段退出0；Java字节码版本52；源码树摘要不变且无class文件 |
| 真实编译失败 | 仅隔离副本加入无效Java fixture；build非零/FAIL，后续阶段未执行 |
| 公共 build.py 逃逸参数 | 进程非零，未创建目标 |
| 源码/外部/相对/父穿越/build基目录 | 全部在启动编译器前拒绝 |
| 空格与shell元字符 | 原样作为argv单参数；shell=False |
| 编译器非零契约 | 模拟exit7原样返回，不转换PASS |
| 输出祖先链接 | 实际symlink或Windows junction拒绝，目标未写 |
| classes内部链接 | 已有booking链接拒绝，外部目标为空 |

最终另一次实际干净 manifest 执行观察为 build退出0；unit输出 `BookingStoreTest: 18 assertions passed`；integration输出 `BookingCliProcessTest: 14 assertions passed`。这是本机开发者验证，Ubuntu CI重跑与独立QA/Review仍由协调者安排。

## 冻结与历史来源

当前工作树应用 source_sha256 为 `98a989a5e88447caef30285678fe8ad53afcd6a76287c64f4db550c825e1da42`；原 manifest 应用基线为 `038a4340b53e722a455e79546f631266297e46acc982af4686179e61ebb62ddb`。新增build.py及manifest变化意味着旧Java来源证据对本次来源已过期（STALE），旧PASS仅保留为历史执行，不能宣称已经覆盖新构建流程。本任务未借用原Java测试者身份、未修改旧execution/EVD以伪装最新结果；当前版本需独立质量阶段及新的CI提交证据。

冻结文件SHA-256：

- build.py：`6a3648acbd398cd8a11b8d41e7d46ab1587eb2903f17fbb5aa28b7fb738c3856`
- manifest.json：`b089e5fc28ad7b4047332cde400f3cd7715e9fecf0f8cd3a50eb89c06ed0257d`
- test_java_clean_build.py：`4354ff9997ddc5c12741f0525c586374ef50357e0cb9a2908affcf34b6099470`

未commit、未安装工具、未部署；旧CI失败、旧Java历史PASS与本次本机验证各自保持事实边界。

## Attempt 2：真实 Runtime 模式揭示的测试夹具编码问题

独立QA的正式 unit FAIL 为 `run-3bc7d50bf08f44ceb9578409b206da7d`：21例中2 errors，分类为TEST_SCRIPT，原失败保留。最初传递的另一个run ID及“Mock干扰”猜测并未证实；核对显示两个link_directory调用均在编译器mock之前。主因是Runtime隐藏进程里symlink创建实际报WinError1314后，cmd mklink输出中文字节，Python `-X utf8` 的 `text=True` reader线程解码失败，stdout成为None，进而触发拼接TypeError。

开发者通过同一 `rd_platform.runner.run_command` 执行两个链接测试，真实重现2 errors（先UTF-8字节0xb4解码错误，再NoneType拼接错误）。普通终端直跑21例仍通过，因此之前的开发者PASS不替代该Runtime模式失败。

本次只修改开发者测试夹具：mklink改为捕获bytes，用 `mbcs` / `errors=replace` 处理诊断，仍严格断言进程退出码；真实链接仍先于编译器mock创建。新增强制symlink权限拒绝分支，只有权限缺失是注入fixture，junction命令和中文路径的文件系统链接是真实创建并核验的。未改生产build.py、manifest、Java业务源码、QA文件或Python lifecycle。

父协调者登记attempt 2 implementation `run-9c182dbe740d4a20973afedff1543352`。修复后通过 `run_command` 以 `-B -X utf8 -m unittest tests.runtime.test_java_clean_build tests.runtime.test_stack_harness -v` 启动，实际 **22/22 PASS，7.486s**；runner退出0、duration_seconds=7.883583、无超时/截断/launch_error。这是开发者同模式验证，独立QA重跑和Review仍由实际责任人完成。

修复后的测试文件冻结SHA-256为 `9c23eb128b0fb7f92e91645fa6a858591c35e416bc91ad3b18b09a8f2f83d1dd`；上节build.py、manifest和应用source摘要保持不变。旧测试文件摘要保留为attempt 1历史。
