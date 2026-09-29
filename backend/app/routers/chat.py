import asyncio
import json
import traceback
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.core.config import get_openai_client, OPENAI_COMPATIBLE_MODEL
from app.models.db_models import User
from app.models.schemas import QueryRequest
from app.services import session_service as sessions
from app.services import memory_service as memory
from app.services import rag_service as rag
from app.services.chat_service import (
    generateSessionTitle,
    format_academic_response,
    should_condense_query,
    condense_query,
    enrichQuery,
)
from app.core.prompts import get_system_prompt, build_chat_system_prompt
from app.services.security_service import get_current_user

router = APIRouter()


@router.post("/chat/stream")
async def chat_stream(req: QueryRequest, current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.id
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


@router.post("/chat")
async def chat(req: QueryRequest, current_user: User = Depends(get_current_user)):
    try:
        user_id = current_user.id
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
