import os
import json
import asyncio
import uuid
import re
import traceback
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from openai import OpenAI
import pypdf.errors

import rag
import sessions
import memory
from prompts import get_system_prompt, build_chat_system_prompt
from schemas import QueryRequest, SessionCreate, MemoryCreateRequest, MemoryOut

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


def extract_user_id(request: Request) -> int:
    user_header = request.headers.get("x-user-id", "")
    clean_user = user_header.strip()
    if clean_user.isdigit():
        return int(clean_user)
    return 1



def generateSessionTitle(userText: str) -> str:
    cleanText = re.sub(r"[^\w\s]", "", userText).strip()
    words = cleanText.split()
    if not words:
        return "Sesi Baru"
    titleStr = " ".join(words[:5])
    return titleStr[:36].strip().capitalize()


def format_academic_response(text: str) -> str:
    if not text:
        return text
    cleaned = re.sub(r"[\u2013\u2014—–]", "", text)
    lines = []
    for line in cleaned.splitlines():
        if line.lstrip().startswith("- ") or line.lstrip().startswith("* "):
            line = re.sub(r"^(\s*)([-*])\s+", r"\1", line)
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"(?<!https)(?<!http)(?<!\d)(?<!\s):", " :", cleaned)
    return cleaned


def should_condense_query(query: str, history_len: int) -> bool:
    if history_len < 2:
        return False
    query_lower = query.lower()
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
        if res.choices and res.choices[0].message and res.choices[0].message.content:
            condensed = res.choices[0].message.content.strip()
            return condensed or query
        return query
    except Exception as e:
        print(f"Query condensation fallback: {e}")
        return query


def enrichQuery(userQuery: str, sessionId: str) -> str:
    summaryKeywords = ["dibahas", "isi", "ringkasan", "rangkum", "tentang", "overview", "summary", "bahan", "topik"]
    isSummaryRequest = any(keyword in userQuery.lower() for keyword in summaryKeywords) or len(userQuery.split()) < 4
    if isSummaryRequest:
        documentSources = rag.get_document_sources(sessionId)
        if documentSources:
            sourceString = " ".join(documentSources)
            return f"{userQuery} {sourceString}"
    return userQuery


@app.post("/ingest")
async def ingest(request: Request, file: UploadFile = File(...), session_id: str = Form(...)):
    try:
        user_id = extract_user_id(request)
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Hanya file PDF yang didukung")
        import pypdf
        from io import BytesIO

        content = await file.read()
        try:
            reader = pypdf.PdfReader(BytesIO(content))
            pages = []
            total_text_len = 0
            for idx, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"page": idx + 1, "text": text})
                    total_text_len += len(text)
        except (pypdf.errors.PdfReadError, pypdf.errors.FileNotDecryptedError) as pdf_err:
            raise HTTPException(status_code=400, detail=f"Gagal membaca PDF: {str(pdf_err)}")

        if not pages or total_text_len < 20:
            raise HTTPException(
                status_code=400,
                detail="PDF ditolak: Dokumen ini berupa hasil scan atau gambar tanpa teks digital yang dapat disalin. Sistem hanya memproses PDF berbasis teks digital.",
            )

        n = await asyncio.to_thread(rag.ingest_pdf_pages, session_id, file.filename, pages)

        session = sessions.get_session(session_id)
        cleanTitle = os.path.splitext(file.filename)[0].replace("_", " ").strip()
        if not session:
            sessions.create_session(session_id, cleanTitle or "Dokumen Baru", user_id)
        elif session.get("title") in ("Untitled", "Sesi Baru"):
            sessions.rename_session(session_id, cleanTitle or "Dokumen Baru")

        sources = rag.get_document_sources(session_id)
        return {"filename": file.filename, "chunks": n, "documents": sources}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session")
async def create_session(request: Request, req: SessionCreate):
    user_id = extract_user_id(request)
    session_id = req.session_id or str(uuid.uuid4())
    sessions.create_session(session_id, req.title, user_id)
    return {"session_id": session_id}


@app.get("/sessions")
async def list_sessions(request: Request):
    user_id = extract_user_id(request)
    return sessions.list_sessions(user_id)


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


@app.get("/memories")
async def get_memories(request: Request):
    user_id = extract_user_id(request)
    return memory.get_user_memories(user_id)


@app.post("/memories")
async def create_memory(request: Request, req: MemoryCreateRequest):
    user_id = extract_user_id(request)
    new_mem = memory.add_user_memory(user_id, req.category, req.fact)
    return new_mem


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    memory.delete_user_memory(memory_id)
    return {"ok": True}


