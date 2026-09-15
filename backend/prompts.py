def get_system_prompt(style: str, context: str = "", history_text: str = "") -> str:
    base = (
        "Kamu adalah asisten cerdas yang serbaguna, analitis, dan komunikatif. "
        "Jawab pertanyaan secara langsung, jelas, dan informatif menggunakan bahasa Indonesia yang mengalir secara alami dan terstruktur. "
        "Gunakan format Markdown yang rapi (paragraf terpisah, cetak tebal untuk poin penting, dan daftar poin jika diperlukan). "
        "JANGAN gunakan pembungkus JSON atau sintaks kurung kurawal."
    )
    if history_text:
        base += f"\n\nRiwayat Percakapan Sebelumnya:\n---\n{history_text}\n---"
    if context:
        base += (
            "\n\nKONTEKS DOKUMEN PENGGUNA:\n---\n"
            f"{context}\n---\n\n"
            "PETUNJUK PENGGUNAAN KONTEKS:\n"
            "1. Sintesiskan informasi dari KONTEKS DOKUMEN di atas menjadi penjelasan yang utuh, logis, dan masuk akal.\n"
            "2. Jangan hanya menyajikan potongan kalimat mentah; susun menjadi kalimat dan paragraf penjelasan yang informatif.\n"
            "3. Cantumkan rujukan sumber dan nomor halaman secara natural di akhir poin/kalimat jika relevan, contoh: [Sumber: nama_file.pdf | Halaman: N].\n"
            "4. Jika informasi spesifik tidak ditemukan di dokumen, sampaikan secara jujur dan berikan ringkasan topik umum dari dokumen yang ada."
        )
    if style == "few-shot":
        base += (
            "\n\nContoh Jawaban:\n"
            "Berdasarkan dokumen terlampir, berikut adalah pembahasan utama yang ditemukan:\n\n"
            "1. **Penerapan Metode Pembelajaran:** Pembelajaran berbasis studi kasus diterapkan untuk meningkatkan keterlibatan siswa. [Sumber: dokumen.pdf | Halaman: 2]\n"
            "2. **Evaluasi Praktikum:** Penggunaan perangkat lunak simulasi membantu pemahaman materi mekanika. [Sumber: dokumen.pdf | Halaman: 4]"
        )
    if style == "cot":
        base += "\n\nPikirkan langkah-demi-langkah secara analitis sebelum memberikan jawaban akhir yang komprehensif."
    return base



def build_chat_system_prompt(style: str, history_text: str = "") -> str:
    base = (
        "Kamu adalah asisten cerdas yang serbaguna dan ramah. "
        "Jawab pertanyaan pengguna secara langsung menggunakan format Markdown yang rapi, jelas, dan terstruktur. "
        "JANGAN gunakan pembungkus JSON atau sintaks kurung kurawal."
    )
    if history_text:
        base += f"\n\nRiwayat Percakapan Sebelumnya:\n---\n{history_text}\n---"
    if style == "few-shot":
        base += (
            "\n\nContoh Jawaban:\n"
            "Machine Learning adalah cabang AI yang berfokus pada pengembangan algoritma untuk belajar dari data."
        )
    if style == "cot":
        base += "\n\nPikirkan langkah-demi-langkah secara analitis sebelum memberikan jawaban akhir."
    return base
