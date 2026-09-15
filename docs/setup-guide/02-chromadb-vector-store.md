# Panduan Stack: Dense Vector Store (ChromaDB)

Dokumen ini berisi panduan teknis konfigurasi dan penggunaan **ChromaDB** sebagai *Dense Vector Store* pada `airesume-project`.

---

## 1. Konfigurasi ChromaDB Persistent Client

ChromaDB berjalan secara *embedded* di dalam aplikasi Python tanpa memerlukan service external (seperti Docker terpisah).

### Setup Client:
```python
import os
from chromadb import PersistentClient
from chromadb.config import Settings

CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chroma")

def get_chroma_client():
    return PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
```

---

## 2. Pengelolaan Collection Per Sesi

Untuk mengisolasi dokumen antar pengguna/sesi, buat koleksi terpisah dengan penamaan berbasis `session_id`.

```python
def get_session_collection(session_id: str):
    client = get_chroma_client()
    collection_name = f"session-{session_id}"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"} # Menggunakan Cosine Distance
    )
```

---

## 3. Ingest Dokumen & Metadata

ChromaDB secara otomatis membuat vector embedding menggunakan model default (`all-MiniLM-L6-v2`) jika tidak ditentukan custom embedding function.

```python
def add_chunks_to_chroma(session_id: str, chunks: list[dict]):
    """
    chunks: list of dict {'id': str, 'text': str, 'metadata': dict}
    """
    collection = get_session_collection(session_id)
    
    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
```

---

## 4. Dense Retrieval (Semantic Search)

Pencarian vektor berdasarkan kemiripan semantik:

```python
def query_dense(session_id: str, query_text: str, top_k: int = 10) -> list[dict]:
    collection = get_session_collection(session_id)
    if collection.count() == 0:
        return []
        
    results = collection.query(
        query_texts=[query_text],
        n_results=min(top_k, collection.count())
    )
    
    output = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0] if "distances" in results else [0]*len(docs)
    
    for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
        output.append({
            "id": doc_id,
            "text": doc,
            "metadata": meta,
            "dense_score": float(dist)
        })
        
    return output
```

---

## 5. Lifecycle & Cleanup

Saat sesi dihapus atau di-reset, hapus koleksi terkait dari ChromaDB:

```python
def delete_session_collection(session_id: str):
    client = get_chroma_client()
    collection_name = f"session-{session_id}"
    try:
        client.delete_collection(name=collection_name)
    except Exception as e:
        print(f"Collection {collection_name} tidak ditemukan atau gagal dihapus: {e}")
```

---

## 6. Tips Performa ChromaDB

- **Penyimpanan**: Direktori `/data/chroma` disimpan di persistent volume.
- **Index HNSW**: Parameter default `hnsw:space: cosine` optimal untuk pencarian teks pendek/chunk resume.
- **Batching**: Jika memuat banyak chunk (>100), gunakan batching `collection.add(..., batch_size=100)`.
