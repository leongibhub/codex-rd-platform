const WARNING = "Browser storage is unavailable. Notes will not persist after this page is closed.";

/**
 * Resolves browser storage once and degrades to an in-memory implementation
 * when either the accessor or a storage operation is denied by the browser.
 */
export function createSafeStorage(owner) {
  const memory = new Map();
  let backend = null;
  let warning = "";

  try {
    backend = owner.localStorage;
    if (!backend || typeof backend.getItem !== "function" || typeof backend.setItem !== "function") {
      backend = null;
      warning = WARNING;
    }
  } catch {
    warning = WARNING;
  }

  function downgrade() {
    backend = null;
    warning = WARNING;
  }

  return {
    get persistent() { return backend !== null; },
    get warning() { return warning; },
    getItem(key) {
      if (backend) {
        try {
          const value = backend.getItem(key);
          if (value !== null) memory.set(key, value);
          return value;
        } catch {
          downgrade();
        }
      }
      return memory.get(key) ?? null;
    },
    setItem(key, value) {
      memory.set(key, value);
      if (backend) {
        try {
          backend.setItem(key, value);
        } catch {
          downgrade();
        }
      }
    },
  };
}
