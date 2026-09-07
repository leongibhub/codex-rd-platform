# V3 capacity and stability validation design

Traceability: `NFR-V3-002` → `DES-V3-001` → `TASK-V3-005`.

## Scope and acceptance

The benchmark validates the local SQLite *read* capacity design target: 100
isolated lifecycle projects, 100,000 artifact-version records, and 1,000,000
lifecycle events. It records real `Runtime.lifecycle_collection()` keyset-page
and `Runtime.lifecycle_snapshot()` timings against that seeded database.

The benchmark reports p50/p95/p99 latency, call throughput, errors, database
size, process RSS where the host exposes it, available CPU count, Python and
SQLite versions, platform information, and wall/CPU timings. A completed full
run is only observed capacity evidence; it is not a performance SLO, Gate
decision, release recommendation, deployment result, or human acceptance.

Seeding is intentionally synthetic and uses batched SQLite inserts. It is
labelled `synthetic_batch_sql` in every result and must never be represented as
Runtime/API write throughput or production-like workload modelling. The timed
read probes use the public Runtime facade.

Every capacity and soak terminal/checkpoint declares
`workload_scope.public_read_operations` as exactly
`Runtime.lifecycle_collection` and `Runtime.lifecycle_snapshot`. Its explicit
exclusions are Runtime write throughput, full-system stability, and write
consistency; result consumers must not infer those properties.

## Safety and risk controls

- `--output-dir` is dedicated to one run. An existing `state.db` is rejected;
  the tool never opens, modifies, or deletes an existing runtime database.
- Results include a generated run ID, so completed histories are append-only.
  A run-local checkpoint may update only its own checkpoint path.
- Full capacity requires `capacity --profile full`; the default is a small
  smoke profile. Full runs enforce a 1.5 GiB database-size ceiling and a
  600-second elapsed-time ceiling. Breach produces terminal `ABORTED` JSON and
  a non-zero exit, not PASS.
- `soak` permits 1 to 259,200 seconds (72 hours), requires interval >= 1
  second, and writes periodic checkpoints plus a terminal JSON. `Ctrl+C` is
  recorded as `INTERRUPTED`; unexpected exceptions as `FAIL`; neither can
  produce PASS.
- Capacity catches `KeyboardInterrupt` during both synthetic seed and public
  read measurement, recording its current `phase` and actual duration. Soak
  treats an interrupted capacity setup as its own `capacity_setup` phase,
  writes a same-run checkpoint and terminal `INTERRUPTED` record, and does not
  continue into sampling.
- The benchmark is local-only, standard-library-only and does not use HTTP,
  k6, or production systems. This is appropriate for the SQLite control-plane
  data path, not a substitute for user-traffic or browser performance tests.

## Test cases

| ID | Requirement | Procedure | Expected observable result |
| --- | --- | --- | --- |
| TC-V3-PERF-001 | NFR-V3-002 | Run synthetic smoke capacity fixture. | Isolated DB/result JSON; public page/snapshot samples and percentiles exist. |
| TC-V3-PERF-002 | NFR-V3-002 | Point at directory containing `state.db`. | Refusal without opening/overwriting it. |
| TC-V3-PERF-003 | NFR-V3-002 | Exceed disk/time budget during seed. | `ABORTED` terminal JSON and non-zero result. |
| TC-V3-PERF-004 | NFR-V3-002 | Run a short soak with interval >= 1. | Checkpoint and PASS terminal JSON contain samples and environment facts. |
| TC-V3-PERF-005 | NFR-V3-002 | Invalid soak duration/interval or >72-hour duration. | Input rejection before database activity. |

## Operator commands

First run a short smoke fixture:

```text
python scripts/benchmark_lifecycle.py capacity --output-dir .rd-platform/perf-smoke --profile smoke
python scripts/benchmark_lifecycle.py soak --output-dir .rd-platform/perf-soak --duration-seconds 30 --interval-seconds 1
```

After reviewing the smoke JSON and reserving local disk/CPU, run the full
capacity fixture (do not point at a project `.rd-platform` directory):

```text
python scripts/benchmark_lifecycle.py capacity --output-dir D:\perf\lifecycle-full --profile full
```

The full profile performs at least one public collection and snapshot sample
for each of its 100 seeded projects; smoke samples cycle over its seeded
projects as well.

The capacity deadline covers both synthetic seed batches and every public
read probe. Soak checkpoints include an elapsed-time/RSS/process-CPU/DB-size
series, so they support trend inspection for this SQLite read path only; they
do not prove whole-system stability or write-consistency behavior.

An authorized long soak can be started separately; this implementation does
not automatically start it:

```text
python scripts/benchmark_lifecycle.py soak --output-dir D:\perf\lifecycle-soak-8h --profile full --duration-seconds 28800 --interval-seconds 1
```

Before treating a full result as observed evidence, retain its terminal JSON
and verify `status` is `PASS`, `seed_mode` remains `synthetic_batch_sql`, and
neither budget was exceeded. The observed-result section below records each
actual execution separately.

For a running capacity benchmark, inspect `<output-dir>/perf-<run-id>-checkpoint.json`; its
terminal counterpart is `perf-<run-id>-terminal.json`. A running soak uses
`soak-<run-id>-checkpoint.json` and completes as `soak-<run-id>-terminal.json`.
The checkpoint belongs only to that generated run ID and is the sole mutable
file; terminal files are new history records.

## Developer execution evidence

