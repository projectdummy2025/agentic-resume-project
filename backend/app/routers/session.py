import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.models.db_models import User
from app.models.schemas import SessionCreate
from app.services import session_service as sessions
from app.services import rag_service as rag
from app.services.security_service import get_current_user

router = APIRouter()


@router.post("/session")
async def create_session(req: SessionCreate, current_user: User = Depends(get_current_user)):
    session_id = req.session_id or str(uuid.uuid4())
    sessions.create_session(session_id, req.title, current_user.id)
    return {"session_id": session_id}


@router.get("/sessions")
async def list_sessions(current_user: User = Depends(get_current_user)):
    return sessions.list_sessions(current_user.id)


@router.get("/session/{session_id}/messages")
async def get_messages(session_id: str, current_user: User = Depends(get_current_user)):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    docs = rag.get_document_sources(session_id)
    return {
        "session": session,
        "messages": sessions.get_messages(session_id),
        "documents": docs,
    }


@router.post("/session/{session_id}/rename")
async def rename_session(session_id: str, title: str, current_user: User = Depends(get_current_user)):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions.rename_session(session_id, title)
    return {"ok": True}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    session = sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    sessions.delete_session(session_id)
    rag.delete_session_index(session_id)
    return {"ok": True}
