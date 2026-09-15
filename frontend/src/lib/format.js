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

// Clean page tags (e.g. "doc.pdf (hal. 3)" -> "doc.pdf")
export function cleanDocumentName(docName) {
  if (!docName) return '';
  return String(docName).replace(/\s*\(hal\.\s*\d+\)$/i, '').trim();
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

  // Strip any raw inline source brackets [Sumber: ...] from response body
  str = str.replace(/\[Sumber:\s*[^\]]+\]/gi, '');

  return marked.parse(str);
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

  const sourcesList = data.dokumen || (data.sumber ? (Array.isArray(data.sumber) ? data.sumber : [data.sumber]) : []);
  if (sourcesList.length > 0) {
    const cleanList = Array.from(new Set(sourcesList.map(cleanDocumentName))).filter(Boolean);
    if (cleanList.length > 0) {
      const docPills = cleanList.map((d) => `
        <span class="inline-citation">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span class="cite-name">${escapeHtml(d)}</span>
        </span>
      `).join('');
      html += `<div class="sources-under-chat">${docPills}</div>`;
    }
  }

  return html;
}