On 2026-09-06, the executable smoke profile was run in isolated new output
directories. Capacity evidence at
`.rd-platform/benchmark-smoke-20260906-2/perf-7a1df7f216854fa082c9425780b7717c-terminal.json`
is `PASS`: 2 projects, 200 artifact versions, 1,000 events, 696,320-byte DB,
and no read errors. Its five public collection samples measured p50/p95/p99
of 98.0585/108.7571/108.7571 ms; five public snapshot samples measured
368.2055/430.9139/430.9139 ms. The host reported 16 CPUs and final RSS
32,059,392 bytes.

The separate two-second soak evidence at
`.rd-platform/benchmark-soak-20260906-2/soak-c2bc01fc5d824f2ca7e6cd7cce72dcc1-terminal.json`
is `PASS` with two samples, no errors, a same-run checkpoint, and a
696,320-byte DB. It is a short operational smoke, not long-term stability
evidence. At this initial smoke checkpoint, full capacity
(100/100,000/1,000,000) and the authorized 8-hour soak were `NOT_EXECUTED`;
the subsequent observations below supersede that checkpoint, not its history.

After checkpoint resource-series support was added, a separate two-second
smoke soak recorded three trend samples at
`.rd-platform/benchmark-soak-20260906-3/soak-8bcb0c7abd864e9dba538c4afbf9d7b8-checkpoint.json`
and terminal JSON of the same prefix. It completed `PASS` with no read errors;
DB size remained 696,320 bytes, RSS samples were 32,227,328 / 32,243,712 /
32,243,712 bytes, and process CPU samples were 0.328125 / 0.687500 /
1.015625 seconds. This confirms checkpoint telemetry mechanics on a short
synthetic read-path run only; it does not establish an 8-hour trend.

The interruption-handling repair applies only to future benchmark invocations.
It does not modify, restart, reinterpret, or backfill the already-running
8-hour soak that began from source SHA
`E482F1E2DD6A5A7AB42736AE227DB56B8B5D12F2D6C1D5FA1F3293F78BEDBC9A`.

The first actual full capacity execution is
`.rd-platform/benchmark-full-20260906-1/perf-29cadeac913240c4a8a2868c36a9788e-terminal.json`.
It is `PASS` with the exact target 100 projects, 100,000 synthetic artifact
versions and 1,000,000 synthetic events. It completed in 129.7199 seconds
under the 600-second cap, produced a 294,764,544-byte DB under the 1.5 GiB cap,
and had no public-read errors. Across one public page and snapshot per seeded
project, collection p50/p95/p99 were 378.4251/566.6010/663.2870 ms (2.5036
calls/s); snapshot p50/p95/p99 were 657.9398/952.4863/1267.4792 ms (1.4402
calls/s). The final RSS was 39,088,128 bytes on the observed 16-CPU Windows
host. This is observed synthetic SQLite read-capacity evidence only.

## Completed eight-hour observation

Independent read-only inspection of
`.rd-platform/benchmark-soak-8h-20260906-1/soak-9241634446774e1291126d1cc1c2a53b-terminal.json`
observed `status: PASS`, `exit_code: 0`, and elapsed time
`28,800.74027900002` seconds (finished `2026-09-06T18:29:36.065483+00:00`).
The immutable terminal file SHA-256 is
`00BE7586AD05A8CDD03CFC510C7C730021920BEDB8EFDC1225E4A24765A398CD`.
The process began on source digest
`E482F1E2DD6A5A7AB42736AE227DB56B8B5D12F2D6C1D5FA1F3293F78BEDBC9A`;
the result applies to that already-running, old read-path process only. Later
code was not hot-loaded, restarted, or used to backfill this observation.

This conclusion is based on continuity data, not the terminal label alone.
There are 4,952 `resource_samples` and 4,952 samples for each collection and
snapshot probe. Resource samples cover elapsed `1.785503099905327` through
`28,800.721267899964` seconds. Across all 4,951 adjacent samples, the gap
range is `3.957618599990383`–`8.19159369985573` seconds (maximum from
`701.0510819000192` to `709.2426755998749` seconds); zero gaps exceed 10, 15,
or 30 seconds. The eight complete elapsed-hour buckets contain respectively
598, 616, 613, 603, 631, 630, 630, and 630 samples; one final sample is in the
0.721-second terminal tail. This supports continuously sampled coverage of the
configured eight-hour interval on this host; it is not proof of behaviour
during unobserved prior/future host time.

`reads.errors` is the empty array. Terminal collection p50/p95/p99 are
249.8004/473.0814/677.6966 ms and snapshot p50/p95/p99 are
451.9230/846.1781/1125.4522 ms. RSS samples begin at 38,850,560 bytes, end at
74,272,768 bytes, range from 35,233,792 to 74,784,768 bytes; terminal RSS is
73,965,568 bytes. CPU samples rise from 1.75 to 4,006.8125 process seconds,
a 4,005.0625-second delta (13.90698% of one CPU over the sampled span). The
database is exactly 294,764,544 bytes in every resource sample. These are
observed resource-series values, not a diagnosis of a memory leak or a
capacity promise.

The workload remains explicitly limited to synthetic SQLite public read-only
`Runtime.lifecycle_collection` and `Runtime.lifecycle_snapshot` probes. It
does not establish Runtime write throughput, write consistency, full-system or
Web-user-flow stability, security, production load, a Gate decision, release,
or customer acceptance.
