# Roadmap Pemanfaatan LLM.

#### **Fase 1: Fondasi & Prompt Engineering Lanjutan**
- **Fokus**: Memahami batasan LLM dan cara mengendalikannya.
- **Konsep**: Zero-shot, Few-shot, Chain-of-Thought (CoT), dan *Structured Output* (JSON).
- **Aksi Nyata**: Buat tool sederhana (Python) yang mengambil input teks petani (misal: "Daun kuning bercak coklat"), lalu output-nya **wajib** format JSON berisi: `penyakit`, `tingkat_keparahan`, `rekomendasi`. Gunakan API gratis/murah (OpenRouter, Groq, atau Ollama lokal).

#### **Fase 2 (Versi 2.0): Grounded RAG & Personal Memory (ChatGPT/Gemini Minimum Clone)**
- **Fokus**: Menghubungkan LLM dengan data dokumen eksternal sekaligus mengingat profil & preferensi pengguna lintas sesi.
- **Konsep**: Hybrid Search (Dense ChromaDB + Sparse BM25), FlashRank Reranking, Atomic Fact Memory Layer (MAG), dan Hybrid Context Fusion.
- **Aksi Nyata**: Bangun "Asisten Chatbot Enterprise (Gemini/ChatGPT Minimum Clone)".
  - Ingest PDF dokumen/resume secara terpadu tanpa perpindahan mode.
  - Gunakan **ChromaDB** + **BM25Okapi** + **FlashRank Cross-Encoder** untuk retrieval dokumen yang presisi.
  - Kelola memori profil pengguna (`user_memories`) menggunakan *Background Memory Lifecycle Engine* (`ADD`, `UPDATE`, `DELETE`, `NOOP`).
  - Buat antarmuka web modern berbasis Astro + SSE Real-Time Streaming + Panel Ingatan Personal.

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