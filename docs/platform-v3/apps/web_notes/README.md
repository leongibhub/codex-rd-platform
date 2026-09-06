# Offline Web Notes

## Scope and traceability

- Task: `TASK-V3-003` (web application slice)
- Requirement: `REQ-MATRIX-WEB`
- Source baseline: `docs/superpowers/specs/2026-09-06-multistack-selftest.md`
- Runtime implementation run: `run-beb11b69f05c47e9a64dac3f3bdc64da`

## Initial model

The product is a single-user, offline browser notes application. A user creates
a short titled note, edits or deletes it, and filters the displayed notes by a
text query. Notes are stored in the browser's `localStorage` under one
application-owned key, so a reload can restore valid saved content. There are
no accounts, synchronization, multi-device conflict resolution, or server API.
All test data is synthetic.

## Requirements and acceptance criteria

| ID | Requirement / measurable acceptance |
| --- | --- |
| REQ-MATRIX-WEB-01 | A user can create a note with a non-blank title and body, each at most 500 characters; invalid input is rejected with an accessible message and does not persist a note. |
| REQ-MATRIX-WEB-02 | A user can edit an existing note; a valid save replaces that note and persists the change. |
| REQ-MATRIX-WEB-03 | A user can delete an existing note; it is removed from the rendered list and persisted storage. |
| REQ-MATRIX-WEB-04 | Search is case-insensitive over title and body, without changing the saved notes. |
| REQ-MATRIX-WEB-05 | Notes survive reload through `localStorage`; malformed or unavailable stored data is treated as an empty collection without crashing. If browser storage is unavailable or begins failing, the application remains usable in an empty in-memory view and visibly warns that later notes will not persist. |
| REQ-MATRIX-WEB-06 | User-controlled note and search text is rendered as text, not HTML; markup such as `<img onerror=...>` cannot create DOM elements or execute. |
| REQ-MATRIX-WEB-07 | `manifest.json` is schema version 1 and exposes argv-only local commands; the application has a loopback-only static serve instruction and Node built-in `node:test` unit suite. |

## Design

`notes.js` is a dependency-free native ES module containing the pure note
domain: validation, ID creation, load/save adapters, create/update/delete and
search. It accepts a storage-shaped object, allowing Node tests to use an
in-memory substitute while the real app uses `window.localStorage`.

`storage.js` resolves `window.localStorage` exactly once inside a guarded
factory. A throwing accessor or later `getItem`/`setItem` error switches to an
empty in-memory adapter and exposes a nonfatal persistence warning.

`app.js` owns browser event wiring and DOM rendering. It creates elements and
uses `textContent` for every user-provided value; it never builds note markup
with `innerHTML`. `index.html` is the accessible, dependency-free interface.
The storage record is a JSON array of `{id, title, body, updatedAt}` values and
is validated on load. IDs use browser `crypto.randomUUID` when available and a
portable fallback otherwise.

## Risk-driven test model

| Test ID | Requirement | Type | Risk | Input / steps | Expected | Automation |
| --- | --- | --- | --- | --- | --- | --- |
| TC-WEB-001 | REQ-MATRIX-WEB-01 | Unit | Invalid/oversized content is saved | Blank, whitespace-only and 501-character fields | Validation error; storage unchanged | `node:test` |
| TC-WEB-002 | REQ-MATRIX-WEB-01 | Unit | Valid creation loses data | Create a valid synthetic note | One normalized, persisted note | `node:test` |
| TC-WEB-003 | REQ-MATRIX-WEB-02 | Unit | Edit targets wrong note or invalid edit overwrites it | Update one of two notes; then submit blank edit | Correct record changes; invalid update throws and collection is unchanged | `node:test` |
| TC-WEB-004 | REQ-MATRIX-WEB-03 | Unit | Delete does not persist | Delete a stored note | It is absent after a fresh load | `node:test` |
| TC-WEB-005 | REQ-MATRIX-WEB-04 | Unit | Search mutates collection or misses body | Mixed-case title/body query | Case-insensitive matching; original array unchanged | `node:test` |
| TC-WEB-006 | REQ-MATRIX-WEB-05 | Unit | Corrupt storage crashes startup | Invalid JSON and invalid record shapes | Empty notes result, no exception | `node:test` |
| TC-WEB-007 | REQ-MATRIX-WEB-05 | Unit | Storage accessor aborts startup | `localStorage` getter throws | Empty in-memory adapter and persistence warning, no throw | `node:test` |
| TC-WEB-008 | REQ-MATRIX-WEB-05 | Unit | Later storage operations abort or lose active draft | `getItem`/`setItem` throw | Adapter degrades to memory and warns, no throw | `node:test` |
| TC-WEB-009 | REQ-MATRIX-WEB-06 | Browser black-box | Stored XSS | Create/edit a note containing markup, reload and inspect rendered list | Literal text visible; no injected element/event execution | Independent browser validation, NOT_EXECUTED here |
| TC-WEB-010 | REQ-MATRIX-WEB-01..05 | Browser black-box | Event/persistence wiring differs from domain behavior | Create, edit, search, delete and reload in a real browser | User flow and local persistence succeed | Independent browser validation, NOT_EXECUTED here |

## Review remediation

`REV-V3-APP-004` identified that resolving `window.localStorage` outside a
guarded operation could reject startup in restricted browser contexts. The
implementation now captures one guarded storage adapter and falls back to an
empty in-memory view for accessor and later operation failures. TC-WEB-007 and
TC-WEB-008 are the developer regressions for this correction; independent
browser rerun remains required.

## Local operation and evidence boundary

From this directory, serve only the loopback interface with:

```powershell
python -m http.server 8080 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8080/`. This implementation document records
developer modeling and unit verification only. Browser acceptance, independent
testing, review, release and human/system acceptance remain separate evidence.
