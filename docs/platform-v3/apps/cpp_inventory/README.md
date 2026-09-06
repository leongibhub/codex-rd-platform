# C++ Inventory CLI

## Scope and traceability

- Task: `TASK-V3-003` (C++ application slice)
- Requirement: `REQ-MATRIX-CPP`
- Source baseline: `docs/superpowers/specs/2026-09-06-multistack-selftest.md`
- Runtime status: implementation active as `run-afdc4512474f4eef8ac96b7afe7a0c43` for `task-bee072b4c58e4cd99f5df51a484ba7cb`. The available compiler is WSL Ubuntu 22.04 `/usr/bin/g++` 11.4; no Windows-native C++ compiler is available. Results will be recorded as WSL validation only.

## Initial model

The tool is a single-user, local command-line inventory utility using only C++ standard-library facilities and synthetic test data. A user can add stock, deduct stock, inspect one SKU, and list all SKUs. Inventory survives a new process through a local file supplied by the caller. There are no accounts, concurrent writers, external services, or production integration in scope.

## Requirements and acceptance criteria

| ID | Requirement / measurable acceptance |
| --- | --- |
| REQ-MATRIX-CPP-01 | `add <sku> <quantity>` accepts a non-empty SKU without separators and a non-negative integer quantity, then persists the increased value. |
| REQ-MATRIX-CPP-02 | `deduct <sku> <quantity>` accepts a non-negative integer quantity only when the existing stock is sufficient; insufficient or absent stock returns a non-zero result and leaves the persisted data unchanged. |
| REQ-MATRIX-CPP-03 | `get <sku>` reports the current stock for an existing SKU; an absent SKU returns a non-zero result. `list` reports all SKU/quantity entries in deterministic SKU order. |
| REQ-MATRIX-CPP-04 | The persistence file is reloaded by a separate process and yields the same committed inventory. |
| REQ-MATRIX-CPP-05 | Malformed persistence data, malformed commands, empty/invalid SKU, negative/non-integer/overflow quantity, and extra arguments are rejected with a non-zero result and no write. |
| REQ-MATRIX-CPP-06 | The application compiles and runs through the portable manifest-v1 argv commands; generated binaries and test data are confined to `{build}` under `.rd-platform/build` and are not committed. |

## Design

The executable will use the explicit form `inventory <data-file> <command> [arguments]`. The data file is a UTF-8 text file with one `sku<TAB>quantity` record per line; SKU validation forbids tab, newline, and whitespace, allowing unambiguous parsing. Loading validates every complete record before exposing any state. Mutations follow load → validate → calculate → write a temporary sibling file → rename, so rejected input and insufficient deductions never alter the committed file. The precise atomicity guarantees of replacement remain filesystem-dependent; multi-process concurrency is excluded.

`inventory.hpp` will contain the domain and persistence API, `inventory.cpp` its implementation, `main.cpp` CLI parsing, and `test_inventory.cpp` standard-library unit tests. The manifest will use only argv arrays and `{root}`, `{app}`, `{build}`, and `{cxx}` placeholders. It will declare the platform-specific build invocation chosen after the host reports the actual compiler.

## Risk-driven test model

| Test ID | Requirement | Type | Risk | Input / expected result | Automation |
| --- | --- | --- | --- | --- |
| TC-CPP-001 | REQ-MATRIX-CPP-01 | Unit | Incorrect accumulation | Add 3 then add 2 to one SKU; value is 5. | C++ test executable |
| TC-CPP-002 | REQ-MATRIX-CPP-02 | Unit | Stock becomes negative / failed deduction writes | Deduct more than available; error and file bytes unchanged. | C++ test executable |
| TC-CPP-003 | REQ-MATRIX-CPP-03 | Unit | Nondeterministic list | Seed unordered SKU insertion; list is lexical by SKU. | C++ test executable |
| TC-CPP-004 | REQ-MATRIX-CPP-04 | Integration | Commit not durable across processes | Mutate in one invocation and query in a fresh invocation; quantity remains. | shell-free manifest argv integration command |
| TC-CPP-005 | REQ-MATRIX-CPP-05 | Unit | Bad persisted data partially accepted | Load malformed line, duplicate SKU, negative or overflow quantity; reject without mutation. | C++ test executable |
| TC-CPP-006 | REQ-MATRIX-CPP-05 | Unit | CLI accepts ambiguous input | Empty SKU, whitespace SKU, `-1`, `1.0`, overflow, and extra arguments each fail. | C++ test executable |
| TC-CPP-007 | REQ-MATRIX-CPP-06 | Integration | Non-portable or untracked output | Expand/run manifest build, unit, integration argv commands; outputs remain beneath `{build}`. | Runtime harness / independent QA |

## Open boundary

`REQ-MATRIX-CPP` does not prescribe a command grammar or file format. The choices above are reversible local defaults that satisfy the specified behavior. No human approval, independent QA/review, release, or system acceptance is claimed by this document.

## Developer verification evidence

- RED (before production source): WSL `/usr/bin/g++ -std=c++17 -Wall -Wextra -Werror examples/multistack/cpp_inventory/test_inventory.cpp ...` failed as expected because `inventory.hpp` did not exist.
- GREEN build: `& .\.venv\Scripts\python.exe -X utf8 examples\multistack\cpp_inventory\verify.py --phase build` returned exit 0 using WSL Ubuntu 22.04 g++ 11.4.
- GREEN unit: `& .\.venv\Scripts\python.exe -X utf8 examples\multistack\cpp_inventory\verify.py --phase unit` returned exit 0 and executed TC-CPP-001/002/003/005/006 (5 tests).
- GREEN integration: `& .\.venv\Scripts\python.exe -X utf8 examples\multistack\cpp_inventory\verify.py --phase integration` returned exit 0, including a separate-process reload and a byte-preservation check for insufficient deduction.

An intermediate unit rerun initially failed because its old synthetic `add-and-reload.tsv` fixture was reused. The test setup was corrected to delete only each named fixture within the caller-provided `{build}/unit` directory; the final unit rerun passed. This was a test-isolation correction, not a persisted-inventory failure.

All generated binaries and synthetic data observed in `.rd-platform/build/cpp_inventory`. This is developer evidence only; independent test and review remain `NOT_EXECUTED`.
