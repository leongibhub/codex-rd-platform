import assert from "node:assert/strict";
import test from "node:test";
import { STORAGE_KEY, createNote, deleteNote, filterNotes, loadNotes, saveNotes, updateNote } from "../../examples/multistack/web_notes/notes.js";

class MemoryStorage {
  constructor() { this.values = new Map(); }
  getItem(key) { return this.values.has(key) ? this.values.get(key) : null; }
  setItem(key, value) { this.values.set(key, value); }
}

test("TC-IQA-WEB-01: public domain operations persist without search mutation", () => {
  const storage = new MemoryStorage();
  let notes = createNote([], { title: " Alpha ", body: "first" }, () => "n1");
  notes = createNote(notes, { title: "Beta", body: "Needle body" }, () => "n2");
  notes = updateNote(notes, "n1", { title: "Alpha", body: "changed" });
  saveNotes(storage, notes);
  const loaded = loadNotes(storage);
  const filtered = filterNotes(loaded, "NEEDLE");
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].id, "n2");
  assert.deepEqual(loadNotes(storage).map((note) => note.id), ["n1", "n2"]);
  saveNotes(storage, deleteNote(loaded, "n1"));
  assert.deepEqual(loadNotes(storage).map((note) => note.id), ["n2"]);
});

test("TC-IQA-WEB-02: invalid and malformed state is harmless data", () => {
  const storage = new MemoryStorage();
  for (const invalid of [{ title: " ", body: "x" }, { title: "x".repeat(501), body: "ok" }]) {
    assert.throws(() => createNote([], invalid, () => "unused"));
  }
  const markup = "<img src=x onerror=globalThis.pwned=1>";
  const note = createNote([], { title: markup, body: markup }, () => "literal");
  assert.equal(note[0].title, markup);
  assert.equal(note[0].body, markup);
  storage.setItem(STORAGE_KEY, "not-json");
  assert.deepEqual(loadNotes(storage), []);
  storage.setItem(STORAGE_KEY, JSON.stringify([{ id: "bad", title: "", body: "x", updatedAt: "now" }]));
  assert.deepEqual(loadNotes(storage), []);
});

test("TC-IQA-WEB-03: unavailable local storage reads degrade safely", () => {
  const unavailable = { getItem() { throw new Error("storage unavailable"); } };
  assert.deepEqual(loadNotes(unavailable), []);
});
