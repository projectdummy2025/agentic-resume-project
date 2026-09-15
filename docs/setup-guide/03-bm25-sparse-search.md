# Panduan Stack: Sparse Keyword Search (BM25)

Dokumen ini berisi panduan teknis konfigurasi dan pencarian berbasis kata kunci (*Exact Matching*) menggunakan algoritma **BM25** pada `airesume-project`.

---

## 1. Mengapa BM25 Diperlukan?

Embedding vektor (*Dense Search*) sering kali gagal menangkap kata kunci eksplisit seperti:
- Nama perusahaan (misal: "GoTo", "BCA", "Shopee").
- Nama alat/teknologi spesifik (misal: "PyTorch", "Kubernetes", "PostgreSQL").
- Angka/IPK/Tanggal (misal: "3.85", "2024").

Algoritma BM25 (*Best Matching 25*) menghitung *Term Frequency* (TF) dan *Inverse Document Frequency* (IDF) untuk menemukan chunk dengan kata kunci persis.

---

## 2. Library & Dependency

- **Library**: `rank_bm25` (`BM25Okapi`)

```bash
pip install rank-bm25
```

---

## 3. Strategi Tokenisasi Teks Resume

Tokenisasi yang baik memengaruhi akurasi BM25. Untuk resume, huruf kecil (*case-insensitive*) dan pembersihan tanda baca wajib dilakukan.

```python
import re

def tokenize(text: str) -> list[str]:
    # Ubah ke lowercase & ambil token alfanumerik (kata & angka)
    text = text.lower()
    tokens = re.findall(r"\b\w+\b", text)
    return tokens
```

---

## 4. Pengelolaan BM25 Index In-Memory Per Sesi

Karena BM25 tidak memerlukan penyimpanan basis data permanen untuk file resume skala kecil, indeks disimpan di RAM per `session_id`.

### Implementasi Store In-Memory:

```python
from rank_bm25 import BM25Okapi

# Dictionary global penampung indeks BM25 per sesi: { session_id: {"bm25": BM25Okapi, "chunks": list[dict]} }
_BM25_STORES: dict[str, dict] = {}

def build_bm25_index(session_id: str, chunks: list[dict]):
    """
    chunks: list of dict {'id': str, 'text': str, 'metadata': dict}
    """
    corpus_tokens = [tokenize(c["text"]) for c in chunks]
    bm25_index = BM25Okapi(corpus_tokens)
    
    _BM25_STORES[session_id] = {
        "bm25": bm25_index,
        "chunks": chunks
    }

def query_bm25(session_id: str, query_text: str, top_k: int = 10) -> list[dict]:
    store = _BM25_STORES.get(session_id)
    if not store or not store["chunks"]:
        return []
        
    bm25_index: BM25Okapi = store["bm25"]
    chunks: list[dict] = store["chunks"]
    
    query_tokens = tokenize(query_text)
    if not query_tokens:
        return []
        
    # Hitung skor BM25 untuk semua dokumen
    scores = bm25_index.get_scores(query_tokens)
    
    # Ambil index dengan skor tertinggi
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    output = []
    for idx in top_indices:
        if scores[idx] > 0: # Hanya ambil yang memiliki relevansi > 0
            chunk = chunks[idx]
            output.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "bm25_score": float(scores[idx])
            })
            
    return output
```

---

## 5. Cleaning Index Saat Sesi Selesai

```python
def clear_bm25_index(session_id: str):
    if session_id in _BM25_STORES:
        del _BM25_STORES[session_id]
```

---

## 6. Ringkasan Kinerja BM25

- **Kecepatan**: < 1 milidetik untuk dokumen resume (< 100 chunk).
- **Penggunaan Memori**: Sangat hemat RAM (< 500 KB per sesi).
- **Reliabilitas**: Sangat tinggi untuk pertanyaan kata kunci spesifik.
