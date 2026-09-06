export const STORAGE_KEY = "offline-web-notes.v1";
const MAX_LENGTH = 500;

function validStoredNote(note) {
  return note
    && typeof note.id === "string" && note.id.length > 0
    && typeof note.title === "string" && note.title.trim().length > 0 && note.title.length <= MAX_LENGTH
    && typeof note.body === "string" && note.body.trim().length > 0 && note.body.length <= MAX_LENGTH
    && typeof note.updatedAt === "string" && note.updatedAt.length > 0;
}

function normalize(input) {
  const title = typeof input?.title === "string" ? input.title.trim() : "";
  const body = typeof input?.body === "string" ? input.body.trim() : "";
  if (!title || !body) throw new Error("Title and body are required.");
  if (title.length > MAX_LENGTH || body.length > MAX_LENGTH) {
    throw new Error(`Title and body must be at most ${MAX_LENGTH} characters.`);
  }
  return { title, body };
}

export function defaultId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `note-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function loadNotes(storage) {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (raw === null) return [];
    const notes = JSON.parse(raw);
    if (!Array.isArray(notes) || !notes.every(validStoredNote)) return [];
    const ids = new Set(notes.map((note) => note.id));
    return ids.size === notes.length ? notes : [];
  } catch {
    return [];
  }
}

export function saveNotes(storage, notes) {
  storage.setItem(STORAGE_KEY, JSON.stringify(notes));
}

export function createNote(notes, input, makeId = defaultId) {
  const fields = normalize(input);
  const id = makeId();
  if (typeof id !== "string" || !id || notes.some((note) => note.id === id)) {
    throw new Error("Unable to create a unique note ID.");
  }
  return [...notes, { id, ...fields, updatedAt: new Date().toISOString() }];
}

export function updateNote(notes, id, input) {
  const fields = normalize(input);
  if (!notes.some((note) => note.id === id)) throw new Error("Note not found.");
  return notes.map((note) => note.id === id
    ? { ...note, ...fields, updatedAt: new Date().toISOString() }
    : note);
}

export function deleteNote(notes, id) {
  if (!notes.some((note) => note.id === id)) throw new Error("Note not found.");
  return notes.filter((note) => note.id !== id);
}

export function filterNotes(notes, query) {
  const needle = String(query ?? "").trim().toLocaleLowerCase();
  if (!needle) return [...notes];
  return notes.filter((note) => `${note.title}\n${note.body}`.toLocaleLowerCase().includes(needle));
}
