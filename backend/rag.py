import os
import re
import uuid
from chromadb import PersistentClient
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest

CHROMA_DIR = os.getenv("CHROMA_DIR", "/data/chroma")
MAX_BM25_SESSIONS = 50

# In-memory store for BM25 indexes per session
# Format: { session_id: { "bm25": BM25Okapi, "chunks": list[dict] } }
_BM25_STORES: dict[str, dict] = {}

# Singleton instances
_CHROMA_CLIENT = None
_FLASHRANK_RANKER = None


def _client():
    global _CHROMA_CLIENT
    if _CHROMA_CLIENT is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _CHROMA_CLIENT = PersistentClient(path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))
    return _CHROMA_CLIENT


def _get_ranker():
    global _FLASHRANK_RANKER
    if _FLASHRANK_RANKER is None:
        cache_dir = os.getenv("FLASHRANK_CACHE_DIR", "/tmp/flashrank_models")
        os.makedirs(cache_dir, exist_ok=True)
        _FLASHRANK_RANKER = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir=cache_dir)
    return _FLASHRANK_RANKER


def _collection(session_id: str):
    name = f"session-{session_id}"
    return _client().get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _recursive_chunk(text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", " ", ""]

    def _split(txt: str, seps: list[str]) -> list[str]:
        if len(txt) <= chunk_size or not seps:
            return [txt] if txt.strip() else []
        sep = seps[0]
        parts = txt.split(sep)
        res, current = [], ""
        for part in parts:
            item = part if not current else sep + part
            if len(current) + len(item) <= chunk_size:
                current += item
            else:
                if current.strip():
                    res.append(current.strip())
                current = part
        if current.strip():
            res.append(current.strip())

        final = []
        for c in res:
            if len(c) > chunk_size and len(seps) > 1:
                final.extend(_split(c, seps[1:]))
            else:
                final.append(c)
        return final

    raw_chunks = _split(text, separators)
    if not raw_chunks:
        return []

    chunks_with_overlap = []
    for i, c in enumerate(raw_chunks):
        if i == 0:
            chunks_with_overlap.append(c)
        else:
            prev_tail = raw_chunks[i - 1][-overlap:] if len(raw_chunks[i - 1]) >= overlap else raw_chunks[i - 1]
            chunks_with_overlap.append(f"{prev_tail} {c}")
    return chunks_with_overlap


def _save_bm25_store(session_id: str, store: dict):
    # Enforce memory cap on in-memory dictionary to prevent memory leak
    if len(_BM25_STORES) >= MAX_BM25_SESSIONS and session_id not in _BM25_STORES:
        oldest_key = next(iter(_BM25_STORES))
        del _BM25_STORES[oldest_key]
    _BM25_STORES[session_id] = store


def _ensure_bm25_store(session_id: str) -> dict | None:
    """Auto-rebuild BM25 store from ChromaDB if not present in memory (e.g. server restart or eviction)."""
    if session_id in _BM25_STORES:
        return _BM25_STORES[session_id]

    collection = _collection(session_id)
    if collection.count() == 0:
        return None

    res = collection.get()
    ids = res.get("ids", [])
    docs = res.get("documents", [])
    metas = res.get("metadatas", [])

    chunks = []
    for doc_id, doc, meta in zip(ids, docs, metas):
        chunks.append({
            "id": doc_id,
            "text": doc,
            "metadata": meta or {}
        })

    if not chunks:
        return None

    corpus_tokens = [_tokenize(c["text"]) for c in chunks]
    bm25_index = BM25Okapi(corpus_tokens) if corpus_tokens else None

    store = {
        "bm25": bm25_index,
        "chunks": chunks
    }
    _save_bm25_store(session_id, store)
    return store


def has_documents(session_id: str) -> bool:
    try:
        collection = _collection(session_id)
        return collection.count() > 0
    except Exception:
        return False


def get_document_sources(session_id: str) -> list[str]:
    try:
        collection = _collection(session_id)
        if collection.count() == 0:
            return []
        res = collection.get()
        metas = res.get("metadatas", [])
        sources = list(dict.fromkeys(m.get("source") for m in metas if m and "source" in m))
        return sources
    except Exception:
        return []


def ingest_pdf_pages(session_id: str, filename: str, pages: list[dict]) -> int:
    """
    Ingest PDF pages incrementally into ChromaDB and BM25 store.
    pages: list of dict {'page': int, 'text': str}
    """
    all_chunks = []
    chunk_counter = 0
    upload_suffix = uuid.uuid4().hex[:6]

    for page_data in pages:
        page_num = page_data.get("page", 1)
        raw_text = page_data.get("text", "")
        chunks = _recursive_chunk(raw_text)

        for text in chunks:
            chunk_id = f"{filename}-p{page_num}-c{chunk_counter}-{upload_suffix}"
            all_chunks.append({
                "id": chunk_id,
                "text": text,
                "metadata": {
                    "source": filename,
                    "page": page_num,
                    "chunk_id": chunk_id,
                }
            })
            chunk_counter += 1

    if not all_chunks:
        return 0

    # 1. Incremental Add to ChromaDB (Dense)
    collection = _collection(session_id)
    ids = [c["id"] for c in all_chunks]
    documents = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]
    collection.add(documents=documents, ids=ids, metadatas=metadatas)

    # 2. Update In-Memory BM25 Index (Incremental Sparse)
    _ensure_bm25_store(session_id)
    existing_store = _BM25_STORES.get(session_id, {"chunks": []})
    combined_chunks = existing_store["chunks"] + all_chunks
    corpus_tokens = [_tokenize(c["text"]) for c in combined_chunks]
    bm25_index = BM25Okapi(corpus_tokens) if corpus_tokens else None

    _save_bm25_store(session_id, {
        "bm25": bm25_index,
        "chunks": combined_chunks
    })

    return len(all_chunks)


