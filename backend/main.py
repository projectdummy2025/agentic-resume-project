import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

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

def get_system_prompt(style: str) -> str:
    base = "Kamu adalah asisten cerdas yang serbaguna. Output WAJIB dalam format JSON valid dengan key: 'jawaban', 'topik', 'sumber' (jika relevan). Format isi 'jawaban' menggunakan Markdown yang rapi (gunakan baris baru '\\n\\n' antar paragraf, dan '\\n- ' atau '\\n1. ' untuk poin-poin agar tidak menumpuk dalam satu paragraf)."
    if style == "few-shot":
        return base + "\nContoh: Input: 'Apa itu machine learning?', Output: {\"jawaban\": \"Machine Learning adalah cabang AI.\\n\\nTahapan utama:\\n1. Pengumpulan Data\\n2. Pelatihan Model\", \"topik\": \"AI/ML\", \"sumber\": \"Definisi umum\"}"
    if style == "cot":
        return base + "\nPikirkan langkah-demi-langkah sebelum menjawab, letakkan pemikiranmu di key 'reasoning' dalam JSON."
    return base

@app.post("/analyze")
async def analyze(req: QueryRequest):
    try:
        model_name = os.getenv("MODEL_NAME", "gemma-4-26b-a4b-it")
        system_instruction = get_system_prompt(req.prompt_style)
        
        # Jalankan di thread pool agar tidak mengunci event loop
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
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
