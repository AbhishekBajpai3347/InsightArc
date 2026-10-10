// Insight Arc: controller. Holds the state, renders it, and wires up the events.
// The flow is always:  user action -> change `state` -> call a render function.

import * as api from './api.js';
import * as storage from './storage.js';
import { MAX_TABLE_ROWS, buildIntro, buildMessage, buildNote, buildTyping, el } from './messages.js';

// ----- constants --------------------------------------------------------------------

const SUPPORTED_EXTENSIONS = ['csv', 'xlsx', 'xls', 'json', 'pickle', 'pkl', 'xml'];
const UNSUPPORTED_FORMAT_MESSAGE =
  'Unsupported file format. Supported formats are: CSV, XLSX, XLS, JSON, Pickle, PKL, XML.';
const DATASET_STATE_LABELS = { none: 'No dataset', uploading: 'Uploading', loaded: 'Loaded', error: 'Error' };
const NOTICE_MS = 6000; // how long a temporary red/grey message stays in the status bar

// ----- elements ---------------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const dom = {
  sidebarToggle: $('sidebar-toggle'), scrim: $('scrim'),
  connection: $('connection'), connectionText: $('connection-text'),
  datasetState: $('dataset-state'), datasetStateText: $('dataset-state-text'),
  uploadButton: $('upload-button'), fileInput: $('file-input'), uploadError: $('upload-error'),
  metaFilename: $('meta-filename'), metaRows: $('meta-rows'), metaColumns: $('meta-columns'),
  columnCount: $('column-count'), search: $('column-search'), columnList: $('column-list'),
  clearConversation: $('clear-conversation'), clearDataset: $('clear-dataset'),
  scroll: $('chat-scroll'), thread: $('thread'), input: $('chat-input'), send: $('send-button'),
  statusbar: $('statusbar'), statusText: $('status-text'),
  confirmDialog: $('confirm-dialog'), lightbox: $('lightbox'), lightboxImg: $('lightbox-img'),
};

// ----- state ------------------------------------------------------------------------

const state = {
  // dataset (runtime memory only: never restored after a refresh)
  status: 'none',         // 'none' | 'uploading' | 'loaded' | 'error'
  dataset: null,          // { filename, rows, columns: [{name, dtype}], suggestions }
  pendingFilename: '',    // shown while uploading
  uploadError: '',        // red text under the Upload button
  search: '',             // column filter text

  // active conversation (saved to localStorage)
  messages: [],           // flat list: user, assistant, user, assistant…
  createdAt: null,        // ISO time of the first message
  datasetSummary: null,   // { filename, rows, columns: [names] } saved next to the conversation; never used to restore the UI

  // activity
  requesting: false,      // a chat request is in flight
  working: false,         // a clear/replace action is in progress
  connected: null,        // null = unknown, true, false
  notice: null,           // temporary status-bar message: { text, kind }
};

const isBusy = () => state.status === 'uploading' || state.requesting || state.working;
const hasConversation = () => state.messages.length > 0;

// ----- rendering --------------------------------------------------------------------

function renderConnection() {
  const text = { true: 'Connected', false: 'Disconnected' }[state.connected] ?? 'Connecting';
  dom.connection.dataset.state = state.connected === null ? 'unknown' : state.connected ? 'connected' : 'disconnected';
  dom.connectionText.textContent = text;
}

function renderSidebar() {
  const { status, dataset } = state;

  dom.datasetState.dataset.state = status;
  dom.datasetStateText.textContent = DATASET_STATE_LABELS[status];

  dom.metaFilename.textContent = status === 'uploading' ? state.pendingFilename : dataset?.filename ?? '—';
  dom.metaFilename.title = dom.metaFilename.textContent;
  dom.metaRows.textContent = dataset ? dataset.rows.toLocaleString() : '—';
  dom.metaColumns.textContent = dataset ? String(dataset.columns.length) : '—';

  dom.uploadError.hidden = !state.uploadError;
  dom.uploadError.textContent = state.uploadError;

  dom.uploadButton.disabled = isBusy();
  dom.clearConversation.disabled = isBusy() || !hasConversation();
  dom.clearDataset.disabled = isBusy() || (status === 'none' && !hasConversation() && !state.uploadError);
  dom.search.disabled = !dataset?.columns.length;

  renderColumns();
}