def ingest(session_id: str, filename: str, text: str) -> int:
    """Backward compatibility fallback for single string text."""
    return ingest_pdf_pages(session_id, filename, [{"page": 1, "text": text}])


def query_dense(session_id: str, query: str, top_k: int = 10) -> list[dict]:
    collection = _collection(session_id)
    if collection.count() == 0:
        return []
    n = min(top_k, collection.count())
    res = collection.query(query_texts=[query], n_results=n)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    ids = res.get("ids", [[]])[0]

    output = []
    for doc_id, doc, meta in zip(ids, docs, metas):
        output.append({
            "id": doc_id,
            "text": doc,
            "metadata": meta or {},
            "source": (meta or {}).get("source", "dokumen"),
            "page": (meta or {}).get("page", 1)
        })
    return output


def query_bm25(session_id: str, query: str, top_k: int = 10) -> list[dict]:
    store = _ensure_bm25_store(session_id)
    if not store or not store.get("bm25") or not store.get("chunks"):
        return []

    bm25_index: BM25Okapi = store["bm25"]
    chunks: list[dict] = store["chunks"]

    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = bm25_index.get_scores(tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    output = []
    for idx in top_indices:
        if scores[idx] > 0:
            c = chunks[idx]
            output.append({
                "id": c["id"],
                "text": c["text"],
                "metadata": c["metadata"],
                "source": c["metadata"].get("source", "dokumen"),
                "page": c["metadata"].get("page", 1),
                "bm25_score": float(scores[idx])
            })
    return output


def reciprocal_rank_fusion(dense_results: list[dict], sparse_results: list[dict], k: int = 60, top_n: int = 8) -> list[dict]:
    rrf_scores: dict[str, float] = {}
    doc_lookup: dict[str, dict] = {}

    for rank, doc in enumerate(dense_results, start=1):
        doc_id = doc["id"]
        doc_lookup[doc_id] = doc
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    for rank, doc in enumerate(sparse_results, start=1):
        doc_id = doc["id"]
        if doc_id not in doc_lookup:
            doc_lookup[doc_id] = doc
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_n]
    fused = []
    for doc_id in sorted_ids:
        item = dict(doc_lookup[doc_id])
        item["rrf_score"] = rrf_scores[doc_id]
        fused.append(item)

    return fused


def rerank_flashrank(query: str, candidates: list[dict], top_k: int = 4) -> list[dict]:
    if not candidates:
        return []
    try:
        ranker = _get_ranker()
        passages = [
            {
                "id": c["id"],
                "text": c["text"],
                "meta": c["metadata"]
            }
            for c in candidates
        ]
        rerank_request = RerankRequest(query=query, passages=passages)
        reranked = ranker.rerank(rerank_request)[:top_k]

        output = []
        for item in reranked:
            meta = item.get("meta", {})
            output.append({
                "id": item["id"],
                "text": item["text"],
                "metadata": meta,
                "source": meta.get("source", "dokumen"),
                "page": meta.get("page", 1),
                "score": float(item.get("score", 0.0))
            })
        return output
    except Exception as e:
        print(f"FlashRank rerank failed, fallback to candidates: {e}")
        return candidates[:top_k]


def retrieve(session_id: str, query: str, k: int = 4) -> list[dict]:
    # 1. Dense Search
    dense_results = query_dense(session_id, query, top_k=10)
    # 2. Sparse Search (BM25)
    sparse_results = query_bm25(session_id, query, top_k=10)

    if not dense_results and not sparse_results:
        return []

    # 3. Hybrid RRF Fusion
    candidates = reciprocal_rank_fusion(dense_results, sparse_results, k=60, top_n=8)

    # 4. Re-ranking via FlashRank ONNX
    final_docs = rerank_flashrank(query, candidates, top_k=k)
    return final_docs


def delete_session_index(session_id: str):
    # Clear ChromaDB collection
    try:
        client = _client()
        client.delete_collection(f"session-{session_id}")
    except Exception as e:
        print(f"ChromaDB delete collection error: {e}")

    # Clear BM25 in-memory store
    if session_id in _BM25_STORES:
        del _BM25_STORES[session_id]
