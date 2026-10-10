// The ACTIVE conversation, kept in the browser's localStorage so it survives a refresh.
//
// What lives where (do not mix these up):
//   localStorage  = the active conversation + a lightweight note of which dataset it was about
//   runtime memory = the actual dataset (never stored here, never restored after a refresh)
//   chats/ folder = a passive archive written by the server (never read by this app)
//
// Only small things are stored: message text, small tables (<= 10 rows), and chart *alt text*.
// Never the dataset, never images, never anything large.

const KEY = 'insightarc.activeConversation';
const VERSION = 1;
export const MAX_COMPLETED_CYCLES = 20; // one cycle = one user message + its reply

const REPLY_TYPES = ['final', 'table', 'image', 'modification', 'error'];

// Keep only the small fields of a message. This is what gets stored AND archived.
export function toStored(message) {
  const { request_id, role, text, type, columns, rows, total_rows, alt } = message;
  const stored = { request_id, role, text };
  if (role === 'assistant') {
    stored.type = type;
    if (type === 'table') Object.assign(stored, { columns, rows, total_rows });
    if (type === 'image') stored.alt = alt; // the image itself is intentionally dropped
  }
  return stored;
}

export function saveConversation({ createdAt, dataset, messages }) {
  const recent = messages.slice(-MAX_COMPLETED_CYCLES * 2); // messages always come in user+reply pairs
  const data = { version: VERSION, created_at: createdAt, dataset, messages: recent.map(toStored) };
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    // Storage full or blocked: the app keeps working, the conversation just won't survive a refresh.
  }
}

export function loadConversation() {
  try {
    const data = JSON.parse(localStorage.getItem(KEY));
    if (data?.version !== VERSION || !Array.isArray(data.messages)) return null;
    const messages = data.messages.map(cleanMessage).filter(Boolean);
    if (messages.length === 0) return null;
    return {
      createdAt: typeof data.created_at === 'string' ? data.created_at : null,
      dataset: data.dataset && typeof data.dataset === 'object' ? data.dataset : null,
      messages,
    };
  } catch {
    return null; // missing, corrupted, or storage unavailable
  }
}

export function clearConversation() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // nothing to do
  }
}

// Stored data came from disk, so never trust its shape.
function cleanMessage(m) {
  if (!m || typeof m.text !== 'string' || !['user', 'assistant'].includes(m.role)) return null;
  const clean = { request_id: String(m.request_id ?? ''), role: m.role, text: m.text };
  if (m.role === 'user') return clean;

  clean.type = REPLY_TYPES.includes(m.type) ? m.type : 'final';
  if (clean.type === 'table') {
    if (Array.isArray(m.columns) && Array.isArray(m.rows)) {
      Object.assign(clean, { columns: m.columns, rows: m.rows, total_rows: m.total_rows ?? m.rows.length });
    } else {
      clean.type = 'final';
    }
  }
  if (clean.type === 'image' && typeof m.alt === 'string') clean.alt = m.alt;
  return clean;
}
