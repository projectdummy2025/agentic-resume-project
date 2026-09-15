# Panduan Stack: Ekstraksi PDF & Page-Aware Semantic Chunking

Dokumen ini berisi panduan teknis ekstraksi teks dari PDF dan pemotongan dokumen (*chunking*) berbasis halaman untuk `airesume-project`.

---

## 1. Library & Dependency

- **Library Utama**: `pypdf` (`PdfReader`)
- **Tujuan**: Membaca dokumen PDF per halaman tanpa mengaburkan konteks posisi halaman, serta membagi teks menjadi chunk semantik dengan overlap.

---

## 2. Metodologi Ekstraksi Per Halaman

Ekstraksi teks tidak boleh menggabungkan seluruh isi PDF menjadi satu string mentah, karena akan menghilangkan metadata lokasi (nomor halaman). 

### Implementasi Ekstraksi:
```python
from pypdf import PdfReader
import re

def extract_pdf_by_page(file_path: str) -> list[dict]:
    reader = PdfReader(file_path)
    pages_data = []
    
    for idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        # Normalisasi spasi dan baris kosong berlebih
        cleaned_text = re.sub(r"\s+", " ", text).strip()
        if cleaned_text:
            pages_data.append({
                "page": idx + 1,
                "text": cleaned_text
            })
            
    return pages_data
```

---

## 3. Recursive Character Splitter

Chunking kaku berbasis panjang karakter tetap (`size=500, overlap=50`) memotong kata/kalimat di tengah. `RecursiveCharacterTextSplitter` memotong berdasarkan urutan pemisah (*separators*): `["\n\n", "\n", " ", ""]`.

### Parameter Ideal untuk Resume & CV:
- **Chunk Size**: `300` - `500` karakter (~60 - 100 kata).
- **Chunk Overlap**: `50` - `75` karakter (~10-15%).
- **Separators**: `["\n\n", "\n", ". ", " ", ""]`.

### Implementasi Custom Recursive Splitter:
```python
def recursive_chunk_text(text: str, chunk_size: int = 400, overlap: int = 60) -> list[str]:
    separators = ["\n\n", "\n", ". ", " ", ""]
    
    def _split(txt: str, seps: list[str]) -> list[str]:
        if len(txt) <= chunk_size or not seps:
            return [txt] if txt.strip() else []
        
        sep = seps[0]
        splits = txt.split(sep)
        result = []
        current = ""
        
        for part in splits:
            item = part if not current else sep + part
            if len(current) + len(item) <= chunk_size:
                current += item
            else:
                if current.strip():
                    result.append(current.strip())
                current = part
                
        if current.strip():
            result.append(current.strip())
            
        # Jika ada bagian yang masih terlalu besar, split lagi dengan separator berikutnya
        final_chunks = []
        for c in result:
            if len(c) > chunk_size and len(seps) > 1:
                final_chunks.extend(_split(c, seps[1:]))
            else:
                final_chunks.append(c)
                
        return final_chunks

    raw_chunks = _split(text, separators)
    
    # Tambahkan overlap antar chunk berurutan
    chunks_with_overlap = []
    for i, c in enumerate(raw_chunks):
        if i == 0:
            chunks_with_overlap.append(c)
        else:
            prev_tail = raw_chunks[i-1][-overlap:] if len(raw_chunks[i-1]) >= overlap else raw_chunks[i-1]
            chunks_with_overlap.append(f"{prev_tail} {c}")
            
    return chunks_with_overlap
```

---

## 4. Format Output Metadata

Setiap chunk yang dihasilkan harus membawa metadata lengkap:

```json
{
  "chunk_id": "resume_ahmad.pdf-p1-c0",
  "text": "Pengalaman Kerja: Software Engineer di PT ABC (2021-2023)...",
  "metadata": {
    "source": "resume_ahmad.pdf",
    "page": 1,
    "chunk_index": 0
  }
}
```

---

## 5. Penanganan Edge Cases

| Masalah | Solusi |
| :--- | :--- |
| **PDF Hasil Scan (Image Only)** | Tambahkan fallback atau abaikan halaman kosong dengan warning. |
| **Tabel / Kolom Terpisah** | Rekonstruksi spasi dengan `re.sub(r"\s+", " ", text)`. |
| **Karakter Non-ASCII / Unicode** | Gunakan encoding UTF-8 standar saat manipulasi string. |
