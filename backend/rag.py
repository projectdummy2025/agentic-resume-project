import os
import re
from chromadb import PersistentClient
from chromadb.config import Settings

CHROMA_DIR = os.getenv("CHROMA_DIR", "/data/chroma")


def _client():
    return PersistentClient(path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))


def _collection(session_id: str):
    name = f"session-{session_id}"
    return _client().get_or_create_collection(name=name)


def _chunk(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def ingest(session_id: str, filename: str, text: str) -> int:
    chunks = _chunk(text)
    if not chunks:
        return 0
    collection = _collection(session_id)
    ids = [f"{filename}-{i}" for i in range(len(chunks))]
    metas = [{"source": filename} for _ in chunks]
    collection.add(documents=chunks, ids=ids, metadatas=metas)
    return len(chunks)


def retrieve(session_id: str, query: str, k: int = 4) -> list[dict]:
    collection = _collection(session_id)
    if collection.count() == 0:
        return []
    res = collection.query(query_texts=[query], n_results=k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    out = []
    for doc, meta in zip(docs, metas):
        out.append({"text": doc, "source": (meta or {}).get("source", "dokumen")})
    return out
