# Deployment executor / 部署执行器

Traceability: `REQ-V3-018`, `DES-V3-003`, `TASK-V3-018`.

`execute_deployment(runtime, config, action='deploy')` accepts only a trusted,
local configuration. It has no HTTP command endpoint and never constructs an
argv from an environment label. Required fields are `project_id`, `environment`,
`operation_id`, absolute `cwd`, `source_hashes`, `deploy`, `health`, `rollback`,
`rollback_health`, and `receipt_dir`. Every command is an explicit argv with a
finite timeout and output-byte limit. `source_hashes` are SHA-256 values for
paths relative to `cwd`; drift stops execution before any command starts.
Project-local script files referenced by an argv must also be listed and pinned
in `source_hashes`; external host tools such as the Python interpreter are not
treated as project source.
Relative argv files resolve under `cwd`; project files outside that bounded
directory are rejected. Every source-hash and project argv path rejects a
symbolic-link or Windows junction component rather than following it outside
the pinned directory. Windows 8.3 short-path and long-path spellings are
canonicalized before project containment is classified, so an in-project script
cannot be misclassified as an external host tool. The adapter rehashes all declared sources immediately
before each deploy, health, rollback, and rollback-health process launch.

Each operation prewrites an fsynced `STARTED` receipt and uses an exclusive
receipt-directory lock. A later invocation that finds a started, nonterminal
operation fails as `unknown; reconcile before retry`; it never blindly replays
a potentially non-idempotent deployment. Terminal command and compensation
facts are retained both in an immutable individual receipt and append-only
`operations.jsonl`. Runner output is bounded and secret-redacted.
Receipt writes flush file data for ordinary process-crash recovery. They do not
claim a host power-loss durability guarantee: this adapter does not issue a
portable directory fsync after rename, so an operator must reconcile any
operation lacking a terminal receipt after abrupt host or filesystem failure.
An existing `operation_id` may return its terminal result only when the exact
configuration fingerprint matches; a changed environment, target, argv, hash,
or other payload is rejected as a receipt conflict.

Trial mode reports `TRIAL_SUCCEEDED`, `TRIAL_ROLLED_BACK`, or
`TRIAL_ROLLBACK_FAILED`. A trial is never a release or deployment record.
Formal mode additionally needs `release_id`, a non-agent human `operator`, a
registered release-manager `executor_id`, and an existing
`deployment_environment` `environment_ref`, plus current nonempty
`evidence_artifact_refs`. It checks a READY release and
current G10 before launch. Its `receipt_dir` must resolve beneath the project
repository before any operation receipt or command is launched, then it records
only actual results through Runtime.
All formal evidence and release mutations are executed through
`LifecycleService` inside one SQLite transaction. A failed later mutation rolls
back earlier evidence/release writes; the physical command receipt remains the
separate, durable observation for reconciliation.
The release API rechecks Gate state. If that registration is rejected due to
concurrent Gate/evidence drift, `formal_registration_error` is returned while
the durable physical command and rollback facts remain available for human
reconciliation; overall `status` is `FAIL` and `actual_status` retains the
physical command outcome, so a caller cannot treat registration failure as a
successful formal release. An explicit formal `action='rollback'` emits only
rollback evidence and calls `release.rollback`; it never calls
`release.record_deployment`. Compensation always has its own independent `rollback_health`
command; successful argv alone never proves recovery.
