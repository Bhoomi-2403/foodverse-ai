// Real, local-only history stored in this browser (no fake data). Safe if storage is unavailable.
const KEY = 'foodverse.history.v1';

export function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]');
  } catch {
    return [];
  }
}

export function addHistory(module, title, path) {
  try {
    const next = [{ module, title, path, at: new Date().toISOString() }, ...getHistory()].slice(0, 20);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* storage unavailable: history is optional */
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
