import { createNote, defaultId, deleteNote, filterNotes, loadNotes, saveNotes, updateNote } from "./notes.js";
import { createSafeStorage } from "./storage.js";

const form = document.querySelector("#note-form");
const title = document.querySelector("#title");
const body = document.querySelector("#body");
const search = document.querySelector("#search");
const list = document.querySelector("#notes");
const status = document.querySelector("#status");
const submit = document.querySelector("#submit");
const cancel = document.querySelector("#cancel-edit");
const storage = createSafeStorage(window);
let notes = loadNotes(storage);
let editingId = null;

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function persist(nextNotes) {
  saveNotes(storage, nextNotes);
  notes = nextNotes;
}

function persistenceMessage(message) {
  return storage.warning ? `${message} ${storage.warning}` : message;
}

function textElement(tag, text, className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function render() {
  list.replaceChildren();
  const visible = filterNotes(notes, search.value);
  if (!visible.length) {
    list.append(textElement("p", "No notes found.", "empty"));
    return;
  }
  for (const note of visible) {
    const item = document.createElement("article");
    item.className = "note";
    item.append(textElement("h2", note.title));
    item.append(textElement("p", note.body));
    const actions = document.createElement("div");
    actions.className = "actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "Edit";
    edit.addEventListener("click", () => startEdit(note));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Delete";
    remove.className = "danger";
    remove.addEventListener("click", () => {
      try {
        persist(deleteNote(notes, note.id));
        if (editingId === note.id) stopEdit();
        setStatus(persistenceMessage("Note deleted."));
        render();
      } catch (error) { setStatus(error.message, true); }
    });
    actions.append(edit, remove);
    item.append(actions);
    list.append(item);
  }
}

function startEdit(note) {
  editingId = note.id;
  title.value = note.title;
  body.value = note.body;
  submit.textContent = "Save changes";
  cancel.hidden = false;
  title.focus();
}

function stopEdit() {
  editingId = null;
  form.reset();
  submit.textContent = "Add note";
  cancel.hidden = true;
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  try {
    const input = { title: title.value, body: body.value };
    persist(editingId ? updateNote(notes, editingId, input) : createNote(notes, input, defaultId));
    setStatus(persistenceMessage(editingId ? "Note updated." : "Note added."));
    stopEdit();
    render();
  } catch (error) { setStatus(error.message, true); }
});
cancel.addEventListener("click", () => { stopEdit(); setStatus("Edit cancelled."); });
search.addEventListener("input", render);
if (storage.warning) setStatus(storage.warning, true);
render();
