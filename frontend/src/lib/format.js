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
  let str = asText(val).trim();

  // Auto-unwrap raw JSON objects if raw JSON string was passed or recorded
  if (str.startsWith('{') && str.endsWith('}')) {
    try {
      const parsed = JSON.parse(str);
      if (parsed.jawaban) {
        str = String(parsed.jawaban).trim();
      }
    } catch {
      // Not valid JSON, keep str as is
    }
  }

  // Auto-fix inline list numbering " text 1. Item" -> linebreaks
  str = str.replace(/(\s)(\d+\.\s+[A-Z])/g, '\n\n$2');
  return marked.parse(str);
}

export function renderSources(sumber) {
  const list = Array.isArray(sumber) ? sumber : [sumber];
  const hasUrls = list.some((s) => String(s).trim().startsWith('http'));
  if (!hasUrls) return `<span>${escapeHtml(asText(sumber))}</span>`;
  return (
    `<div class="sources-flex">` +
    list.map((src) => {
      const str = String(src).trim();
      if (!/^https?:\/\//.test(str)) {
        return `<span class="source-link">${escapeHtml(str)}</span>`;
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

  const hasMeta = data.topik || data.sumber || data.dokumen?.length;
  if (hasMeta) {
    html += `<div class="meta-chips">`;
    if (data.topik) {
      html += `
        <div class="meta-chip">
          <span class="chip-label">TOPIK</span>
          <span class="chip-val">${escapeHtml(asText(data.topik))}</span>
        </div>`;
    }
    if (data.sumber) {
      html += `
        <div class="meta-chip">
          <span class="chip-label">SUMBER</span>
          <span class="chip-val">${renderSources(data.sumber)}</span>
        </div>`;
    }
    if (data.dokumen?.length) {
      html += `
        <div class="meta-chip">
          <span class="chip-label">RAG DOCS</span>
          <span class="chip-val">${data.dokumen.map((d) => escapeHtml(d)).join(', ')}</span>
        </div>`;
    }
    html += `</div>`;
  }

  return html;
}
