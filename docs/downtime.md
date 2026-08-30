# Roadmap Pemanfaatan LLM.

#### **Fase 1: Fondasi & Prompt Engineering Lanjutan**
- **Fokus**: Memahami batasan LLM dan cara mengendalikannya.
- **Konsep**: Zero-shot, Few-shot, Chain-of-Thought (CoT), dan *Structured Output* (JSON).
- **Aksi Nyata**: Buat tool sederhana (Python) yang mengambil input teks petani (misal: "Daun kuning bercak coklat"), lalu output-nya **wajib** format JSON berisi: `penyakit`, `tingkat_keparahan`, `rekomendasi`. Gunakan API gratis/murah (OpenRouter, Groq, atau Ollama lokal).

#### **Fase 2: RAG (Retrieval-Augmented Generation)**
- **Fokus**: Menghubungkan LLM dengan data eksternal (kunci untuk aplikasi perusahaan).
- **Konsep**: Embeddings, Vector Database, Chunking strategies, *Retrieval evaluation*.
- **Aksi Nyata**: Bangun "Asisten Dokumen Pertanian". 
  - Ingest PDF pedoman pemupukan atau regulasi pertanian.
  - Gunakan **ChromaDB** atau **FAISS** (ringan, bisa jalan di server mini).
  - Gunakan embedding model ringan (misal: `all-MiniLM-L6-v2`).
  - Buat antarmuka web sederhana (Streamlit atau Next.js) untuk tanya-jawab.

#### **Fase 3: Agentic Workflow & Function Calling**
- **Fokus**: Membuat LLM bukan hanya "berbicara", tapi "bertindak".
- **Konsep**: Tool use, Function calling, ReAct (Reasoning and Acting) pattern.
- **Aksi Nyata**: Bangun agen yang bisa: 
  1. Menerima query: "Cek harga beras hari ini dan bandingkan dengan rata-rata bulan lalu".
  2. Memanggil API publik (misal: API harga pangan atau mock API).
  3. Mengolah data tersebut dan memberikan ringkasan analitis.
  - Gunakan framework **LangChain** atau **LlamaIndex** (pilih satu, jangan keduanya sekaligus agar tidak distraksi).

#### **Fase 4: Deployment & Optimasi Biaya**
- **Fokus**: Membuat proyek layak produksi dan efisien.
- **Konsep**: Caching (menghemat token), Rate limiting, Evaluasi sederhana (misal: mengecek apakah output JSON valid).
- **Aksi Nyata**: 
  - Deploy aplikasi RAG/Agent-mu. Karena budget terbatas, gunakan **Cloudflare Workers AI** (gratis/cheap) atau jalankan model kecil (Llama 3 8B quantized) di server mini rumahmu, lalu ekspos menggunakan **cloudflared** (yang sudah kamu kuasai) sebagai backend API.

---