import json
import re
from ..core.config import get_openai_client, OPENAI_COMPATIBLE_MODEL
from . import rag_service as rag

GREETING_PATTERNS = [
    r"^(halo|hai|hello|hi|hei)\b",
    r"^(selamat\s+(pagi|siang|sore|malam))\b",
    r"^(terima\s+kasih|makasih|thanks|thank\s+you)\b",
    r"^(ok|oke|sip|siap|baiklah|mantap)\b",
    r"^(siapa\s+(kamu|namamu|anda))\b",
    r"^(tes|test|ping)\b",
]

DOCUMENT_KEYWORDS = [
    "dokumen", "pdf", "file", "halaman", "resume", "cv",
    "lampiran", "berkas", "catatan", "penulis", "isi dokumen",
    "summary", "ringkasan", "paragraf", "bab", "sitasi",
]

AMBIGUOUS_TOKENS = [
    "itu", "ini", "tersebut", "dia", "nya", "mereka", "ia",
    "tadi", "sebelumnya", "kedua", "pertama", "terakhir",
    "it", "they", "them", "this", "that",
]

FOLLOW_UP_PHRASES = [
    "mengapa", "kenapa", "bagaimana", "lalu", "terus",
    "kenapa begitu", "apa maksudnya", "jelaskan lagi", "contohnya", "detailnya",
]


def generateSessionTitle(userText: str) -> str:
    cleanText = re.sub(r"[^\w\s]", "", userText).strip()
    words = cleanText.split()
    if not words:
        return "Sesi Baru"
    titleStr = " ".join(words[:5])
    return titleStr[:36].strip().capitalize()


def detectIntent(userQuery: str, hasDocuments: bool = False) -> str:
    # Periksa apakah pesan adalah sapaan umum atau basa-basi santai
    queryLower = userQuery.strip().lower()
    for patternItem in GREETING_PATTERNS:
        if re.search(patternItem, queryLower):
            return "chitchat"

    # Jika sesi memiliki dokumen, periksa indikator pencarian dokumen
    if hasDocuments:
        for keywordItem in DOCUMENT_KEYWORDS:
            if keywordItem in queryLower:
                return "document"
        return "document"

    return "general"


def shouldCondense(queryText: str, historyLength: int) -> bool:
    # Sesi baru atau tanpa riwayat tidak memerlukan kondensasi query
    if historyLength < 2:
        return False

    queryLower = queryText.strip().lower()

    # Jangan lakukan kondensasi untuk sapaan atau pesan pembuka
    for patternItem in GREETING_PATTERNS:
        if re.search(patternItem, queryLower):
            return False

    words = re.findall(r"\b\w+\b", queryLower)

    # Periksa token rujukan ambigu ke percakapan sebelumnya
    hasAmbiguousToken = any(token in AMBIGUOUS_TOKENS for token in words)
    if hasAmbiguousToken:
        return True

    # Periksa pertanyaan lanjutan singkat yang bergantung pada riwayat
    isShortFollowUp = len(words) <= 4 and any(phrase in queryLower for phrase in FOLLOW_UP_PHRASES)
    if isShortFollowUp:
        return True

    return False


def condenseQuery(queryText: str, historyText: str) -> str:
    # Kembalikan query awal jika belum ada riwayat obrolan
    if not historyText:
        return queryText
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
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
                {"role": "user", "content": f"Riwayat Percakapan:\n{historyText}\n\nPertanyaan Terbaru: {queryText}"},
            ],
            temperature=0.2,
            max_tokens=80,
        )
        if response.choices and response.choices[0].message and response.choices[0].message.content:
            condensedText = response.choices[0].message.content.strip()
            return condensedText or queryText
        return queryText
    except Exception as error:
        print(f"Query condensation fallback: {error}")
        return queryText


def enrichQuery(userQuery: str, sessionId: str) -> str:
    summaryKeywords = ["dibahas", "isi", "ringkasan", "rangkum", "tentang", "overview", "summary", "bahan", "topik"]
    isSummaryRequest = any(keyword in userQuery.lower() for keyword in summaryKeywords) or len(userQuery.split()) < 4
    if isSummaryRequest:
        documentSources = rag.get_document_sources(sessionId)
        if documentSources:
            sourceString = " ".join(documentSources)
            return f"{userQuery} {sourceString}"
    return userQuery


def buildHistory(historyMessages: list[dict], maxRecent: int = 6) -> list[dict]:
    # Gunakan semua riwayat langsung jika jumlah pesan masih di bawah batas
    if len(historyMessages) <= maxRecent:
        return [
            {"role": messageItem["role"], "content": messageItem["content"]}
            for messageItem in historyMessages
        ]

    # Pisahkan pesan lama dan pesan terkini untuk menjaga kontinuitas
    olderMessages = historyMessages[:-maxRecent]
    recentMessages = historyMessages[-maxRecent:]

    topics = []
    for messageItem in olderMessages:
        if messageItem.get("role") == "user":
            snippet = messageItem.get("content", "").strip().replace("\n", " ")
            if len(snippet) > 80:
                snippet = snippet[:80] + "..."
            if snippet:
                topics.append(snippet)

    # Susun ringkasan topik lama sebagai konteks pemandu
    contextSummary = "Topik yang telah didiskusikan sebelumnya dalam sesi ini:\n- " + "\n- ".join(topics[-4:])
    formattedHistory = [{"role": "system", "content": contextSummary}]

    for messageItem in recentMessages:
        formattedHistory.append({"role": messageItem["role"], "content": messageItem["content"]})

    return formattedHistory


def cleanResponse(rawText: str) -> str:
    # Kembalikan teks asli jika kosong
    if not rawText:
        return rawText

    cleanedText = rawText.strip()

    # Bersihkan pembungkus JSON bocor jika model mengembalikan format JSON mentah
    if cleanedText.startswith("{") and cleanedText.endswith("}"):
        try:
            parsedObject = json.loads(cleanedText)
            if "jawaban" in parsedObject:
                cleanedText = str(parsedObject["jawaban"]).strip()
        except Exception:
            pass

    # Rapikan spasi berlebih antar paragraf tanpa merusak bullet list Markdown
    cleanedText = re.sub(r"\n{3,}", "\n\n", cleanedText)
    return cleanedText


# Alias untuk menjaga kompatibilitas impor yang sudah ada
format_academic_response = cleanResponse
should_condense_query = shouldCondense
condense_query = condenseQuery
