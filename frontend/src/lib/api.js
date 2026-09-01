const API_BASE = '/api';

async function request(path, options = {}) {
  // Prevent sending requests for draft sessions defensively
  if (path.includes('draft-')) {
    throw new Error('Sesi ini belum disimpan.');
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options,
    });
    clearTimeout(timeout);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (res.status === 404) {
        throw new Error('Sesi tidak ditemukan atau belum disimpan.');
      }
      throw new Error(data.detail || 'Gagal memproses permintaan');
    }
    return data;
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Permintaan timeout');
    }
    if (options.retry && err instanceof TypeError) {
      return request(path, { ...options, retry: false });
    }
    throw err;
  }
}

export async function createSession(sessionId = null, title = null) {
  return request('/session', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, title }),
  });
}

export async function listSessions() {
  return request('/sessions', { method: 'GET' });
}

export async function renameSession(id, title) {
  return request(`/session/${id}/rename`, {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function deleteSession(id) {
  return request(`/session/${id}`, { method: 'DELETE' });
}

export async function getMessages(sessionId) {
  return request(`/session/${sessionId}/messages`, { method: 'GET' });
}

export async function chat(text, promptStyle, sessionId) {
  if (sessionId && sessionId.startsWith('draft-')) throw new Error('Sesi ini belum disimpan.');
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ text, prompt_style: promptStyle, session_id: sessionId, use_rag: false }),
  });
}

export async function analyze(text, promptStyle, sessionId) {
  if (sessionId && sessionId.startsWith('draft-')) throw new Error('Sesi ini belum disimpan.');
  return request('/analyze', {
    method: 'POST',
    body: JSON.stringify({ text, prompt_style: promptStyle, session_id: sessionId, use_rag: true }),
  });
}

export async function ingestPdf(file, sessionId) {
  const form = new FormData();
  form.append('file', file);
  form.append('session_id', sessionId);
  const res = await fetch('/api/ingest', { method: 'POST', body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Gagal mengunggah dokumen');
  return data;
}