function renderColumns() {
  dom.columnList.replaceChildren();

  if (state.status === 'uploading') {
    dom.columnCount.textContent = '';
    for (let i = 0; i < 6; i++) {
      dom.columnList.append(el('li', { class: 'column-row skeleton', 'aria-hidden': 'true' }, el('span', { class: 'skeleton-bar' })));
    }
    return;
  }

  const columns = state.dataset?.columns ?? [];
  const query = state.search.trim().toLowerCase();
  const visible = query ? columns.filter((c) => c.name.toLowerCase().includes(query)) : columns;

  dom.columnCount.textContent = columns.length ? (query ? `${visible.length} of ${columns.length}` : String(columns.length)) : '';

  if (columns.length === 0) {
    dom.columnList.append(el('li', { class: 'column-empty', text: 'Columns appear here once a dataset is loaded.' }));
  } else if (visible.length === 0) {
    dom.columnList.append(el('li', { class: 'column-empty', text: `No columns match “${state.search.trim()}”.` }));
  } else {
    for (const column of visible) {
      dom.columnList.append(
        el('li', { class: 'column-row' }, el('span', { class: 'col-name', title: column.name, text: column.name }), el('span', { class: 'col-type', text: column.dtype })),
      );
    }
  }
}

// The thin bar at the bottom: shows the dataset's current state, or a temporary notice.
function renderStatusBar() {
  const { kind, text } = state.notice ?? baselineStatus();
  dom.statusbar.dataset.kind = kind;
  dom.statusText.textContent = text;
}

function baselineStatus() {
  if (state.uploadError) return { kind: 'error', text: state.uploadError };
  if (state.status === 'uploading') return { kind: 'busy', text: `Loading ${state.pendingFilename}…` };
  if (state.status === 'loaded') {
    const { filename, rows, columns } = state.dataset;
    return { kind: 'success', text: `${filename} loaded · ${rows.toLocaleString()} rows · ${columns.length} columns` };
  }
  return { kind: 'neutral', text: 'No dataset loaded' };
}

function renderComposer() {
  const canType = state.status === 'loaded' || state.status === 'uploading'; // typing stays possible while loading
  dom.input.disabled = !canType;
  dom.input.placeholder = {
    loaded: 'Ask something about your dataset...',
    uploading: 'Loading your dataset...',
  }[state.status] ?? 'Upload a dataset to start asking questions';
  dom.send.disabled = state.status !== 'loaded' || state.requesting || dom.input.value.trim() === '';
}

// Rebuilds the whole conversation from state. Only used when the conversation or dataset state changes
// wholesale (start-up, clear, upload); new messages are simply appended (see appendNode).
function renderThread() {
  dom.thread.replaceChildren();

  if (!hasConversation()) {
    const intro = buildIntro(introText(), state.status === 'loaded' ? state.dataset.suggestions ?? [] : [], (text) => send(text));
    intro.dataset.role = 'intro';
    dom.thread.append(intro);
  } else {
    for (const message of state.messages) dom.thread.append(buildMessage(message, messageHandlers));
    if (state.status !== 'loaded' && state.status !== 'uploading') {
      dom.thread.append(buildNote('Restored from your last session. The dataset is not loaded: upload one to start a new conversation.'));
    }
  }
  scrollToBottom(false);
}

function introText() {
  if (state.status === 'uploading') return `Loading ${state.pendingFilename}…`;
  if (state.status === 'loaded') {
    return state.dataset.suggestions?.length
      ? `${state.dataset.filename} is ready. Ask a question below, or try one of these.`
      : `${state.dataset.filename} is ready. Ask a question about it below.`;
  }
  return 'Upload a dataset to get started.';
}

// Update everything except the conversation.
function refresh() {
  renderSidebar();
  renderStatusBar();
  renderComposer();
}

function refreshAll() {
  refresh();
  renderThread();
}

function appendNode(node) {
  node.classList.add('enter');
  dom.thread.append(node);
  scrollToBottom(true);
  // An image has no height until it has loaded, so scroll again once it does.
  node.querySelector('img')?.addEventListener('load', () => scrollToBottom(false), { once: true });
}

function scrollToBottom(smooth) {
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  dom.scroll.scrollTo({ top: dom.scroll.scrollHeight, behavior: smooth && !reduceMotion ? 'smooth' : 'auto' });
}

function notify(text, kind = 'error') {
  state.notice = { text, kind };
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => {
    state.notice = null;
    renderStatusBar();
  }, NOTICE_MS);
  renderStatusBar();
}

// ----- dataset: choose, confirm, load ----------------------------------------------

let confirmingReplace = false; // true while the "replace?" dialog is open

