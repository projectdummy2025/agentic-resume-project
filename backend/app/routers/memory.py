from fastapi import APIRouter, Depends
from app.models.db_models import User
from app.models.schemas import MemoryCreateRequest
from app.services import memory_service as memory
from app.services.security_service import get_current_user

router = APIRouter()


@router.get("/memories")
async def get_memories(current_user: User = Depends(get_current_user)):
    return memory.get_user_memories(current_user.id)


@router.post("/memories")
async def create_memory(req: MemoryCreateRequest, current_user: User = Depends(get_current_user)):
    new_mem = memory.add_user_memory(current_user.id, req.category, req.fact)
    return new_mem


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, current_user: User = Depends(get_current_user)):
    memory.delete_user_memory(memory_id)
    return {"ok": True}
