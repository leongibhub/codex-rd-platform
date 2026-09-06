# TASK-V3-012/013 Independent CI build QA

Execution owner: `/root/v3_qa_apps` (independent Tester)  
Date: 2026-09-06  
Status: `TASK-V3-012` retry unit/integration and `TASK-V3-013` revision-2 unit/integration are current and ready for review. Historical failed/superseded records remain below.

## Scope, risks, and evidence rule

This plan derives from the first GitHub CI observations: a fresh Ubuntu Java build failed because its classes output directory did not exist, and Windows native C++ was not runnable after the compiler probe path/DLL handling was insufficient. It covers only local adapter behavior and workflow contract. It does not convert a mock, a Windows tool probe, Node adapter output, or a local compiler discovery into GitHub-hosted native C++ PASS evidence.

| Test case | Requirement/risk | Preconditions and data | Steps / expected observable result | Current state |
| --- | --- | --- | --- | --- |
| TC-CI-IND-1201 | `REQ-MATRIX-JAVA`; clean JDK 8 compilation can fail when `classes` is absent | New temporary workspace; copied `java_booking`; real `javac` and `java` report version 1.8 | Invoke public `stack-run` for build/unit/integration. Expect three PASS phase records, generated class files only in `<workspace>/.rd-platform/build/java_booking/classes`, and byte-identical copied sources. | PASS: `run-8b583f11e72e46829967dc8701749379`. |
| TC-CI-IND-1202 | `NFR-V3-003`; generated output escapes root/traverses parent | Same isolated workspace, actual JDK 8, build helper targets outside root, source tree, parent and relative paths | Expect `ValueError` before compilation and no outside directory creation. | PASS: `run-8b583f11e72e46829967dc8701749379`. |
| TC-CI-IND-1203 | `NFR-V3-003`; link/junction redirects build artifacts | Same workspace; real directory symlink or Windows junction inside an existing `classes` tree | Invoke the helper's exact `classes_directory` validation with the isolated root. Expect explicit symlink/junction/reparse rejection and no file below the external target; lexical root rejection alone is not evidence for this case. | PASS: `run-8b583f11e72e46829967dc8701749379`. |
| TC-CI-IND-1204 | `TASK-V3-013`; `JAVA_HOME` executable suffix must match the real CI OS | Fresh subprocess using the current OS Python; a temporary `JAVA_HOME/bin/java.exe` on Windows or `JAVA_HOME/bin/java` on Linux | Import production resolver without mocking OS and expect its native suffix path. This is path-selection evidence only, not a Java execution PASS. | PASS: `run-049c8d9d1cf2418aabca9b610811d56b`. |
| TC-CI-IND-1205 | `TASK-V3-013`; Windows GNU tool discovery/DLL preparation must not be misrepresented | Actual local `stack-probe`; workflow YAML | Assert probe reports only AVAILABLE/NOT_AVAILABLE plus existing path when available; assert workflow requires `g++.exe`, its `libstdc++-6.dll` location and `$GITHUB_PATH`, with no `continue-on-error`. A live Windows GitHub compiler/run remains required. | PASS: `run-049c8d9d1cf2418aabca9b610811d56b`. |

## Planned command and reporting

After `/root` confirms each developer implementation is frozen and the matching Runtime task is READY, run the developer unit command followed by:

```powershell
.venv\Scripts\python.exe -X utf8 -m unittest tests.independent_v3.test_ci_build_independent -v
```

Register results sequentially using tester identity `/root/v3_qa_apps` for Java task `task-9fe93a6e2e9e484a8db6c886854ce134` and native task `task-ef5124d4909940758962ca113a8854b4`. Any fail will be recorded through the Runtime failure flow without source changes or a skip-to-green workaround.

## Actual phase evidence

| Task / phase | Runtime run | Actual command / observable result | Status |
| --- | --- | --- | --- |
| TASK-V3-012 unit | `run-3bc7d50bf08f44ceb9578409b206da7d` | `.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_java_clean_build tests.runtime.test_stack_harness -q`; 21 tests, 2 errors, exit 1. The record first shows UTF-8 `UnicodeDecodeError` reader-thread failures for Chinese `cmd /c mklink /J` output, then two link fixtures hit `TypeError` concatenating `None + str`. | FAIL / `TEST_SCRIPT` fixture encoding; implementation retry required. |
| TASK-V3-012 retry unit | `run-fa6beb4a5eeb4aa488908521801dd0cd` | Same developer command after the bytes-capture/`mbcs` fixture correction; 22 tests, exit 0, 7.782441s. | PASS |
| TASK-V3-012 independent integration | `run-8b583f11e72e46829967dc8701749379` | TC-1201 clean copied-workspace CLI build/unit/integration, TC-1202 outside/traversal rejection, and TC-1203 explicit link/junction/reparse branch; 3 tests, exit 0, 6.895139s. | PASS |
| TASK-V3-013 unit | `run-80b1bcc7e4794d75887d4473559829ed` | `.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_native_tool_probe tests.platform.test_ci_contract tests.runtime.test_stack_harness -q`; 18 tests, exit 0, 1.828541s. | PASS |
| TASK-V3-013 independent integration (historical) | `run-377e593ecc8c4653b98f956d772c530b` | The former WSL-specific TC-1204 plus TC-1205; 2 tests, exit 0, 4.110221s. | PASS, but superseded by fixture-contract correction; do not use as current evidence. |
| TASK-V3-013 revision-2 unit | `run-be0a5fe7db204e86b748493bbd1478ac` | Same frozen developer suite; 18 tests, exit 0, 1.873276s. | PASS |
| TASK-V3-013 revision-2 independent integration | `run-049c8d9d1cf2418aabca9b610811d56b` | Corrected current-OS TC-1204 plus TC-1205; 2 tests, exit 0, 0.785828s. | PASS |

The current full independent suite directly qualified 5/5 PASS in 8.037s. TC-1203 uses raw-byte capture and `mbcs` replacement decoding only for a failed `cmd /c mklink /J` diagnostic, avoiding unsafe UTF-8 decoding of Windows code-page output; it still requires the helper's explicit symlink/junction/reparse rejection. TC-1204 no longer requires a WSL distribution on a Windows CI runner: each CI OS runs the production resolver with its own Python and its own expected filename (`java.exe` on Windows; `java` on Linux). The direct qualification is supplemental to the current Task 012 and Task 013 Runtime phase evidence above.

## Explicit limits

- GitHub Actions online Ubuntu/Windows execution, Windows native GNU DLL loading, and the original `0xC0000139` recovery are **NOT_EXECUTED** until a real hosted workflow run and its evidence are read.
- The current-OS `JAVA_HOME` test only validates executable-name resolution; it neither invokes Java nor proves a Java toolchain is installed. Linux execution evidence must come from the Ubuntu CI runner; Windows does not assume WSL is installed.
- No browser, WeChat IDE/device, production database, Gate decision, release, or human approval is in scope.
