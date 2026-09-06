# Committed-only local installation transfer

Traceability: `TASK-V3-015`, `BUG-INSTALL-001`, `NFR-V3-004`.

## Scope and design

`install-to-D.ps1` is a local delivery helper, not a release or acceptance
mechanism. It first resolves one committed source SHA and inspects that exact
tree. It then initializes a fresh destination repository, fetches only that
SHA at depth one, and makes a detached checkout of that same SHA. This is
intentionally not a Git archive: `scripts/setup.ps1` requires an existing Git
worktree and `HEAD`. Pinning inspection, fetch, and checkout to one SHA means
a concurrent source-HEAD update cannot bypass the checked denylist.

The destination contains only a depth-one Git record necessary for setup; it
does not copy the source `.git` directory, remote configuration, complete
history, worktree state, ignored files, caches, or local secrets. The fresh
repository has detached `HEAD` and no configured source remote. It also does
not copy source-local Git identity: `scripts/setup.ps1` therefore continues to
require a visible `git user.name` and `git user.email` in the target process
configuration (for example, an already configured user/global identity).

The installer rejects `-Force`, a non-empty or non-directory destination, the
source itself, any source descendant, any source-path ancestor containing a
reparse point, and a destination path containing a reparse point. It never
deletes or merges into an existing destination. A new destination that fails
initialization, fetch, checkout, or setup may retain `.install-failed` with a
plain failure marker; it is never reported as installed. An empty ordinary
directory is allowed as the caller-selected new delivery location.

Before cloning, the committed tree is inspected and delivery fails closed if it
contains `.git`, `.venv`, `.rd-platform`, `.env`, `.worktrees`,
`.pytest_cache`, `__pycache__`, `knowledge/local`, or `cache` paths. The only
exception is the exact path `knowledge/local/README.md` when its Git blob is
exactly `f361c8f3bd3b7bb62af25fb46bb48c0965c2e263`, the reviewed public rule
stub. The Git path comparison is case-sensitive: a same-blob case variant is
not the exception. A changed stub, any sibling/descendant local-knowledge
file, or a file at another path remains blocked. This is a limited path
denylist, not a general secret-scanning or DLP claim.
`scripts/setup.ps1` remains unchanged and runs normally after a successful
transfer; its own Git identity, Python, dependency, and validation
preconditions still apply.

The static source/destination reparse checks and the fixed-Git-SHA sequence are
not a filesystem sandbox and do not claim immunity to a malicious concurrent
filesystem replacement after validation. They prevent the observed ordinary
path/link and source-HEAD race classes within this local helper's scope.

## Developer tests

| ID | Requirement / risk | Observable result |
| --- | --- | --- |
| TC-INSTALL-015-01 | committed-only delivery | Isolated Git fixture transfers a tracked file, preserves a depth-one detached Git worktree for setup with no remote, and excludes ignored `.env`, `.venv`, and `.rd-platform`. |
| TC-INSTALL-015-02 | no overwrite | Existing non-empty target and `-Force` are rejected; original target content remains. |
| TC-INSTALL-015-03 | path containment | Source/equal and descendant targets, source junction ancestry, and a junction/reparse target are rejected. |
| TC-INSTALL-015-04 | sensitive tracked paths | Each committed `.env`, `.worktrees`, `.pytest_cache`, `__pycache__`, or `cache` path blocks delivery before fetch and records the new-target failure marker. |
| TC-INSTALL-015-05 | fixed-tree race boundary | Static contract asserts that inspection, depth-one fetch, and detached checkout use the same captured SHA. |
| TC-INSTALL-015-06 | canonical local knowledge exception | The approved stub transfers; its modified content, same-blob case-variant path, or any bystander local file is rejected before fetch. The repository fixture confirms the approved blob identity. |

Executed developer command:

```text
.venv\Scripts\python.exe -X utf8 -m unittest tests.platform.test_install_transfer -v
```

Preliminary implementation evidence (before the formal Runtime run was
registered) was 6/6 passing in 5.612 seconds. It is not represented as
evidence for the later registered implementation attempt. For that actual
follow-up attempt, the initial RED run showed the missing pinned-commit and
source-reparse controls (2 failures), then the repaired suite passed 8/8 in
8.623 seconds on Windows. Every fixture native subprocess has a finite timeout;
junction diagnostic output is decoded from bytes with the locale and replacement
handling only for assertion messages.

The actual pre-setup installer run from source `c3eb271` was correctly
recorded as `FAIL` for `BUG-INSTALL-002`: it rejected the canonical stub and
left the new target's `.install-failed` marker without payload. That target was
preserved for evidence. Revision 2 implementation run
`run-c000861b1ce84634bb40edb73102b571` added the exact path-and-blob exception;
its RED run had 1/11 failure and its GREEN developer run passed 11/11 in
11.948 seconds. This does not replace the separate real dependency-installing
setup, independent QA, or review evidence.

Revision 3 corrects PowerShell's default case-insensitive equality with `-ceq`.
The new same-blob `knowledge/local/readme.md` fixture was RED before that
change and is included in the revision-3 focused verification.

This focused evidence does not execute a real dependency-installing setup,
perform a production install, or constitute independent QA/review or system
acceptance.
