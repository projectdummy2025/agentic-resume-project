def get_system_prompt(style: str, context: str = "") -> str:
    base = (
        "Kamu adalah asisten cerdas yang serbaguna dan komunikatif. "
        "Jawab pertanyaan secara langsung menggunakan format Markdown yang rapi, jelas, dan terstruktur "
        "(gunakan paragraf terpisah, cetak tebal untuk poin penting, serta daftar poin '- ' atau '1. '). "
        "JANGAN gunakan pembungkus JSON atau sintaks kurung kurawal."
    )
    if context:
        base += (
            "\n\nKONTEKS DOKUMEN PENGGUNA:\n---\n"
            f"{context}\n---\n\n"
            "PETUNJUK PENGGUNAAN KONTEKS:\n"
            "1. Jawab pertanyaan pengguna berdasarkan KONTEKS DOKUMEN di atas.\n"
            "2. Cantumkan rujukan sumber dan nomor halaman secara eksplisit jika relevan, contoh: [Sumber: nama_file.pdf | Halaman: N].\n"
            "3. Jika informasi tidak terdapat dalam dokumen, jawab secara umum dengan jujur bahwa informasi tersebut tidak ada pada dokumen terlampir."
        )
    if style == "few-shot":
        base += (
            "\n\nContoh Jawaban:\n"
            "Machine Learning adalah cabang dari kecerdasan buatan (AI) yang memungkinkan sistem belajar dari data.\n\n"
            "**Tahapan Utama:**\n"
            "1. Pengumpulan & Pra-pemrosesan Data\n"
            "2. Pelatihan & Evaluasi Model\n"
            "3. Deployment Inferensi"
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