async function handleFileChosen(file) {
  if (!file || isBusy() || confirmingReplace) return;

  // Checked in the browser: unsupported files are never sent to the server.
  const extension = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : '';
  if (!SUPPORTED_EXTENSIONS.includes(extension)) {
    showUploadError(UNSUPPORTED_FORMAT_MESSAGE);
    return;
  }

  // Replacing something that exists needs an explicit yes. Nothing changes on Cancel.
  if (state.status === 'loaded' || hasConversation()) {
    confirmingReplace = true;
    const confirmed = await confirmReplace();
    confirmingReplace = false;
    if (!confirmed) return;
    state.working = true;
    refresh();
    await archiveCurrentConversation();
    resetConversation();
    state.working = false;
  }

  await loadDataset(file);
}

function showUploadError(text) {
  state.uploadError = text;
  if (state.status === 'none') state.status = 'error';
  clearTimeout(showUploadError.timer);
  if (state.status === 'loaded') {
    // A dataset is still loaded and untouched, so this message is only temporary.
    showUploadError.timer = setTimeout(() => {
      state.uploadError = '';
      refresh();
    }, NOTICE_MS);
  }
  refreshAll();
}

function confirmReplace() {
  return new Promise((resolve) => {
    dom.confirmDialog.returnValue = '';
    dom.confirmDialog.addEventListener('close', () => resolve(dom.confirmDialog.returnValue === 'confirm'), { once: true });
    dom.confirmDialog.showModal();
  });
}

async function loadDataset(file) {
  const filename = file.name;
  clearTimeout(showUploadError.timer);
  Object.assign(state, { status: 'uploading', dataset: null, datasetSummary: null, uploadError: '', search: '', pendingFilename: filename });
  dom.search.value = '';
  refreshAll();

  try {
    state.dataset = await api.loadDataset(file);
    state.datasetSummary = summarize(state.dataset);
    state.status = 'loaded';
  } catch (error) {
    state.status = 'error';
    state.uploadError = error instanceof api.ApiError ? error.message : 'Something went wrong while loading the dataset.';
    if (!(error instanceof api.ApiError)) console.error(error);
  }

  refreshAll();
  if (state.status === 'loaded') focusInput();
}

// ----- clear actions ----------------------------------------------------------------

async function clearConversation() {
  if (isBusy() || !hasConversation()) return;
  state.working = true;
  refresh();
  await archiveCurrentConversation();
  resetConversation();
  try {
    await api.clearConversation(); // the server keeps its own analysis memory: forget it too
  } catch {
    // Server unreachable: the screen still resets.
  }
  state.working = false;
  refreshAll(); // the loaded dataset is untouched
}

async function clearDataset() {
  if (isBusy()) return;
  state.working = true;
  refresh();
  await archiveCurrentConversation();
  resetConversation();
  try {
    await api.clearDataset();
  } catch {
    // Server unreachable: the UI still resets, and the server forgets its dataset on the next page load.
  }
  Object.assign(state, { status: 'none', dataset: null, datasetSummary: null, uploadError: '', search: '', working: false });
  dom.search.value = '';
  refreshAll();
}

function resetConversation() {
  state.messages = [];
  state.createdAt = null;
  storage.clearConversation();
}

// Send a copy of the finished conversation to the server's chats/ archive.
// This never blocks or breaks the UI: if it fails, the conversation is still cleared.
async function archiveCurrentConversation() {
  if (!hasConversation()) return;
  try {
    await api.archiveConversation({
      created_at: state.createdAt,
      dataset: state.datasetSummary,
      messages: state.messages.map(storage.toStored),
    });
  } catch (error) {
    console.warn('Could not archive the conversation:', error);
  }
}

// ----- chat -------------------------------------------------------------------------

// `suggestion` is set when a suggestion chip is clicked; otherwise the text comes from the input box.
async function send(suggestion) {
  const text = (suggestion ?? dom.input.value).trim();
  if (!text) return;                                      // empty / whitespace-only: do nothing
  if (state.status !== 'loaded' || state.requesting) return; // one request at a time; the draft is kept

  if (suggestion === undefined) {
    dom.input.value = '';
    autoGrow();
  }

  const requestId = newId();
  state.requesting = true;

  dom.thread.querySelector('[data-role="intro"]')?.remove();
  const userMessage = { request_id: requestId, role: 'user', text };
  appendNode(buildMessage(userMessage, messageHandlers));
  const typing = buildTyping();
  appendNode(typing);
  refresh();

  let reply;
  try {
    reply = await api.sendChat({ request_id: requestId, message: text });
  } catch (error) {
    const known = error instanceof api.ApiError;
    reply = { type: 'error', message: known ? error.message : 'Something went wrong. Please try again.' };
    if (known) notify(error.message);
    else console.error(error);
  }

  // The cycle is complete: it is now static history and is never rewritten.
  typing.remove();
  const assistantMessage = toAssistantMessage(requestId, reply);
  if (reply.dataset) applyModification(reply.dataset); // the server sends it whenever the dataset changed
  state.messages.push(userMessage, assistantMessage);
  state.createdAt ??= new Date().toISOString();
  state.requesting = false;
  persist();

  appendNode(buildMessage(assistantMessage, messageHandlers));
  refresh();
}

