import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services import session_service as sessions
from app.services import rag_service as rag
from app.routers import auth, chat, document, session, memory

app = FastAPI()
sessions.init_db()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(asyncio.to_thread(rag.warmup))


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(document.router)
app.include_router(session.router)
app.include_router(memory.router)
