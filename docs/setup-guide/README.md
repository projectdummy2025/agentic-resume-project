# Panduan Setup Stack RAG Modular

Dokumen ini adalah repositori panduan teknis dan referensi mandiri untuk setiap komponen tech stack yang digunakan dalam arsitektur **Lean Modular RAG** pada `airesume-project`.

---

## Daftar Panduan Stack (Berdasarkan Urutan Pipeline)

1. **[01-pdf-extraction-chunking.md](01-pdf-extraction-chunking.md)**
   - Parsing PDF per halaman (`pypdf`).
   - Splitter kalimat/paragraf semantik bersarang (`RecursiveCharacterTextSplitter`).
   - Struktur metadata (`source`, `page`, `chunk_id`).

2. **[02-chromadb-vector-store.md](02-chromadb-vector-store.md)**
   - Konfigurasi `PersistentClient` & pengelolaan koleksi per sesi.
   - Vector Embedding & pencarian kemiripan kosinus.
   - Operasi CRUD & penanganan memori.

3. **[03-bm25-sparse-search.md](03-bm25-sparse-search.md)**
   - Integrasi `rank_bm25` (`BM25Okapi`).
   - Strategi tokenisasi teks resume (nama, skill, IPK, tanggal).
   - Pengelolaan indeks in-memory per `session_id`.

4. **[04-rrf-hybrid-fusion.md](04-rrf-hybrid-fusion.md)**
   - Penggabungan peringkat pencarian Hybrid (Dense + Sparse).
   - Formula RRF ($k=60$) & kalkulasi skor gabungan.
   - Pembersihan duplikat & normalisasi ranking.

5. **[05-flashrank-onnx-reranker.md](05-flashrank-onnx-reranker.md)**
   - Cross-Encoder Re-ranking tanpa GPU menggunakan `flashrank` + `onnxruntime`.
   - Konfigurasi model `ms-marco-TinyBERT-L-2-v2`.
   - Penyusunan konteks akhir & citation grounding.

---

## Ringkasan Dependency Backend

Daftar paket Python yang dibutuhkan (`backend/requirements.txt`):

```text
fastapi
uvicorn
openai
pydantic
python-dotenv
chromadb
pypdf
python-multipart
rank-bm25
flashrank
onnxruntime
```