function toAssistantMessage(requestId, reply) {
  const message = { request_id: requestId, role: 'assistant', type: reply.type, text: reply.message };
  if (reply.type === 'table') {
    message.columns = reply.columns;
    message.rows = reply.rows.slice(0, MAX_TABLE_ROWS); // only the top rows are ever kept
    message.total_rows = Number.isFinite(reply.total_rows) ? reply.total_rows : reply.rows.length;
  }
  if (reply.type === 'image') {
    message.image = reply.image; // kept in memory for this session only, never saved or archived
    message.alt = reply.alt || reply.message;
  }
  return message;
}

function applyModification(dataset) {
  state.dataset = dataset;
  state.datasetSummary = summarize(dataset);
}

const summarize = (dataset) => ({ filename: dataset.filename, rows: dataset.rows, columns: dataset.columns.map((c) => c.name) });

function persist() {
  storage.saveConversation({ createdAt: state.createdAt, dataset: state.datasetSummary, messages: state.messages });
}

function newId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// ----- composer ---------------------------------------------------------------------

function autoGrow() {
  dom.input.style.height = 'auto';
  dom.input.style.height = `${Math.min(dom.input.scrollHeight, 132)}px`;
}

function focusInput() {
  if (!matchMedia('(pointer: coarse)').matches) dom.input.focus(); // don't pop the keyboard up on phones
}

// ----- image lightbox & mobile drawer -----------------------------------------------

const messageHandlers = {
  onOpenImage(src, alt) {
    dom.lightboxImg.src = src;
    dom.lightboxImg.alt = alt;
    dom.lightbox.showModal();
  },
};

function setDrawer(open) {
  document.body.dataset.drawer = open ? 'open' : 'closed';
  dom.sidebarToggle.setAttribute('aria-expanded', String(open));
}

// ----- events -----------------------------------------------------------------------

dom.uploadButton.addEventListener('click', () => dom.fileInput.click());
dom.fileInput.addEventListener('change', () => {
  const file = dom.fileInput.files[0];
  dom.fileInput.value = ''; // lets the same file be chosen twice in a row
  handleFileChosen(file);
});

dom.clearConversation.addEventListener('click', clearConversation);
dom.clearDataset.addEventListener('click', clearDataset);

// Column search is 100% client-side: no network involved.
dom.search.addEventListener('input', () => {
  state.search = dom.search.value;
  renderColumns();
});
dom.search.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && dom.search.value) {
    dom.search.value = '';
    state.search = '';
    renderColumns();
  }
});

dom.input.addEventListener('input', () => {
  autoGrow();
  renderComposer();
});
dom.input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    send();
  }
});
dom.send.addEventListener('click', () => send());

dom.lightbox.addEventListener('click', () => dom.lightbox.close());

dom.sidebarToggle.addEventListener('click', () => setDrawer(document.body.dataset.drawer !== 'open'));
dom.scrim.addEventListener('click', () => setDrawer(false));
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') setDrawer(false);
});

api.watchConnection((connected) => {
  state.connected = connected;
  renderConnection();
});

// Last-resort safety net for anything unexpected.
function reportUnexpected(error) {
  console.error(error);
  notify('Something went wrong. Please try again.');
}
window.addEventListener('error', (event) => reportUnexpected(event.error));
window.addEventListener('unhandledrejection', (event) => reportUnexpected(event.reason));

// ----- start-up ---------------------------------------------------------------------

async function init() {
  // Restore the active conversation. The dataset itself is NOT restored: the UI starts at "No dataset".
  const saved = storage.loadConversation();
  if (saved) {
    state.messages = saved.messages;
    state.createdAt = saved.createdAt;
    state.datasetSummary = saved.dataset;
  }
  renderConnection();
  refreshAll();

  // The server may still hold a dataset from before the refresh. Clear it so both sides agree,
  // which also tells us whether the server is reachable.
  try {
    await api.clearDataset();
  } catch {
    // the connection indicator already shows "Disconnected"
  }
}

init();
