# Java Meeting-room Booking CLI

## Scope and traceability

- Task: `TASK-V3-003` (Java application slice)
- Runtime task / implementation run: `task-040d30aa16f54e84afb74dae678450ac` / `run-bd59a53bea7241e59cc9f6e790218dd5`
- Requirement: `REQ-MATRIX-JAVA`
- Source baseline: `docs/superpowers/specs/2026-09-06-multistack-selftest.md`
- Lifecycle position: development preparation under G6; independent test, review, release, and human acceptance are not executed.
- Evidence status: preflight initially found no `javac` on `PATH`. The coordinator supplied the actual JDK 8 tools: `C:\Program Files\Java\jdk-1.8\bin\javac.exe` and `java.exe` (`1.8.0_431`). Source and developer tests were then executed with those tools; independent validation remains separate.

## Initial model

This is a single-user, local command-line utility using the Java standard library and synthetic data only. A caller creates a room reservation, cancels one by its generated identifier, and lists reservations. State survives separate processes in a caller-provided local data file. There are no users, authentication, time zones, recurring reservations, concurrent writers, external services, or production integration.

The supplied requirement does not specify a command grammar, ID scheme, or storage format. The following reversible defaults are inferred to make the stated behaviour testable:

- Invocation: `booking <data-file> add <room> <start> <end>`, `booking <data-file> cancel <id>`, or `booking <data-file> list [room]`.
- Timestamps are strict ISO-8601 local date-times accepted by `LocalDateTime.parse`, for example `2026-09-06T09:00`; all comparisons therefore use one explicitly documented timezone-free representation.
- Reservation IDs are monotonically assigned positive decimal values and persisted with the reservation.
- A reservation is the half-open interval `[start, end)`. Thus `start < end` is required; same-room intervals conflict exactly when `newStart < existingEnd && existingStart < newEnd`; an end equal to the next start is allowed.
- Records use an escaped, line-oriented text format internal to the program. The loader rejects malformed data as a whole before a mutation is attempted.

## Requirements and measurable acceptance criteria

| ID | Requirement / measurable acceptance |
| --- | --- |
| REQ-MATRIX-JAVA-01 | `add` accepts a non-empty room value without record separators and two strict timestamps where `start < end`; it persists a new reservation and returns its ID. |
| REQ-MATRIX-JAVA-02 | Adding an overlapping reservation for the same room returns a non-zero exit and leaves the persisted data byte-for-byte unchanged. Non-overlapping and adjacent same-room reservations are accepted. Different rooms do not conflict. |
| REQ-MATRIX-JAVA-03 | `cancel <id>` removes exactly one existing reservation and persists the change. Unknown, malformed, or extra arguments return non-zero without a write. |
| REQ-MATRIX-JAVA-04 | `list [room]` reports committed bookings in a deterministic order and optionally limits output to exactly the requested room. |
| REQ-MATRIX-JAVA-05 | A second process reloads committed data and observes the same bookings. Malformed commands, invalid rooms/timestamps/intervals/IDs, extra arguments, and malformed persistence data are rejected without modifying data. |
| REQ-MATRIX-JAVA-06 | The application compiles and runs through manifest-v1 portable argv commands. All class files and synthetic test data are located beneath `{build}` (under `.rd-platform/build`) and are not committed. |

## Design

`Booking` is the immutable domain record (`id`, `room`, `start`, `end`). `BookingStore` owns strict read/validate, conflict detection, mutation, and temporary-file replacement. `BookingCli` parses the command line and maps expected domain/validation errors to non-zero exits. A standard-library test class invokes the domain/store directly; a separate process test invokes the compiled CLI for persistence behaviour.

Persistence is validated completely before exposing records. A mutation performs load -> validate -> calculate -> write temporary sibling -> replace, so command and conflict failures cannot alter committed data. Replacement atomicity remains filesystem-dependent, and multiple writers are outside scope.

`manifest.json` is schema version 1 with `id`, `stack`, `requirements`, `commands`, `native_validation`, and `entrypoint`. Its commands are argv arrays only; they use `{app}`, `{build}`, `{java}`, and `{javac}` placeholders, with compiler output restricted to `{build}`.

## Risk-driven test model

