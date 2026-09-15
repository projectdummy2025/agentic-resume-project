# Panduan Stack: Lightweight Re-ranking (FlashRank & ONNX)

Dokumen ini berisi panduan teknis implementasi *Cross-Encoder Re-ranking* berbasis CPU menggunakan **FlashRank** dan runtime **ONNX** pada `airesume-project`.

---

## 1. Mengapa Re-ranking Diperlukan?

Hasil dari Hybrid Search (Dense + BM25 via RRF) adalah kandidat berbasis bi-encoder dan frekuensi kata. Namun, model Bi-Encoder tidak memproses interaksi langsung antara kata dalam pertanyaan (*query*) dan kata dalam dokumen (*passage*).

*Cross-Encoder* membaca pasangan `(query, passage)` secara simultan untuk menghitung probabilitas relevansi yang jauh lebih akurat.

---

## 2. Mengapa FlashRank (ONNX Runtime)?

- **Ringan & Cepat**: Menggunakan model terkuantisasi via ONNX Runtime.
- **Tanpa GPU & PyTorch**: Ukuran library kecil (~10MB vs PyTorch > 800MB).
- **Latency Rendah**: Reranking 5-10 dokumen selesai dalam ~20-50 milidetik pada CPU biasa.

---

## 3. Library & Dependency

- **Library**: `flashrank`

```bash
pip install flashrank
```

---

## 4. Inisialisasi & Model Selection

Pilihan model default: `ms-marco-TinyBERT-L-2-v2` (sangat ringan ~4MB) atau `ms-marco-MiniLM-L-12-v2` (~30MB).

### Inisialisasi Ranker Singleton:

```python
from flashrank import Ranker, RerankRequest

# Inisialisasi sekali saja (Singleton) agar model tidak dimuat berulang kali
_RANKER_INSTANCE = None

def get_ranker() -> Ranker:
    global _RANKER_INSTANCE
    if _RANKER_INSTANCE is None:
        # Default model: ms-marco-TinyBERT-L-2-v2
        _RANKER_INSTANCE = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="/tmp/flashrank_models")
    return _RANKER_INSTANCE
```

---

## 5. Implementasi Re-ranking

```python
def rerank_candidates(query: str, candidates: list[dict], top_k: int = 4) -> list[dict]:
    """
    candidates: list of dict {'id': str, 'text': str, 'metadata': dict}
    """
    if not candidates:
        return []
        
    ranker = get_ranker()
    
    # Format passages sesuai kontrak FlashRank
    passages = [
        {
            "id": c["id"],
            "text": c["text"],
            "meta": c["metadata"]
        }
        for c in candidates
    ]
    
    rerank_request = RerankRequest(query=query, passages=passages)
    reranked_results = ranker.rerank(rerank_request)
    
    # Ambil top-k dokumen dengan skor tertinggi
    top_results = reranked_results[:top_k]
    
    output = []
    for item in top_results:
        output.append({
            "id": item["id"],
            "text": item["text"],
            "metadata": item.get("meta", {}),
            "score": float(item.get("score", 0.0))
        })
        
    return output
```

---

## 6. Prompt Assembly & Citation Grounding

Setelah mendapatkan top-k chunk yang telah di-rerank, rakit konteks teks dengan label sumber dan halaman agar LLM dapat menyertakan sitasi.

```python
def format_context_with_citations(reranked_chunks: list[dict]) -> str:
    if not reranked_chunks:
        return "Tidak ada dokumen relevan yang ditemukan."
        
    formatted_parts = []
    for i, chunk in enumerate(reranked_chunks, start=1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "dokumen.pdf")
        page = meta.get("page", 1)
        text = chunk.get("text", "").strip()
        
        part = f"[{i}] Sumber: {source} (Halaman {page})\n{text}"
        formatted_parts.append(part)
        
    return "\n\n---\n\n".join(formatted_parts)
```

---

## 7. Matriks Efisiensi FlashRank

| Model | Ukuran Model | Latency CPU (10 Docs) | Akurasi Re-ranking |
| :--- | :--- | :--- | :--- |
| **ms-marco-TinyBERT-L-2-v2** | ~4 MB | ~15-25 ms | Baik (Optimal untuk Resume) |
| **ms-marco-MiniLM-L-12-v2** | ~34 MB | ~50-80 ms | Sangat Tinggi |
