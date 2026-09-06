import test from "node:test";
import assert from "node:assert/strict";

import {
  createNote,
  deleteNote,
  filterNotes,
  loadNotes,
  saveNotes,
  updateNote,
} from "../notes.js";
import { createSafeStorage } from "../storage.js";

function memoryStorage(initial = undefined) {
  let value = initial;
  return {
    getItem() { return value ?? null; },
    setItem(_key, next) { value = next; },
    dump() { return value; },
  };
}

test("TC-WEB-001: blank and oversized fields are rejected before persistence", () => {
  const storage = memoryStorage();
  const notes = [];

  for (const input of [
    { title: " ", body: "valid" },
    { title: "valid", body: "\t" },
    { title: "x".repeat(501), body: "valid" },
    { title: "valid", body: "x".repeat(501) },
  ]) {
    assert.throws(() => createNote(notes, input, () => "id-1"), /required|500/i);
  }
  assert.equal(storage.dump(), undefined);
});

test("TC-WEB-002: valid creation normalizes, appends, and persists", () => {
  const storage = memoryStorage();
  const created = createNote([], { title: "  Buy milk  ", body: "  oat  " }, () => "note-1");
  saveNotes(storage, created);

  assert.deepEqual(created, [{ id: "note-1", title: "Buy milk", body: "oat", updatedAt: created[0].updatedAt }]);
  assert.deepEqual(loadNotes(storage), created);
});

test("TC-WEB-003: update changes only its target and invalid input cannot overwrite", () => {
  const notes = [
    { id: "a", title: "first", body: "one", updatedAt: "2026-01-01T00:00:00.000Z" },
    { id: "b", title: "second", body: "two", updatedAt: "2026-01-01T00:00:00.000Z" },
  ];
  const updated = updateNote(notes, "b", { title: "changed", body: "body" });

  assert.equal(updated[0], notes[0]);
  assert.deepEqual(updated[1], { ...notes[1], title: "changed", body: "body", updatedAt: updated[1].updatedAt });
  assert.throws(() => updateNote(notes, "a", { title: "", body: "body" }), /required/i);
  assert.deepEqual(notes[0], { id: "a", title: "first", body: "one", updatedAt: "2026-01-01T00:00:00.000Z" });
});

test("TC-WEB-004: delete persists absence across a fresh load", () => {
  const storage = memoryStorage();
  const remaining = deleteNote([{ id: "a", title: "A", body: "B", updatedAt: "time" }], "a");
  saveNotes(storage, remaining);
  assert.deepEqual(loadNotes(storage), []);
});

test("TC-WEB-005: case-insensitive search includes body and does not mutate notes", () => {
  const notes = [
    { id: "a", title: "Shopping", body: "Milk", updatedAt: "time" },
    { id: "b", title: "Work", body: "Review NOTES", updatedAt: "time" },
  ];
  const before = structuredClone(notes);
  assert.deepEqual(filterNotes(notes, "notes").map(({ id }) => id), ["b"]);
  assert.deepEqual(filterNotes(notes, "MILK").map(({ id }) => id), ["a"]);
  assert.deepEqual(notes, before);
});

test("TC-WEB-006: malformed storage is safely treated as empty", () => {
  assert.deepEqual(loadNotes(memoryStorage("not json")), []);
  assert.deepEqual(loadNotes(memoryStorage('[{"id":"x","title":5}]')), []);
});

test("TC-WEB-007: a throwing localStorage accessor falls back to an empty in-memory view", () => {
  const owner = {};
  Object.defineProperty(owner, "localStorage", {
    get() { throw new Error("SecurityError: storage denied"); },
  });

  const storage = createSafeStorage(owner);
  assert.equal(storage.persistent, false);
  assert.match(storage.warning, /not persist/i);
  assert.equal(storage.getItem("missing"), null);
  storage.setItem("draft", "value");
  assert.equal(storage.getItem("draft"), "value");
});

test("TC-WEB-008: getItem and setItem failures are nonfatal and downgrade to memory", () => {
  const readFailure = createSafeStorage({
    localStorage: {
      getItem() { throw new Error("get denied"); },
      setItem() { throw new Error("set denied"); },
    },
  });

  assert.equal(readFailure.getItem("existing"), null);
  assert.equal(readFailure.persistent, false);
  assert.match(readFailure.warning, /not persist/i);

  const writeFailure = createSafeStorage({
    localStorage: {
      getItem() { return null; },
      setItem() { throw new Error("set denied"); },
    },
  });
  writeFailure.setItem("draft", "value");
  assert.equal(writeFailure.persistent, false);
  assert.equal(writeFailure.getItem("draft"), "value");
  assert.match(writeFailure.warning, /not persist/i);
});
