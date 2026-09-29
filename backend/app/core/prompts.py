def format_user_memories(user_memories: list[dict] | None) -> str:
    if not user_memories:
        return ""
    memory_lines = []
    for idx, mem in enumerate(user_memories, start=1):
        category = mem.get("category", "profile")
        fact = mem.get("fact", "")
        memory_lines.append(f"{idx}. [{category}] {fact}")
    facts_block = "\n".join(memory_lines)
    return (
        "\n\nINGATAN PROFIL PENGGUNA (LONG-TERM MEMORY) :\n---\n"
        f"{facts_block}\n---\n"
        "Gunakan ingatan profil pengguna di atas untuk memberikan jawaban yang dipersonalisasi dan relevan dengan identitas pengguna .\n"
    )


def get_system_prompt(style: str, context: str = "", user_memories: list[dict] | None = None) -> str:
    base = (
        "Kamu adalah asisten cerdas yang serbaguna, analitis, akademis, dan profesional. "
        "Jawab pertanyaan pengguna secara langsung, jelas, berbobot, dan komprehensif menggunakan bahasa Indonesia. "
        "ATURAN FORMATTING DAN TANDA BACA WAJIB :\n"
        "1. Berikan 1 spasi SEBELUM setiap tanda titik dua (contoh : deskripsi poin) .\n"
        "2. DILARANG KERAS menggunakan tanda dash/strip (- atau —) dalam bentuk apapun. Gunakan penomoran (1., 2.) atau paragraf untuk daftar poin .\n"
        "3. Tulis jawaban dengan format Markdown yang bersih, terstruktur, dan sangat mudah disalin (copy-paste ready) .\n"
        "JANGAN gunakan pembungkus JSON atau sintaks kurung kurawal."
    )

    memory_text = format_user_memories(user_memories)
    if memory_text:
        base += memory_text

    if context:
        base += (
            "\n\nKONTEKS DOKUMEN PENGGUNA :\n---\n"
            f"{context}\n---\n\n"
            "PETUNJUK PENGGUNAAN KONTEKS :\n"
            "1. Sintesiskan informasi dari KONTEKS DOKUMEN di atas menjadi penjelasan yang utuh, logis, dan akademis .\n"
            "2. Jawab pertanyaan pengguna dengan menggunakan konteks dokumen di atas secara komprehensif dan berbobot .\n"
            "3. JANGAN menuliskan tag rujukan mentah seperti [Sumber: ...] di dalam teks jawaban, karena sumber akan ditampilkan otomatis oleh sistem .\n"
            "4. Jika informasi spesifik tidak ditemukan di dokumen, sampaikan secara jujur dan berikan penjelasan berdasar konteks yang ada ."
        )
    if style == "few-shot":
        base += (
            "\n\nContoh Jawaban :\n"
            "Berdasarkan dokumen terlampir, berikut adalah analisis utama yang ditemukan :\n\n"
            "1. Penerapan Metode Pembelajaran : Pembelajaran berbasis studi kasus diterapkan untuk meningkatkan keterlibatan siswa .\n"
            "2. Evaluasi Praktikum : Penggunaan perangkat lunak simulasi membantu pemahaman materi mekanika ."
        )
    if style == "cot":
        base += "\n\nPikirkan langkah-demi-langkah secara analitis dan akademis sebelum memberikan jawaban akhir yang komprehensif ."
    return base


def build_chat_system_prompt(style: str, user_memories: list[dict] | None = None) -> str:
    base = (
        "Kamu adalah asisten cerdas yang serbaguna, analitis, dan profesional. "
        "Jawab pertanyaan pengguna secara langsung, berbobot, dan komprehensif menggunakan format Markdown yang rapi dan terstruktur. "
        "ATURAN FORMATTING DAN TANDA BACA WAJIB :\n"
        "1. Berikan 1 spasi SEBELUM setiap tanda titik dua (contoh : deskripsi poin) .\n"
        "2. DILARANG KERAS menggunakan tanda dash/strip (- atau —) dalam bentuk apapun. Gunakan penomoran (1., 2.) atau paragraf untuk daftar poin .\n"
        "3. Tulis jawaban dengan format Markdown yang bersih, terstruktur, dan sangat mudah disalin (copy-paste ready) .\n"
        "JANGAN gunakan pembungkus JSON atau sintaks kurung kurawal."
    )

    memory_text = format_user_memories(user_memories)
    if memory_text:
        base += memory_text

    if style == "few-shot":
        base += (
            "\n\nContoh Jawaban :\n"
            "Machine Learning adalah cabang kecerdasan buatan (AI) yang berfokus pada pengembangan algoritma untuk belajar dari data ."
        )
    if style == "cot":
        base += "\n\nPikirkan langkah-demi-langkah secara analitis sebelum memberikan jawaban akhir yang berbobot ."
    return base
