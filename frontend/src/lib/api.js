export async function analyze(text, promptStyle) {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, prompt_style: promptStyle })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal memproses permintaan');
  return data;
}

export async function ingestPdf(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/api/ingest', { method: 'POST', body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Gagal mengunggah dokumen');
  return data;
}
