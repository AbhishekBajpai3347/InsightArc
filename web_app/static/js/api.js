// The only module that talks to the local FastAPI server.
// Every failure is turned into an ApiError with a message that is safe to show the user.

export class ApiError extends Error {}

// Connection status comes from ordinary requests (no polling):
// a request that reaches the server = connected, a network failure = disconnected.
let onConnectionChange = () => {};
export function watchConnection(callback) {
  onConnectionChange = callback;
}

async function request(method, path, body, extraOptions = {}) {
  let response;
  try {
    response = await fetch(path, {
      method,
      // A FormData body (file upload) must NOT get a Content-Type: the browser adds its own, with the boundary.
      headers: body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : undefined,
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
      ...extraOptions,
    });
  } catch {
    onConnectionChange(false);
    throw new ApiError('Cannot reach the local server. Make sure it is running and try again.');
  }
  onConnectionChange(true);

  let data = null;
  try {
    data = await response.json();
  } catch {
    // Not JSON (for example a plain-text 500 page).
  }

  if (!response.ok) {
    throw new ApiError(errorDetail(data) || `The server returned an error (HTTP ${response.status}).`);
  }
  if (data === null) throw new ApiError('The server sent a response that could not be read.');
  return data;
}

// FastAPI errors look like {"detail": "text"} or {"detail": [{"msg": "..."}]}.
function errorDetail(data) {
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => String(item?.msg ?? '').replace(/^Value error, /, ''))
      .filter(Boolean)
      .join(' ');
  }
  return '';
}

// ----- public functions -------------------------------------------------------------

export async function loadDataset(file) {
  const form = new FormData();
  form.append('file', file, file.name);
  const data = await request('POST', '/api/dataset/load', form);
  if (!isDataset(data.dataset)) throw new ApiError('The server sent an unexpected response.');
  return data.dataset;
}

export function clearDataset() {
  return request('POST', '/api/dataset/clear', {});
}

export async function sendChat(payload) {
  return validateResult(await request('POST', '/api/chat', payload));
}

// Forget the server's analysis memory (the dataset stays loaded).
export function clearConversation() {
  return request('POST', '/api/conversation/clear', {});
}

export function archiveConversation(payload) {
  return request('POST', '/api/archive', payload);
}

// ----- result contract --------------------------------------------------------------
// Whatever produces results (today: the mock, later: the real engine) must return one of:
//   { type: 'final',        message }
//   { type: 'table',        message, columns: [...], rows: [[...]], total_rows? }
//   { type: 'image',        message, image: '<base64 PNG>', alt? }
//   { type: 'modification', message, dataset: { filename, rows, columns: [{name, dtype}] } }
//   { type: 'error',        message }
// ANY reply may also carry `dataset` (same shape) when the dataset changed during that turn,
// so the sidebar always matches the data, even if the last output was a table or a chart.

const RESULT_TYPES = ['final', 'table', 'image', 'modification', 'error'];
const PNG_BASE64_PREFIX = 'iVBORw0KGgo'; // every PNG file starts with these bytes

function isDataset(d) {
  return (
    d &&
    typeof d.filename === 'string' &&
    Number.isFinite(d.rows) &&
    Array.isArray(d.columns) &&
    d.columns.every((c) => typeof c?.name === 'string' && typeof c?.dtype === 'string')
  );
}

function validateResult(result) {
  const unexpected = () => new ApiError('The server sent an unexpected response.');
  if (!result || !RESULT_TYPES.includes(result.type) || typeof result.message !== 'string') throw unexpected();
  if (result.type === 'table' && !(Array.isArray(result.columns) && Array.isArray(result.rows))) throw unexpected();
  if (result.type === 'image' && !(typeof result.image === 'string' && result.image.startsWith(PNG_BASE64_PREFIX))) throw unexpected();
  if (result.type === 'modification' && !isDataset(result.dataset)) throw unexpected();
  if (result.dataset != null && !isDataset(result.dataset)) throw unexpected();
  return result;
}
