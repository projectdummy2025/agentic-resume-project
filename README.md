# Tutorial Menjalankan Aplikasi

## 1. Konfigurasi Environment (Root)
1. Salin `.env.example` menjadi `.env` di folder root proyek.
2. Buka `.env` dan sesuaikan variabel lingkungan.

## 2. Menjalankan Backend dengan Virtual Environment (venv)
Gunakan Virtual Environment (`.venv`) untuk mengisolasi dependensi Python tanpa menginstal paket secara global.

1. Buat dan aktifkan Virtual Environment dari folder root:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install seluruh dependensi backend (termasuk SQLAlchemy ORM):
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Jalankan server FastAPI backend:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   *Backend berjalan di `http://localhost:8000`.*

## 3. Menjalankan Backend dengan Docker (Opsional)
Backend juga dapat dijalankan dalam container Docker:
1. Pastikan Docker & Docker Compose terinstal.
2. Jalankan perintah dari folder root proyek:
   ```bash
   docker compose up --build
   ```

## 4. Menjalankan Frontend (Astro)
1. Buka terminal baru dan masuk ke folder `frontend`:
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
   *Frontend berjalan di `http://localhost:3000`.*

## 5. Penggunaan
Buka browser dan akses `http://localhost:3000`. Unggah PDF lewat tombol "Unggah" di header atau mulailah percakapan langsung untuk memanfaatkan fitur **Hybrid Context Fusion & Long-Term Memory (MAG)**.
