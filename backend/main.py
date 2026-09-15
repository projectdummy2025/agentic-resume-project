import os
import json
import asyncio
import uuid
import re
import traceback
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from openai import OpenAI
import pypdf.errors

import rag
import sessions
from prompts import get_system_prompt, build_chat_system_prompt
from schemas import QueryRequest, SessionCreate

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI()
sessions.init_db()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(asyncio.to_thread(rag.warmup))

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


def get_openai_client():
    api_key = OPENAI_COMPATIBLE_API_KEY.strip() if OPENAI_COMPATIBLE_API_KEY else "dummy_api_key"
    return OpenAI(
        api_key=api_key,
        base_url=OPENAI_COMPATIBLE_BASE_URL,
    )


def should_condense_query(query: str, history_len: int) -> bool:
    """Only condense query if history is multi-turn AND query is short or ambiguous."""
    if history_len < 2:
        return False
    query_lower = query.lower()
    # Check for pronoun / follow-up reference words in Indonesian / English
    ambiguous_tokens = ["itu", "ini", "tersebut", "dia", "nya", "mereka", "ia", "it", "they", "them", "this", "that"]
    words = re.findall(r"\b\w+\b", query_lower)
    if len(words) < 7 or any(w in ambiguous_tokens for w in words):
        return True
    return False


def condense_query(query: str, history_text: str) -> str:
    if not history_text:
        return query
    try:
        client = get_openai_client()
        res = client.chat.completions.create(
            model=OPENAI_COMPATIBLE_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tugasmu: Gabungkan riwayat percakapan dan pertanyaan terbaru pengguna "
                        "menjadi 1 kalimat pertanyaan pencarian yang mandiri, eksplisit, dan spesifik. "
                        "Output HANYA kalimat pertanyaan tanpa awalan/penjelasan."
                    ),
                },
                {"role": "user", "content": f"Riwayat Percakapan:\n{history_text}\n\nPertanyaan Terbaru: {query}"},
            ],
            temperature=0.2,
            max_tokens=80,
        )
        condensed = res.choices[0].message.content.strip()
        return condensed or query
    except Exception as e:
        print(f"Query condensation fallback: {e}")
        return query


def enrichQuery(userQuery: str, sessionId: str) -> str:
    # Always append document sources to retrieval query to anchor RAG search to document context
    documentSources = rag.get_document_sources(sessionId)
    if documentSources:
        sourceString = " ".join(documentSources)
        return f"{userQuery} {sourceString}"
    return userQuery




@app.post("/ingest")
async def ingest(file: UploadFile = File(...), session_id: str = Form(...)):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung")
        import pypdf
        from io import BytesIO

        content = await file.read()
        try:
            reader = pypdf.PdfReader(BytesIO(content))
            pages = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"page": idx + 1, "text": text})
        except (pypdf.errors.PdfReadError, pypdf.errors.FileNotDecryptedError) as pdf_err:
            raise HTTPException(status_code=400, detail=f"Gagal membaca PDF: {str(pdf_err)}")

        if not pages:
            raise HTTPException(status_code=400, detail="Dokumen PDF kosong atau tidak berisi teks yang dapat dibaca.")

        n = await asyncio.to_thread(rag.ingest_pdf_pages, session_id, file.filename, pages)

        session = sessions.get_session(session_id)
        if not session:
            sessions.create_session(session_id, file.filename)
        elif session.get("title") in ("Untitled", "Sesi Baru"):
            sessions.rename_session(session_id, file.filename)

        sources = rag.get_document_sources(session_id)
        return {"filename": file.filename, "chunks": n, "documents": sources}
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
    docs = rag.get_document_sources(session_id)
    return {
        "session": session,
        "messages": sessions.get_messages(session_id),
        "documents": docs,
    }


@app.get("/session/{session_id}/documents")
async def get_session_documents(session_id: str):
    session = sessions.get_session(session_id)
    if not session:
        return {"documents": []}
    return {"documents": rag.get_document_sources(session_id)}


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


def call_llm(system_instruction: str, user_message: str):
    client = get_openai_client()
    return client.chat.completions.create(
        model=OPENAI_COMPATIBLE_MODEL,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
    )


