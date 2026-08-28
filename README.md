# Tutorial Menjalankan Aplikasi

## 1. Konfigurasi Environment (Root)
1. Salin `.env.example` menjadi `.env` di folder root proyek.
2. Buka `.env` dan isi `GEMINI_API_KEY` dengan kunci API Gemini Anda.

## 2. Menjalankan Backend (Python)
1. Buka terminal baru dan masuk ke folder `backend`:
   ```bash
   cd backend
   ```
2. Buat virtual environment menggunakan `python` dan aktifkan:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # (Di Windows: .venv\Scripts\activate)
   ```
3. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```
4. Jalankan server FastAPI:
   ```bash
   uvicorn main:app --reload
   ```
   *Server backend akan berjalan di `http://localhost:8000`.*

## 3. Menjalankan Frontend (Node.js)
1. Buka terminal baru (biarkan terminal backend tetap berjalan) dan masuk ke folder `frontend`:
   ```bash
   cd frontend
   ```
2. Install dependensi NPM:
   ```bash
   npm install
   ```
3. Jalankan server Express:
   ```bash
   npm run dev
   ```
   *Server frontend akan berjalan di `http://localhost:3000`.*

## 4. Penggunaan
Buka browser dan akses `http://localhost:3000`. Aplikasi siap digunakan.