| Test ID | Requirement | Type | Risk | Input / steps | Expected result | Automation |
| --- | --- | --- | --- | --- | --- | --- |
| TC-JAVA-001 | REQ-MATRIX-JAVA-01 | Unit | Invalid interval or timestamp accepted | Add valid booking; try invalid timestamp and equal/reversed endpoints. | Valid booking exists; each invalid case fails without write. | Standard-library Java test executable |
| TC-JAVA-002 | REQ-MATRIX-JAVA-02 | Unit | Double-booking or false conflict | Add `[09:00,10:00)`; add overlap, adjacency, and another-room overlap. | Overlap fails byte-stable; adjacent and other-room cases pass. | Standard-library Java test executable |
| TC-JAVA-003 | REQ-MATRIX-JAVA-03 | Unit | Cancellation deletes wrong record | Seed two records; cancel one; try missing/invalid ID. | Only target removed; invalid cases do not write. | Standard-library Java test executable |
| TC-JAVA-004 | REQ-MATRIX-JAVA-04 | Unit | Nondeterministic/incorrect listing | Insert out-of-order rooms/times and filter one room. | Stable documented order; filter contains only requested room. | Standard-library Java test executable |
| TC-JAVA-005 | REQ-MATRIX-JAVA-05 | Unit | Corrupt data partially accepted | Use malformed, duplicate-ID, invalid-time, and invalid-interval data files. | Each is rejected; no mutation occurs. | Standard-library Java test executable |
| TC-JAVA-006 | REQ-MATRIX-JAVA-05 | Unit | CLI accepts ambiguous input | Empty room, separators, bad timestamp, non-decimal ID, extra args. | Non-zero exit and byte-stable persistence. | CLI subprocess test |
| TC-JAVA-007 | REQ-MATRIX-JAVA-05 | Integration | Commit is not durable | Add in one CLI process; list/cancel in fresh processes. | Later process reads exact prior committed state. | CLI subprocess test |
| TC-JAVA-008 | REQ-MATRIX-JAVA-06 | Integration | Non-portable/untracked build | Expand and run manifest build/unit/integration argv. | Compile and tests use only `{build}` outputs. | Runtime harness / independent QA |

## Boundary and open evidence

The Runtime implementation run was started before the agent received its task. This document records the actual run ID but does not imply successful implementation. The preflight compiler absence was resolved by a coordinator-supplied JDK 8 path. The RED compile first failed because the planned `Booking`, `BookingStore`, and `BookingException` types did not exist; it then passed after the minimal implementation. Independent QA, independent review, release packaging, and human/system acceptance remain `NOT_EXECUTED`.

## Developer verification evidence

| Evidence | Command / result | Status |
| --- | --- | --- |
| RED-TC-JAVA-001 | `javac -encoding UTF-8 -d .rd-platform/build/java_booking/classes examples/multistack/java_booking/src/booking/BookingStoreTest.java` initially failed with 20 unresolved references to planned `BookingStore`, `Booking`, and `BookingException` types. An earlier directory-missing invocation was an environment/setup failure and is not used as the RED assertion. | OBSERVED |
| EVD-JAVA-001 | `C:\Program Files\Java\jdk-1.8\bin\javac.exe -encoding UTF-8 -d .rd-platform\build\java_booking\classes` followed by the six source paths declared in `manifest.json`; exit 0. | OBSERVED |
| EVD-JAVA-002 | `C:\Program Files\Java\jdk-1.8\bin\java.exe -cp .rd-platform\build\java_booking\classes booking.BookingStoreTest .rd-platform\build\java_booking\unit-data`; `BookingStoreTest: 18 assertions passed`, exit 0. | OBSERVED |
| EVD-JAVA-003 | `C:\Program Files\Java\jdk-1.8\bin\java.exe -cp .rd-platform\build\java_booking\classes booking.BookingCliProcessTest .rd-platform\build\java_booking\integration-data`; `BookingCliProcessTest: 11 assertions passed`, exit 0. | OBSERVED |
| EVD-JAVA-004 | `git diff --check`; exit 0. It emitted only CRLF conversion warnings for shared files outside this application's ownership. | OBSERVED |

The developer-owned checks cover TC-JAVA-001 through TC-JAVA-008. They are not independent QA or code review evidence and do not establish G7/G8, release, or final system acceptance.

The first Runtime completion attempt for `run-bd59a53bea7241e59cc9f6e790218dd5` failed before any state write with `ModuleNotFoundError: No module named 'rd_platform.lifecycle'`; that shared lifecycle dependency was outside this application's ownership. After the coordinator restored it, the same run was finished `PASS` with the actual compiler, source list, manifest/document references, and `18 + 11 = 29` developer assertions as evidence. The task is now `READY` for an independent `unit` phase; these results remain developer evidence only and do not establish independent QA, review, release, or final acceptance.

## Review remediation: REV-V3-APP-005

The independent review in `docs/platform-v3/app-review.md` found that `BookingCliProcessTest` always constructed `<java.home>/bin/java.exe`, violating the portable-manifest acceptance on Linux/macOS. Retry implementation run `run-67cf7bf52ef04ddfaec62d5e56754a0b` replaces that hard-coded suffix with `javaExecutableName(osName)`: Windows resolves `java.exe`; other operating-system names resolve `java`. The test first failed to compile with the three planned `javaExecutableName(String)` calls unresolved (RED). After implementation, the same real Windows JDK 8 compile passed; `BookingStoreTest` reported 18 assertions and `BookingCliProcessTest` reported 14 assertions, including explicit Windows/Linux/macOS executable-name resolution. This is a platform-neutral unit assertion only: no Linux/macOS process was executed or claimed.

## Skill usability observation

`platform-orchestration` correctly required a Runtime snapshot and real host/task/run identity before claiming work. Its general guidance does not prescribe how an application worker should represent an unavailable language compiler in a manifest before source exists; this task records the absence explicitly and defers the manifest command choice rather than inventing an executable path.
