import os
import numpy as np
from google import genai
from google.genai import types

# Memeriksa API key
if "GEMINI_API_KEY" not in os.environ:
    print("Error: Set environment variable GEMINI_API_KEY terlebih dahulu")
    print("Contoh: export GEMINI_API_KEY='apikey_anda'")
    exit(1)

client = genai.Client()

# 1. Dokumen dasar & Chunking manual (Sangat Sederhana)
dokumen = [
    "Machine Learning adalah cabang dari AI yang memungkinkan komputer belajar dari data.",
    "RAG (Retrieval-Augmented Generation) menggabungkan pencarian informasi dengan pembuatan teks oleh LLM.",
    "Python adalah bahasa pemrograman yang populer untuk data science dan AI.",
    "Vector embedding mengubah teks menjadi deretan angka agar makna semantiknya dapat dihitung.",
]

print("1. Melakukan embedding dokumen...")

# 2. Embedding
def embed_teks(teks):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=teks,
    )
    return response.embeddings[0].values

# Proses seluruh dokumen menjadi vector
vektor_dokumen = [embed_teks(doc) for doc in dokumen]

# 3. Pengguna bertanya (Query)
pertanyaan = "Apa itu RAG?"
print(f"\nPertanyaan: '{pertanyaan}'")

print("2. Mencari teks yang paling relevan (Retrieval)...")
vektor_pertanyaan = embed_teks(pertanyaan)

# Menghitung kemiripan (Cosine Similarity)
def hitung_cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_a = np.linalg.norm(vec1)
    norm_b = np.linalg.norm(vec2)
    return dot_product / (norm_a * norm_b)

skor_kemiripan = [hitung_cosine_similarity(vektor_pertanyaan, v) for v in vektor_dokumen]

# Ambil index dengan skor tertinggi
index_terbaik = np.argmax(skor_kemiripan)
konteks_terpilih = dokumen[index_terbaik]

print(f"   -> Ditemukan teks paling relevan: '{konteks_terpilih}' (Skor: {skor_kemiripan[index_terbaik]:.4f})")

# 4. Generate jawaban dengan LLM
print("\n3. Meminta LLM menjawab berdasarkan konteks (Generation)...")

prompt = f"""Gunakan konteks berikut untuk menjawab pertanyaan. Jika jawabannya tidak ada di konteks, bilang tidak tahu.

Konteks: {konteks_terpilih}

Pertanyaan: {pertanyaan}
"""

response = client.models.generate_content(
    model="gemma-4-26b-a4b-it", # atau gemini-1.5-flash
    contents=prompt
)

print("\n--- JAWABAN LLM ---")
print(response.text)
