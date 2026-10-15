import re
from datetime import datetime
from app.core.config import get_openai_client, OPENAI_COMPATIBLE_MODEL
from app.services import session_service as sessions
from app.services import rag_service as rag

SUMMARY_PROMPT = (
    "Kamu adalah penyusun dokumen profesional. Buat satu dokumen ringkasan komprehensif dan objektif "
    "dalam format Markdown dari ringkasan bahan yang diberikan.\n\n"
    "STRUKTUR WAJIB:\n"
    "# [Judul representatif]\n\n"
    "## Ringkasan Eksekutif\n"
    "## Poin Pembahasan Kunci\n"
    "## Temuan dan Keputusan\n"
    "## Sumber Rujukan Dokumen\n\n"
    "Gunakan bahasa Indonesia baku. Jangan menulis salam, pembungkus kode, atau informasi yang tidak ada dalam bahan. "
    "Pada bagian sumber, cantumkan nama file asli dan halaman yang relevan."
)

BATCH_PROMPT = (
    "Ringkas bahan berikut secara faktual dalam Markdown. Pertahankan semua keputusan, temuan, angka, nama, "
    "serta penanda [Dokumen: ... | Halaman: ...] yang relevan. Jangan menambah informasi baru."
)

MAX_BATCH_CHARS = 28000


def buildSessionContext(sessionId: str) -> dict:
    # Ambil seluruh riwayat percakapan sesi secara berurutan
    rawMessages = sessions.get_messages(sessionId)
    chatSections = []
    for message in rawMessages:
        roleLabel = "Pengguna" if message.get("role") == "user" else "Asisten"
        content = message.get("content", "").strip()
        if content:
            chatSections.append(f"{roleLabel}: {content}")

    # Ambil seluruh chunk RAG dan hilangkan overlap dari proses chunking
    rawChunks = rag.get_document_chunks(sessionId)
    documentSections = []
    previousChunks = {}
    for chunk in rawChunks:
        content = chunk["text"].strip()
        documentKey = (chunk["source"], chunk["page"])
        previousText = previousChunks.get(documentKey, "")
        overlap = previousText[-60:]
        if overlap and content.startswith(overlap):
            content = content[len(overlap):].lstrip()
        previousChunks[documentKey] = chunk["text"].strip()
        if content:
            documentSections.append(
                f"[Dokumen: {chunk['source']} | Halaman: {chunk['page']}]\n{content}"
            )

    return {
        "chat_sections": chatSections,
        "document_sections": documentSections,
        "sources": _sourcePages(rawChunks),
        "message_count": len(rawMessages),
        "chunk_count": len(rawChunks),
    }


def generateSessionSummary(sessionId: str, titleHint: str | None = None) -> dict:
    context = buildSessionContext(sessionId)
    if context["message_count"] == 0 and context["chunk_count"] == 0:
        raise ValueError("Sesi tidak memiliki riwayat percakapan maupun dokumen untuk diringkas")

    # Ringkas setiap batch agar seluruh chat dan chunk dokumen tetap diproses
    allSections = [
        "=== RIWAYAT PERCAKAPAN ===\n" + "\n\n".join(context["chat_sections"]),
        "=== DOKUMEN RAG ===\n" + "\n\n---\n\n".join(context["document_sections"]),
    ]
    batches = _buildBatches([section for section in allSections if section.strip()])
    client = get_openai_client()
    batchSummaries = []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"({timestamp}) Generating session summary for session {sessionId}")

    for batch in batches:
        batchSummaries.append(_complete(client, BATCH_PROMPT, batch))

    # Reduksi berulang saat gabungan ringkasan batch masih melebihi context model
    while len("\n\n---\n\n".join(batchSummaries)) > MAX_BATCH_CHARS:
        batchSummaries = [
            _complete(client, BATCH_PROMPT, batch)
            for batch in _buildBatches(batchSummaries)
        ]

    sourceList = "\n".join(
        f"- {source} (Halaman {', '.join(str(page) for page in pages)})"
        for source, pages in context["sources"].items()
    ) or "- Tidak ada dokumen sumber"

    finalMaterial = (
        "=== RINGKASAN SELURUH BAHAN ===\n"
        + "\n\n---\n\n".join(batchSummaries)
        + "\n\n=== SUMBER WAJIB ===\n"
        + sourceList
    )
    rawMarkdown = _complete(client, SUMMARY_PROMPT, finalMaterial)
    cleanMarkdown = _cleanMarkdown(rawMarkdown)
    cleanMarkdown = _ensureSources(cleanMarkdown, sourceList)

    firstLine = cleanMarkdown.splitlines()[0] if cleanMarkdown.splitlines() else "Ringkasan Sesi"
    extractedTitle = re.sub(r"^[#\s]+", "", firstLine).strip()
    documentTitle = extractedTitle or titleHint or "Ringkasan Dokumen Sesi"

    return {
        "title": documentTitle,
        "markdown": cleanMarkdown,
        "sources": list(context["sources"].keys()),
    }


def _buildBatches(sections: list[str]) -> list[str]:
    batches = []
    currentParts = []
    currentLength = 0

    for section in sections:
        remaining = section
        while remaining:
            available = MAX_BATCH_CHARS - currentLength
            if available <= 0:
                batches.append("\n\n".join(currentParts))
                currentParts = []
                currentLength = 0
                available = MAX_BATCH_CHARS

            if len(remaining) <= available:
                currentParts.append(remaining)
                currentLength += len(remaining)
                remaining = ""
                continue

            splitAt = remaining.rfind("\n\n", 0, available)
            if splitAt < available // 2:
                splitAt = available
            currentParts.append(remaining[:splitAt])
            batches.append("\n\n".join(currentParts))
            currentParts = []
            currentLength = 0
            remaining = remaining[splitAt:].lstrip()

    if currentParts:
        batches.append("\n\n".join(currentParts))

    return batches


def _sourcePages(chunks: list[dict]) -> dict[str, list[int]]:
    sources = {}
    for chunk in chunks:
        source = chunk["source"]
        page = chunk["page"]
        sources.setdefault(source, [])
        if page not in sources[source]:
            sources[source].append(page)
    return sources


def _complete(client, systemPrompt: str, userPrompt: str) -> str:
    response = client.chat.completions.create(
        model=OPENAI_COMPATIBLE_MODEL,
        messages=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": userPrompt},
        ],
        temperature=0.2,
    )
    if not response.choices or not response.choices[0].message:
        raise RuntimeError("Model tidak mengembalikan ringkasan")
    content = response.choices[0].message.content or ""
    if not content.strip():
        raise RuntimeError("Model mengembalikan ringkasan kosong")
    return content.strip()


def _cleanMarkdown(markdownText: str) -> str:
    cleanMarkdown = markdownText.strip()
    if cleanMarkdown.startswith("```markdown"):
        cleanMarkdown = cleanMarkdown[11:].strip()
    elif cleanMarkdown.startswith("```"):
        cleanMarkdown = cleanMarkdown[3:].strip()
    if cleanMarkdown.endswith("```"):
        cleanMarkdown = cleanMarkdown[:-3].strip()
    return cleanMarkdown


def _ensureSources(markdownText: str, sourceList: str) -> str:
    sourceHeading = "## Sumber Rujukan Dokumen"
    if sourceHeading not in markdownText:
        return f"{markdownText}\n\n{sourceHeading}\n\n{sourceList}"

    beforeSources = markdownText.split(sourceHeading, 1)[0].rstrip()
    return f"{beforeSources}\n\n{sourceHeading}\n\n{sourceList}"
