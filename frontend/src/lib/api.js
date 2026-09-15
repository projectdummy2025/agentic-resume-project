const API_BASE = '/api';

async function request(path, options = {}) {
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
      throw new Error(data.detail || `HTTP Error ${res.status}: Gagal memproses permintaan`);
    }
    return data;
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Permintaan timeout (20s)');
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

export async function getSessionDocuments(sessionId) {
  return request(`/session/${sessionId}/documents`, { method: 'GET' });
}

export async function chat(text, promptStyle, sessionId) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ text, prompt_style: promptStyle, session_id: sessionId }),
  });
}

export async function analyze(text, promptStyle, sessionId) {
  return chat(text, promptStyle, sessionId);
}

export async function chatStream(text, promptStyle, sessionId, onChunk, onDocuments, onDone, onError) {
  try {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, prompt_style: promptStyle, session_id: sessionId }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP Error ${res.status}: Gagal memproses pesan`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.error) {
              if (onError) onError(new Error(payload.error));
              return;
            }
            if (payload.documents && onDocuments) {
              onDocuments(payload.documents);
            }
            if (payload.chunk && onChunk) {
              onChunk(payload.chunk);
            }
            if (payload.done && onDone) {
              onDone(payload.full_text);
            }
          } catch (e) {
            console.error('Gagal membaca data stream', e);
          }
        }
      }
    }
  } catch (err) {
    if (onError) onError(err);
    else throw err;
  }
}

export async function ingestPdf(file, sessionId) {
  const form = new FormData();
  form.append('file', file);
  form.append('session_id', sessionId);
  const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Gagal mengunggah dokumen');
  return data;
}
