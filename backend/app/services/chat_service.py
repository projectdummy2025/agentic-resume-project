import re
from ..core.config import get_openai_client, OPENAI_COMPATIBLE_MODEL
from . import rag_service as rag


def generateSessionTitle(userText: str) -> str:
    cleanText = re.sub(r"[^\w\s]", "", userText).strip()
    words = cleanText.split()
    if not words:
        return "Sesi Baru"
    titleStr = " ".join(words[:5])
    return titleStr[:36].strip().capitalize()


def format_academic_response(text: str) -> str:
    if not text:
        return text
    cleaned = re.sub(r"[–——–]", "", text)
    lines = []
    for line in cleaned.splitlines():
        if line.lstrip().startswith("- ") or line.lstrip().startswith("* "):
            line = re.sub(r"^(\s*)([-*])\s+", r"\1", line)
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"(?<!https)(?<!http)(?<!\d)(?<!\s):", " :", cleaned)
    return cleaned


def should_condense_query(query: str, history_len: int) -> bool:
    if history_len < 2:
        return False
    query_lower = query.lower()
    ambiguous_tokens = ["itu", "ini", "tersebut", "dia", "nya", "mereka", "ia", "it", "they", "them", "this", "that"]
    words = re.findall(r"\b\w+\b", query_lower)
    if len(words) < 7 or any(w in ambiguous_tokens for w in words):
        return True
    return False


def condense_query(query: str, history_text: str) -> str:
    if not history_text:
        return query
    try:
        client = get_openai_client()
        res = client.chat.completions.create(
            model=OPENAI_COMPATIBLE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tugasmu: Gabungkan riwayat percakapan dan pertanyaan terbaru pengguna "
                        "menjadi 1 kalimat pertanyaan pencarian yang mandiri, eksplisit, dan spesifik. "
                        "Output HANYA kalimat pertanyaan tanpa awalan/penjelasan."
                    ),
                },
                {"role": "user", "content": f"Riwayat Percakapan:\n{history_text}\n\nPertanyaan Terbaru: {query}"},
            ],
            temperature=0.2,
            max_tokens=80,
        )
        if res.choices and res.choices[0].message and res.choices[0].message.content:
            condensed = res.choices[0].message.content.strip()
            return condensed or query
        return query
    except Exception as e:
        print(f"Query condensation fallback: {e}")
        return query


def enrichQuery(userQuery: str, sessionId: str) -> str:
    summaryKeywords = ["dibahas", "isi", "ringkasan", "rangkum", "tentang", "overview", "summary", "bahan", "topik"]
    isSummaryRequest = any(keyword in userQuery.lower() for keyword in summaryKeywords) or len(userQuery.split()) < 4
    if isSummaryRequest:
        documentSources = rag.get_document_sources(sessionId)
        if documentSources:
            sourceString = " ".join(documentSources)
            return f"{userQuery} {sourceString}"
    return userQuery
