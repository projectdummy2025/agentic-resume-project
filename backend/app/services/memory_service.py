import uuid
import json
from datetime import datetime, timezone
from openai import OpenAI
from ..core.database import SessionLocal
from ..core.config import DEFAULT_USER_ID
from ..models.db_models import User, UserMemory


def get_user_memories(user_id: int = DEFAULT_USER_ID) -> list[dict]:
    with SessionLocal() as db:
        memories = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id)
            .order_by(UserMemory.updated_at.desc())
            .all()
        )
        return [
            {
                "id": m.id,
                "user_id": m.user_id,
                "category": m.category,
                "fact": m.fact,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            for m in memories
        ]


def add_user_memory(user_id: int, category: str, fact: str) -> dict:
    memory_id = f"mem_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, created_at=now_iso)
            db.add(user)
            db.flush()

        mem = UserMemory(
            id=memory_id,
            user_id=user_id,
            category=category,
            fact=fact,
            created_at=now_iso,
            updated_at=now_iso,
        )
        db.add(mem)
        db.commit()
        return {
            "id": mem.id,
            "user_id": mem.user_id,
            "category": mem.category,
            "fact": mem.fact,
            "created_at": mem.created_at,
            "updated_at": mem.updated_at,
        }


def update_user_memory(memory_id: str, category: str, fact: str):
    now_iso = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as db:
        mem = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
        if mem:
            mem.category = category
            mem.fact = fact
            mem.updated_at = now_iso
            db.commit()


def delete_user_memory(memory_id: str):
    with SessionLocal() as db:
        mem = db.query(UserMemory).filter(UserMemory.id == memory_id).first()
        if mem:
            db.delete(mem)
            db.commit()


def evaluate_memories_async(
    user_id: int,
    recent_messages: list[dict],
    openai_client: OpenAI,
    model_name: str,
):
    """Background async LLM task evaluating recent conversation turn to update user atomic memories via ORM."""
    if not recent_messages:
        return

    existing_memories = get_user_memories(user_id)
    existing_text = json.dumps(existing_memories, ensure_ascii=False)
    history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in recent_messages[-2:]])

    system_instruction = (
        "Kamu adalah Memory Extraction Engine untuk personalisasi pengguna. "
        "Tugasmu: Analisis percakapan terbaru dan perbarui fakta memori personal pengguna.\n"
        "Kategori fakta yang didukung: 'profile', 'work', 'skill', 'preference'.\n"
        "Opsi Keputusan Aksi (Gunakan format JSON List) :\n"
        "1. ADD: Tambahkan fakta baru tentang pengguna. Contoh: {\"action\": \"ADD\", \"category\": \"skill\", \"fact\": \"...\"}\n"
        "2. UPDATE: Perbarui fakta lama yang berubah. Contoh: {\"action\": \"UPDATE\", \"target_id\": \"mem_123\", \"category\": \"work\", \"fact\": \"...\"}\n"
        "3. DELETE: Hapus fakta lama yang sudah tidak berlaku. Contoh: {\"action\": \"DELETE\", \"target_id\": \"mem_123\"}\n"
        "4. NOOP: Tidak ada fakta personal baru/berubah. Return list kosong [].\n\n"
        "OUTPUT HARUS JSON murni berisikan array of objects."
    )

    prompt_content = f"MEMORI SAAT INI:\n{existing_text}\n\nPERCAKAPAN TERBARU:\n{history_text}"

    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt_content},
            ],
            temperature=0.1,
            max_tokens=300,
        )

        content = response.choices[0].message.content or "[]"
        clean_json = content.replace("```json", "").replace("```", "").strip()

        decisions = json.loads(clean_json)
        if not isinstance(decisions, list):
            return

        for dec in decisions:
            action = dec.get("action", "").upper()
            if action == "ADD" and dec.get("fact"):
                add_user_memory(user_id, dec.get("category", "profile"), dec.get("fact"))
            elif action == "UPDATE" and dec.get("target_id") and dec.get("fact"):
                update_user_memory(dec.get("target_id"), dec.get("category", "profile"), dec.get("fact"))
            elif action == "DELETE" and dec.get("target_id"):
                delete_user_memory(dec.get("target_id"))

        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"({timestamp_str}) Evaluated memory lifecycle for user {user_id}: processed {len(decisions)} actions")
    except Exception as exc:
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"({timestamp_str}) Error evaluating memory lifecycle for user {user_id}: {exc}")
