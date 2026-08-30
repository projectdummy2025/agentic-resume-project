import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

import rag

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client()

class QueryRequest(BaseModel):
    text: str
    prompt_style: str = "zero-shot"

def get_system_prompt(style: str, context: str = "") -> str:
    base = "Kamu adalah asisten cerdas yang serbaguna. Output WAJIB dalam format JSON valid dengan key: 'jawaban', 'topik', 'sumber' (jika relevan). Format isi 'jawaban' menggunakan Markdown yang rapi (gunakan baris baru '\\n\\n' antar paragraf, dan '\\n- ' atau '\\n1. ' untuk poin-poin agar tidak menumpuk dalam satu paragraf)."
    if context:
        base += f"\n\nGunakan KONTEKS berikut dari dokumen pengguna untuk menjawab, dan sebutkan sumbernya di key 'sumber':\n---\n{context}\n---"
    if style == "few-shot":
        return base + "\nContoh: Input: 'Apa itu machine learning?', Output: {\"jawaban\": \"Machine Learning adalah cabang AI.\\n\\nTahapan utama:\\n1. Pengumpulan Data\\n2. Pelatihan Model\", \"topik\": \"AI/ML\", \"sumber\": \"Definisi umum\"}"
    if style == "cot":
        return base + "\nPikirkan langkah-demi-langkah sebelum menjawab, letakkan pemikiranmu di key 'reasoning' dalam JSON."
    return base

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung")
        import pypdf
        from io import BytesIO
        reader = pypdf.PdfReader(BytesIO(await file.read()))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        n = await asyncio.to_thread(rag.ingest, file.filename, text)
        return {"filename": file.filename, "chunks": n}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze(req: QueryRequest):
    try:
        model_name = os.getenv("MODEL_NAME", "gemma-4-26b-a4b-it")
        docs = await asyncio.to_thread(rag.retrieve, req.text)
        context = "\n\n".join(f"[{d['source']}]\n{d['text']}" for d in docs)
        system_instruction = await asyncio.to_thread(get_system_prompt, req.prompt_style, context)

        def _call_api():
            return client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.7
                ),
                contents=req.text
            )

        response = await asyncio.to_thread(_call_api)
        result = json.loads(response.text)
        if docs:
            result["dokumen"] = sorted({d["source"] for d in docs})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
