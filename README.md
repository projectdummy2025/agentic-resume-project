# RAG Asisten Pribadi (Tahap Belajar)

Proyek ini bertujuan membuat Asisten Pribadi berbasis Retrieval-Augmented Generation (RAG) menggunakan data lokal (dokumen pribadi) tanpa menyerahkan kepemilikan data ke cloud, meskipun model bahasanya menggunakan API (Gemini/Gemma).

## Rencana Bertahap (Roadmap)

1. **[SELESAI] Konsep Dasar RAG (In-Memory)**: Skrip Python sederhana untuk memahami Chunking -> Embedding -> Retrieval -> Generation.
2. **[SEGERA] Persistent Local Vector Store**: Menyimpan vektor (embeddings) secara lokal ke disk menggunakan ChromaDB, sehingga dokumen tidak perlu di-embed berulang kali.
3. **Document Loader & Splitter**: Menangani dokumen asli (TXT, MD, PDF) dan memecahnya menjadi chunk secara cerdas (misalnya dengan LangChain atau LlamaIndex minimalis).
4. **Local LLM Option (Opsional)**: Menyiapkan opsi integrasi dengan Ollama untuk menjalankan LLM secara penuh di mesin lokal, 100% offline.
5. **Chat Interface**: Membuat antarmuka interaktif (CLI/Gradio/Streamlit) agar asisten bisa diajak berdiskusi terkait dokumen pribadi.
