# Tutorial Menjalankan Aplikasi

## 1. Konfigurasi Environment (Root)
1. Salin `.env.example` menjadi `.env` di folder root proyek.
2. Buka `.env` dan isi `GEMINI_API_KEY` dengan kunci API Gemini Anda.

## 2. Menjalankan Backend (Docker)
Backend berjalan di container (CPU-only, Chroma ONNX + embedding lokal, LLM via Gemini API).
1. Pastikan Docker & Docker Compose terinstall.
2. Dari folder root proyek:
   ```bash
   docker compose up --build
   ```
   *Backend berjalan di `http://localhost:8000`. Vektor tersimpan persisten di `./chroma-data`.*
3. (Opsional) ingest PDF lewat endpoint:
   ```bash
   curl -F "file=@dokumen.pdf" http://localhost:8000/ingest
   ```

## 3. Menjalankan Frontend (Astro)
1. Buka terminal baru (biarkan backend tetap berjalan) dan masuk ke folder `frontend`:
   ```bash
   cd frontend
   ```
2. Install dependensi:
   ```bash
   npm install
   ```
3. Jalankan dev server (proxy `/api` → backend `:8000`):
   ```bash
   npm run dev
   ```
   *Frontend berjalan di `http://localhost:3000`. Untuk produksi: `npm run build` lalu `npm run preview`.*

## 4. Penggunaan
Buka browser dan akses `http://localhost:3000`. Unggah PDF lewat tombol "Unggah" di header untuk mengisi basis pengetahuan RAG.
