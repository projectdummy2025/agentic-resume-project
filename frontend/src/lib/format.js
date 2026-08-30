import { marked } from 'marked';

export function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (m) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m]
  ));
}

function asText(val) {
  if (val === null || val === undefined) return '-';
  if (typeof val === 'object') return JSON.stringify(val, null, 2);
  return String(val);
}

export function renderMarkdown(val) {
  if (!val) return '';
  let str = asText(val);
  // Auto-fix inline list numbering " text 1. Item" -> linebreaks
  str = str.replace(/(\s)(\d+\.\s+[A-Z])/g, '\n\n$2');
  return marked.parse(str);
}

export function renderSources(sumber) {
  const list = Array.isArray(sumber) ? sumber : [sumber];
  const hasUrls = list.some((s) => String(s).trim().startsWith('http'));
  if (!hasUrls) return `<div>${escapeHtml(asText(sumber))}</div>`;
  return (
    `<div class="sources-flex">` +
    list.map((src) => {
      const str = String(src).trim();
      if (!/^https?:\/\//.test(str)) {
        return `<span class="source-link" style="color: var(--text-primary); background: var(--surface-color); border-color: var(--border-color);">${escapeHtml(str)}</span>`;
      }
      try {
        const host = new URL(str).hostname;
        return `<a href="${escapeHtml(str)}" target="_blank" rel="noopener" class="source-link">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
          ${escapeHtml(host)}
        </a>`;
      } catch {
        return `<a href="${escapeHtml(str)}" target="_blank" rel="noopener" class="source-link">${escapeHtml(str)}</a>`;
      }
    }).join('') +
    `</div>`
  );
}

export function renderResult(data) {
  let html = '';
  if (data.reasoning) {
    html += `
      <details class="thinking-accordion">
        <summary>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          <span>Thinking process</span>
        </summary>
        <div class="thinking-body">${escapeHtml(asText(data.reasoning))}</div>
      </details>`;
  }
  if (data.jawaban) html += `<div class="result-block">${renderMarkdown(data.jawaban)}</div>`;
  if (data.topik) {
    html += `
      <div class="meta-card">
        <div class="meta-label">Topik</div>
        <div class="meta-value">${escapeHtml(asText(data.topik))}</div>
      </div>`;
  }
  if (data.sumber) {
    html += `
      <div class="meta-card">
        <div class="meta-label">Sumber</div>
        <div class="meta-value">${renderSources(data.sumber)}</div>
      </div>`;
  }
  if (data.dokumen?.length) {
    html += `
      <div class="meta-card">
        <div class="meta-label">Dokumen RAG</div>
        <div class="meta-value">${data.dokumen.map((d) => escapeHtml(d)).join(', ')}</div>
      </div>`;
  }
  html += `
    <button class="json-toggle-btn" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block'; this.querySelector('span').textContent = this.nextElementSibling.style.display === 'block' ? 'Sembunyikan Raw JSON' : 'Tampilkan Raw JSON'">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
      <span>Tampilkan Raw JSON</span>
    </button>
    <pre class="raw-json-block" style="display:none">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
  return html;
}
