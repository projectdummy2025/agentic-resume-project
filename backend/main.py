import os
import json
import asyncio
import uuid
import traceback
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI

import rag
import sessions
from prompts import get_system_prompt, build_chat_system_prompt
from schemas import QueryRequest, SessionCreate

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()
sessions.init_db()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compat")
OPENAI_COMPATIBLE_API_KEY = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
OPENAI_COMPATIBLE_BASE_URL = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:8000/v1")
OPENAI_COMPATIBLE_MODEL = os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-4o-mini")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ingest")
async def ingest(file: UploadFile = File(...), session_id: str = Form(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung")
        import pypdf
        from io import BytesIO
        reader = pypdf.PdfReader(BytesIO(await file.read()))
        pages = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"page": idx + 1, "text": text})
        
        n = await asyncio.to_thread(rag.ingest_pdf_pages, session_id, file.filename, pages)
        
        session = sessions.get_session(session_id)
        if not session:
            sessions.create_session(session_id, file.filename)
        elif session.get("title") in ("Untitled", "Sesi Baru"):
            sessions.rename_session(session_id, file.filename)
            
        return {"filename": file.filename, "chunks": n}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def call_llm(system_instruction: str, user_message: str):
    client = OpenAI(
        api_key=OPENAI_COMPATIBLE_API_KEY,
        base_url=OPENAI_COMPATIBLE_BASE_URL,
    )
    return client.chat.completions.create(
        model=OPENAI_COMPATIBLE_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
    )


@app.post("/session")
async def create_session(req: SessionCreate):
    session_id = req.session_id or str(uuid.uuid4())
    sessions.create_session(session_id, req.title)
    return {"session_id": session_id}


@app.get("/sessions")
async def list_sessions():
    return sessions.list_sessions()


@app.get("/session/{session_id}/messages")
async def get_messages(session_id: str):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session, "messages": sessions.get_messages(session_id)}


@app.post("/session/{session_id}/rename")
async def rename_session(session_id: str, title: str):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions.rename_session(session_id, title)
    return {"ok": True}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions.delete_session(session_id)
    rag.delete_session_index(session_id)
    return {"ok": True}


@app.post("/chat")
async def chat(req: QueryRequest):
    try:
        session = sessions.get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Auto-rename session if it has default title
        if session.get("title") in ("Untitled", "Sesi Baru"):
            title = req.text[:40].strip() + ("..." if len(req.text) > 40 else "")
            sessions.rename_session(req.session_id, title)

        history = sessions.get_messages(req.session_id)
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        system_instruction = build_chat_system_prompt(req.prompt_style, history_text)
        
        sessions.add_message(req.session_id, "user", req.text)

        response = call_llm(system_instruction, req.text)

        content = response.choices[0].message.content
        result = json.loads(content)

        sessions.add_message(req.session_id, "assistant", result.get("jawaban", ""))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /chat: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze(req: QueryRequest):
    try:
        session = sessions.get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Auto-rename session if it has default title
        if session.get("title") in ("Untitled", "Sesi Baru"):
            title = req.text[:40].strip() + ("..." if len(req.text) > 40 else "")
            sessions.rename_session(req.session_id, title)

        history = sessions.get_messages(req.session_id)
        docs = await asyncio.to_thread(rag.retrieve, req.session_id, req.text)
        
        context_parts = []
        for d in docs:
            src = d.get("source", "dokumen")
            pg = d.get("page", 1)
            txt = d.get("text", "").strip()
            context_parts.append(f"[Sumber: {src} | Halaman: {pg}]\n{txt}")
        context = "\n\n---\n\n".join(context_parts)
        
        system_instruction = get_system_prompt(req.prompt_style, context)
        
        sessions.add_message(req.session_id, "user", req.text)

        response = call_llm(system_instruction, req.text)

        content = response.choices[0].message.content
        result = json.loads(content)

        if docs:
            result["dokumen"] = list(dict.fromkeys(f"{d['source']} (hal. {d.get('page', 1)})" for d in docs))
        sessions.add_message(req.session_id, "assistant", result.get("jawaban", ""))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /analyze: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
