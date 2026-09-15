def get_system_prompt(style: str, context: str = "") -> str:
    base = (
        "Kamu adalah asisten cerdas yang serbaguna. Output WAJIB dalam format JSON valid dengan key: 'jawaban', 'topik', 'sumber' (jika relevan). "
        "Format isi 'jawaban' menggunakan Markdown yang rapi (gunakan baris baru '\\n\\n' antar paragraf, dan '\\n- ' atau '\\n1. ' untuk poin-poin agar tidak menumpuk dalam satu paragraf)."
    )
    if context:
        base += (
            "\n\nGunakan KONTEKS berikut dari dokumen pengguna untuk menjawab. "
            "Sebutkan rujukan sumber dan nomor halaman secara spesifik pada isi 'jawaban' maupun di key 'sumber':\n---\n"
            f"{context}\n---"
        )
    if style == "few-shot":
        return base + "\nContoh: Input: 'Apa itu machine learning?', Output: {\"jawaban\": \"Machine Learning adalah cabang AI.\\n\\nTahapan utama:\\n1. Pengumpulan Data\\n2. Pelatihan Model\", \"topik\": \"AI/ML\", \"sumber\": \"Definisi umum\"}"
    if style == "cot":
        return base + "\nPikirkan langkah-demi-langkah sebelum menjawab, letakkan pemikiranmu di key 'reasoning' dalam JSON."
    return base


def build_chat_system_prompt(style: str, history_text: str = "") -> str:
    base = (
        "Kamu adalah asisten cerdas yang serbaguna. Output WAJIB dalam format JSON valid dengan key: 'jawaban', 'topik'. "
        "Format isi 'jawaban' menggunakan Markdown yang rapi."
    )
    if history_text:
        base += f"\n\nPercakapan sebelumnya:\n---\n{history_text}\n---"
    if style == "few-shot":
        return base + "\nContoh: Input: 'Apa itu machine learning?', Output: {\"jawaban\": \"Machine Learning adalah cabang AI.\", \"topik\": \"AI/ML\"}"
    if style == "cot":
        return base + "\nPikirkan langkah-demi-langkah sebelum menjawab, letakkan pemikiranmu di key 'reasoning' dalam JSON."
    return base