@app.post("/chat/stream")
async def chat_stream(request: Request, req: QueryRequest):
    try:
        user_id = extract_user_id(request)
        history = sessions.get_messages(req.session_id)
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)

        session = sessions.get_session(req.session_id)
        isPlaceholderTitle = not session or session.get("title") in ("Untitled", "Sesi Baru", "Dokumen Baru") or session.get("title", "").endswith(".pdf") or "_" in session.get("title", "")
        newTitle = generateSessionTitle(req.text)

        if not session:
            sessions.create_session(req.session_id, newTitle, user_id)
            session = sessions.get_session(req.session_id)
        elif isPlaceholderTitle and len(history) == 0:
            sessions.rename_session(req.session_id, newTitle)

        sessions.add_message(req.session_id, "user", req.text)

        user_memories = memory.get_user_memories(user_id)
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
            system_prompt = get_system_prompt(req.prompt_style, context, user_memories)
            if docs:
                doc_refs = list(dict.fromkeys(f"{d['source']} (hal. {d.get('page', 1)})" for d in docs))
        else:
            system_prompt = build_chat_system_prompt(req.prompt_style, user_memories)

        async def sse_generator():
            full_text = ""
            persisted = False
            try:
                client = get_openai_client()
                api_messages = [{"role": "system", "content": system_prompt}]
                for m in history[-6:]:
                    api_messages.append({"role": m["role"], "content": m["content"]})
                api_messages.append({"role": "user", "content": req.text})

                response = client.chat.completions.create(
                    model=OPENAI_COMPATIBLE_MODEL,
                    messages=api_messages,
                    temperature=0.7,
                    stream=True,
                )

                if doc_refs:
                    yield f"data: {json.dumps({'documents': doc_refs})}\n\n"

                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        full_text += delta
                        yield f"data: {json.dumps({'chunk': delta})}\n\n"
                    await asyncio.sleep(0)

                full_text = format_academic_response(full_text)
                sessions.add_message(req.session_id, "assistant", full_text)
                persisted = True
                yield f"data: {json.dumps({'done': True, 'full_text': full_text})}\n\n"

                # Trigger background memory lifecycle evaluator
                recent_turn = [
                    {"role": "user", "content": req.text},
                    {"role": "assistant", "content": full_text},
                ]
                asyncio.create_task(
                    asyncio.to_thread(
                        memory.evaluate_memories_async,
                        user_id,
                        recent_turn,
                        client,
                        OPENAI_COMPATIBLE_MODEL,
                    )
                )

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
async def chat(request: Request, req: QueryRequest):
    try:
        user_id = extract_user_id(request)
        history = sessions.get_messages(req.session_id)
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)

        session = sessions.get_session(req.session_id)
        isPlaceholderTitle = not session or session.get("title") in ("Untitled", "Sesi Baru", "Dokumen Baru") or session.get("title", "").endswith(".pdf") or "_" in session.get("title", "")
        newTitle = generateSessionTitle(req.text)

        if not session:
            sessions.create_session(req.session_id, newTitle, user_id)
            session = sessions.get_session(req.session_id)
        elif isPlaceholderTitle and len(history) == 0:
            sessions.rename_session(req.session_id, newTitle)

        has_docs = rag.has_documents(req.session_id)
        user_memories = memory.get_user_memories(user_id)

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
            system_instruction = get_system_prompt(req.prompt_style, context, user_memories)
            api_messages = [{"role": "system", "content": system_instruction}]
            for m in history[-6:]:
                api_messages.append({"role": m["role"], "content": m["content"]})
            api_messages.append({"role": "user", "content": req.text})

            response = get_openai_client().chat.completions.create(
                model=OPENAI_COMPATIBLE_MODEL,
                messages=api_messages,
                temperature=0.7,
            )
            content = ""
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content or ""

            content = format_academic_response(content)
            result = {"jawaban": content}
            if docs:
                result["dokumen"] = list(dict.fromkeys(f"{d['source']} (hal. {d.get('page', 1)})" for d in docs))
        else:
            system_instruction = build_chat_system_prompt(req.prompt_style, user_memories)
            api_messages = [{"role": "system", "content": system_instruction}]
            for m in history[-6:]:
                api_messages.append({"role": m["role"], "content": m["content"]})
            api_messages.append({"role": "user", "content": req.text})

            response = get_openai_client().chat.completions.create(
                model=OPENAI_COMPATIBLE_MODEL,
                messages=api_messages,
                temperature=0.7,
            )
            content = ""
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content or ""
            content = format_academic_response(content)
            result = {"jawaban": content}

        sessions.add_message(req.session_id, "assistant", result.get("jawaban", ""))

        # Trigger background memory lifecycle evaluator
        recent_turn = [
            {"role": "user", "content": req.text},
            {"role": "assistant", "content": result.get("jawaban", "")},
        ]
        asyncio.create_task(
            asyncio.to_thread(
                memory.evaluate_memories_async,
                user_id,
                recent_turn,
                get_openai_client(),
                OPENAI_COMPATIBLE_MODEL,
            )
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in /chat: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