@app.post("/chat/stream")
async def chat_stream(req: QueryRequest):
    try:
        session = sessions.get_session(req.session_id)
        if not session:
            title = req.text[:40].strip() + ("..." if len(req.text) > 40 else "")
            sessions.create_session(req.session_id, title or "Sesi Baru")
            session = sessions.get_session(req.session_id)
        elif session.get("title") in ("Untitled", "Sesi Baru"):
            title = req.text[:40].strip() + ("..." if len(req.text) > 40 else "")
            sessions.rename_session(req.session_id, title)

        history = sessions.get_messages(req.session_id)
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        sessions.add_message(req.session_id, "user", req.text)

        has_docs = rag.has_documents(req.session_id)
        doc_refs = []

        if has_docs:
            if should_condense_query(req.text, len(history)):
                condensed = await asyncio.to_thread(condense_query, req.text, history_text)
            else:
                condensed = req.text

            searchQuery = enrichQuery(condensed, req.session_id)
            docs = await asyncio.to_thread(rag.retrieve, req.session_id, searchQuery)

            context_parts = []
            for d in docs:
                src = d.get("source", "dokumen")
                pg = d.get("page", 1)
                txt = d.get("text", "").strip()
                context_parts.append(f"[Sumber: {src} | Halaman: {pg}]\n{txt}")

            context = "\n\n---\n\n".join(context_parts)
            system_prompt = get_system_prompt(req.prompt_style, context, history_text)
            if docs:
                doc_refs = list(dict.fromkeys(f"{d['source']} (hal. {d.get('page', 1)})" for d in docs))
        else:
            system_prompt = build_chat_system_prompt(req.prompt_style, history_text)

        async def sse_generator():
            full_text = ""
            persisted = False
            try:
                client = get_openai_client()
                response = client.chat.completions.create(
                    model=OPENAI_COMPATIBLE_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": req.text},
                    ],
                    temperature=0.7,
                    stream=True,
                )

                if doc_refs:
                    yield f"data: {json.dumps({'documents': doc_refs})}\n\n"

                for chunk in response:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        full_text += delta
                        yield f"data: {json.dumps({'chunk': delta})}\n\n"
                    await asyncio.sleep(0)

                sessions.add_message(req.session_id, "assistant", full_text)
                persisted = True
                yield f"data: {json.dumps({'done': True, 'full_text': full_text})}\n\n"
            except Exception as stream_err:
                print(f"Error in SSE stream: {stream_err}")
                yield f"data: {json.dumps({'error': str(stream_err), 'done': True})}\n\n"
            finally:
                if not persisted and full_text.strip():
                    try:
                        sessions.add_message(req.session_id, "assistant", full_text)
                    except Exception as persist_err:
                        print(f"Failed to persist partial assistant response: {persist_err}")

        return StreamingResponse(sse_generator(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /chat/stream: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: QueryRequest):
    try:
        session = sessions.get_session(req.session_id)
        if not session:
            title = req.text[:40].strip() + ("..." if len(req.text) > 40 else "")
            sessions.create_session(req.session_id, title or "Sesi Baru")
            session = sessions.get_session(req.session_id)
        elif session.get("title") in ("Untitled", "Sesi Baru"):
            title = req.text[:40].strip() + ("..." if len(req.text) > 40 else "")
            sessions.rename_session(req.session_id, title)

        history = sessions.get_messages(req.session_id)
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        has_docs = rag.has_documents(req.session_id)

        sessions.add_message(req.session_id, "user", req.text)

        if has_docs:
            if should_condense_query(req.text, len(history)):
                condensed = await asyncio.to_thread(condense_query, req.text, history_text)
            else:
                condensed = req.text

            searchQuery = enrichQuery(condensed, req.session_id)
            docs = await asyncio.to_thread(rag.retrieve, req.session_id, searchQuery)
            context_parts = []
            for d in docs:
                src = d.get("source", "dokumen")
                pg = d.get("page", 1)
                txt = d.get("text", "").strip()
                context_parts.append(f"[Sumber: {src} | Halaman: {pg}]\n{txt}")

            context = "\n\n---\n\n".join(context_parts)
            system_instruction = get_system_prompt(req.prompt_style, context, history_text)
            response = call_llm(system_instruction, req.text)
            content = response.choices[0].message.content or ""

            result = {"jawaban": content}
            if docs:
                result["dokumen"] = list(dict.fromkeys(f"{d['source']} (hal. {d.get('page', 1)})" for d in docs))
        else:
            system_instruction = build_chat_system_prompt(req.prompt_style, history_text)
            response = call_llm(system_instruction, req.text)
            content = response.choices[0].message.content or ""
            result = {"jawaban": content}

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
    return await chat(req)
