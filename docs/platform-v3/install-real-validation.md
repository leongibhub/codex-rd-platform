# Real isolated installation validation

Task: `TASK-V3-015`; defects: `BUG-INSTALL-001`, `BUG-INSTALL-002`.

This is a local temporary installation check, not production deployment,
human identity authentication, a release, or a project Gate decision.

## First attempt: observed FAIL

- Source: committed and pushed `c3eb271089c0599b54775b2b4d3cb1c349a62bd0`.
- Date: 2026-09-06.
- Entry: Windows PowerShell `install-to-D.ps1 -Destination <new temporary directory>`.
- Target basename: `codex-rd-install-verified-a3c420551f4346cc91e9eade85a5e8c7`.
- The process received explicitly synthetic Git name/email through process-only
  `GIT_CONFIG_*` variables. No global Git identity was changed or represented as
  a human signature. `COMPANY_LOCAL_ROOTS` pointed to the new target's local
  knowledge directory; it did not reuse private source knowledge.
- Actual exit: `1`, during committed-tree preflight.
- Actual error: `Committed source contains delivery-blocked sensitive/local
  path(s): knowledge/local/README.md.`
- No source payload or dependency setup was executed. The new directory retained
  `.install-failed`; it was not deleted or relabelled as installed.

The public repository contains a non-sensitive knowledge-policy stub at exactly
`knowledge/local/README.md`, Git blob `f361c8f3bd3b7bb62af25fb46bb48c0965c2e263`.
Its content was read from the committed Git tree. The original isolated test
fixtures omitted this real repository artifact and therefore did not expose
the false positive. This is an actual product packaging defect, not a successful
installation or a dependency/network failure.

`BUG-INSTALL-002` reopens TASK-V3-015 as revision 2. The fix must allow only this
exact reviewed public path and content, while rejecting modified stubs and all
other prohibited local knowledge/state. The initial failure and previous
scoped fixture results remain history. A new committed-source attempt must run
the normal setup before this document can record real installation PASS.
