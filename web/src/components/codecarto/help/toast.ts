/**
 * Toast notification system.
 *
 * Usage:
 *   ToastManager.show('message');         // auto-dismiss in 5s
 *   ToastManager.show('message', 8000);   // custom duration
 *
 * Hint management (single-show per session):
 *   ToastManager.hint('key', 'message');  // shows only once per browser session
 *
 * The ToastContainer component must be mounted somewhere in the app.
 */

import m from 'mithril';

const HINT_KEY = 'cc:hints-seen';

interface Toast {
  id: number;
  message: string;
  expiry: number;
}

let _nextId = 1;
const _toasts: Toast[] = [];

function _seenHints(): Set<string> {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(HINT_KEY) ?? '[]'));
  } catch {
    return new Set();
  }
}

function _markHintSeen(key: string): void {
  const seen = _seenHints();
  seen.add(key);
  sessionStorage.setItem(HINT_KEY, JSON.stringify([...seen]));
}

export const ToastManager = {
  show(message: string, durationMs = 5000): void {
    const id = _nextId++;
    _toasts.push({ id, message, expiry: Date.now() + durationMs });
    m.redraw();
    setTimeout(() => {
      const idx = _toasts.findIndex(t => t.id === id);
      if (idx !== -1) _toasts.splice(idx, 1);
      m.redraw();
    }, durationMs);
  },

  /** Show a hint only once per browser session. */
  hint(key: string, message: string, durationMs = 6000): void {
    if (_seenHints().has(key)) return;
    _markHintSeen(key);
    this.show(message, durationMs);
  },

  dismiss(id: number): void {
    const idx = _toasts.findIndex(t => t.id === id);
    if (idx !== -1) _toasts.splice(idx, 1);
    m.redraw();
  },
};

/** Mount this component once at the app root to display toasts. */
export const ToastContainer: m.Component = {
  view() {
    const now = Date.now();
    const active = _toasts.filter(t => t.expiry > now);
    if (active.length === 0) return null;

    return m('div.cc-toasts', active.map(t =>
      m('div.cc-toast', { key: t.id }, [
        m('span.cc-toast__msg', t.message),
        m('button.cc-toast__close', {
          onclick: () => ToastManager.dismiss(t.id),
        }, '×'),
      ])
    ));
  },
};
