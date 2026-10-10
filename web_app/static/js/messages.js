// Builds the DOM for chat content.
//
// SAFETY: nothing here uses innerHTML. All text goes in through textContent / text nodes,
// so whatever the server (or, later, the AI) returns can never be interpreted as HTML.

export const MAX_TABLE_ROWS = 10;

// el('div', { class: 'x', onclick: fn }, child, 'text', ...)  ->  <div class="x">…</div>
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value == null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of children.flat()) {
    if (child != null && child !== false) node.append(child); // strings become text nodes
  }
  return node;
}

// ----- messages ---------------------------------------------------------------------

export function buildMessage(message, { onOpenImage }) {
  if (message.role === 'user') {
    return el('div', { class: 'msg msg-user' }, el('div', { class: 'bubble', text: message.text }));
  }

  const bubble = el('div', { class: 'bubble' }, el('p', { class: 'msg-text', text: message.text }));
  if (message.type === 'table') bubble.append(...buildTable(message));
  if (message.type === 'image') bubble.append(buildImage(message, onOpenImage));

  const classes = ['msg', 'msg-assistant'];
  if (message.type === 'error') classes.push('is-error');
  return el('div', { class: classes.join(' ') }, bubble);
}

export function buildTyping() {
  return el(
    'div',
    { class: 'msg msg-assistant', role: 'status' },
    el(
      'div',
      { class: 'bubble typing' },
      el('span', { class: 'sr-only', text: 'Analyzing…' }),
      el('span', { class: 'typing-dot' }),
      el('span', { class: 'typing-dot' }),
      el('span', { class: 'typing-dot' }),
    ),
  );
}

// The assistant's opening message (never stored or archived), optionally with suggestion chips.
export function buildIntro(text, suggestions = [], onPick = () => {}) {
  const chips = suggestions.map((suggestion) =>
    el('button', { class: 'chip', type: 'button', text: suggestion, onclick: () => onPick(suggestion) }),
  );
  return el(
    'div',
    { class: 'msg msg-assistant' },
    el('div', { class: 'bubble' }, el('p', { class: 'msg-text', text }), chips.length ? el('div', { class: 'chips' }, chips) : null),
  );
}

export function buildNote(text) {
  return el('p', { class: 'thread-note', text });
}

// ----- tables -----------------------------------------------------------------------

// Returns [tableWrapper, caption?]. Only the first MAX_TABLE_ROWS rows are ever rendered.
function buildTable({ columns, rows, total_rows }) {
  const shown = rows.slice(0, MAX_TABLE_ROWS);
  const total = Number.isFinite(total_rows) ? total_rows : rows.length;
  const isNumeric = columns.map((_, i) => shown.length > 0 && shown.every((row) => typeof row[i] === 'number' || row[i] == null));

  const head = el('tr', {}, columns.map((name, i) => el('th', { scope: 'col', class: isNumeric[i] ? 'num' : '', text: String(name) })));
  const body = shown.map((row) =>
    el('tr', {}, columns.map((_, i) => el('td', { class: isNumeric[i] ? 'num' : '', text: formatCell(row[i]) }))),
  );

  const wrapper = el('div', { class: 'table-wrap' }, el('table', { class: 'result-table' }, el('thead', {}, head), el('tbody', {}, body)));
  const caption = total > shown.length ? el('p', { class: 'table-caption', text: `Showing the first ${shown.length} of ${total} rows` }) : null;
  return [wrapper, caption].filter(Boolean);
}

function formatCell(value) {
  return value == null ? '—' : String(value);
}

// ----- images -----------------------------------------------------------------------

function buildImage(message, onOpenImage) {
  if (!message.image) {
    // Images are not kept in localStorage, so after a refresh only a placeholder remains.
    return el('p', { class: 'image-missing', text: 'This chart is not kept after a refresh.' });
  }
  const alt = message.alt || message.text;
  const src = `data:image/png;base64,${message.image}`;
  return el(
    'button',
    { class: 'image-button', type: 'button', 'aria-label': 'Enlarge chart', onclick: () => onOpenImage(src, alt) },
    el('img', { class: 'msg-image', src, alt }),
  );
}
