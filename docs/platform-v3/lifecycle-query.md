# V3 public lifecycle collection query

Traceability: `REQ-V3-008`, `NFR-V3-002`, `NFR-V3-004` → `DES-V3-001` → `TASK-V3-004`.

This read-only interface returns one named lifecycle collection at a time. It
does not execute Runtime commands, alter lifecycle state, expose arbitrary
SQLite tables, or change the existing `Runtime.snapshot()` or
`Runtime.lifecycle_snapshot()` contracts.

## Public API

`Runtime.lifecycle_collection(project_id, collection, *, limit=200,
after_cursor=None)` accepts exactly these twelve collection names:

`gates`, `work_orders`, `artifacts`, `trace_links`, `test_models`,
`test_cases`, `test_executions`, `defects`, `gate_assessments`,
`gate_decisions`, `evidence`, and `releases`.

`limit` is an integer from 1 through 500 (booleans are rejected). The cursor
is opaque, project- and collection-bound, and carries an internal stable
SQLite `rowid` only; malformed, cross-project, or cross-collection cursors
are rejected. Cursor fields are exact, bounded in length, and its rowid must
fit SQLite's signed 64-bit range. Rows are ordered by rowid and queried with keyset pagination, so
collections above 500 records remain fully visible over successive pages.

Every response has this schema:

```json
{
  "schema_version": "lifecycle-collection-v1",
  "project_id": "project-...",
  "collection": "artifacts",
  "items": [],
  "total": 0,
  "next_cursor": null,
  "has_more": false
}
```

Work-order lease digests and release digests are removed. The same secret
redaction and current Gate validity projection used by lifecycle snapshots are
applied; a stale recorded Gate PASS is not returned as a current PASS.

## Adapters

CLI (read-only):

```text
python -m rd_platform.cli --db .rd-platform/state.db lifecycle-collection --project-id project-... artifacts --limit 200
```

HTTP (loopback GET only):

```text
GET /api/lifecycle/collection?project_id=project-...&collection=artifacts&limit=200&after_cursor=<opaque>
```

The endpoint retains the existing exact `127.0.0.1` Host boundary. Query keys
may occur once only; unknown keys, missing project/collection, malformed
limits/cursors, and duplicate parameters return HTTP 400.

## Developer verification

`python -m unittest tests.runtime.test_lifecycle_query -v` exercises a 501-row
artifact collection over multiple pages, project isolation, malformed input,
secret/digest removal, the CLI parser, and loopback HTTP query validation.
This developer evidence does not establish independent QA, Gate status,
release readiness, or system acceptance.
