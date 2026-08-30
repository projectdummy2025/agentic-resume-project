import os
import json
import asyncio
import uuid
import traceback
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from google import genai
from google.genai import types

import rag
import sessions
from prompts import get_system_prompt, build_chat_system_prompt
from schemas import QueryRequest, SessionCreate

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()
sessions.init_db()

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
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        n = await asyncio.to_thread(rag.ingest, session_id, file.filename, text)
        
        session = sessions.get_session(session_id)
        if not session:
            sessions.create_session(session_id, file.filename)
        elif session.get("title") == "Untitled":
            sessions.rename_session(session_id, file.filename)
            
        return {"filename": file.filename, "chunks": n}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        
        client = genai.Client()
        model_name = os.getenv("MODEL_NAME", "gemma-4-26b-a4b-it")
        sessions.add_message(req.session_id, "user", req.text)
        
        response = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
                contents=req.text,
            )
        )
        result = json.loads(response.text)
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
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        docs = await asyncio.to_thread(rag.retrieve, req.session_id, req.text)
        context = "\n\n".join(f"[{d['source']}]\n{d['text']}" for d in docs)
        system_instruction = get_system_prompt(req.prompt_style, context)
        
        client = genai.Client()
        model_name = os.getenv("MODEL_NAME", "gemma-4-26b-a4b-it")
        sessions.add_message(req.session_id, "user", req.text)
        
        response = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
                contents=req.text,
            )
        )
        result = json.loads(response.text)
        if docs:
            result["dokumen"] = sorted({d["source"] for d in docs})
        sessions.add_message(req.session_id, "assistant", result.get("jawaban", ""))
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /analyze: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
