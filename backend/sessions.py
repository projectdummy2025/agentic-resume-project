from datetime import datetime, timezone
from database import engine, SessionLocal, Base
from models import User, SessionModel, Message

DEFAULT_USER_ID = 1


def init_db():
    Base.metadata.create_all(bind=engine)


def create_session(session_id: str, title: str | None = None, user_id: int = DEFAULT_USER_ID):
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        now_iso = datetime.now(timezone.utc).isoformat()
        if not user:
            user = User(id=user_id, created_at=now_iso)
            db.add(user)
            db.flush()

        session_obj = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if session_obj:
            session_obj.title = title or "Untitled"
            session_obj.user_id = user_id
        else:
            session_obj = SessionModel(
                id=session_id,
                user_id=user_id,
                title=title or "Untitled",
                created_at=now_iso,
            )
            db.add(session_obj)
        db.commit()


def list_sessions(user_id: int = DEFAULT_USER_ID) -> list[dict]:
    with SessionLocal() as db:
        sessions = (
            db.query(SessionModel)
            .filter(SessionModel.user_id == user_id)
            .order_by(SessionModel.created_at.desc())
            .all()
        )
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "title": s.title,
                "created_at": s.created_at,
            }
            for s in sessions
        ]


def get_session(session_id: str) -> dict | None:
    with SessionLocal() as db:
        s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not s:
            return None
        return {
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "created_at": s.created_at,
        }


def rename_session(session_id: str, title: str):
    with SessionLocal() as db:
        s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if s:
            s.title = title
            db.commit()


def delete_session(session_id: str):
    with SessionLocal() as db:
        s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if s:
            db.delete(s)
            db.commit()


def add_message(session_id: str, role: str, content: str):
    with SessionLocal() as db:
        now_iso = datetime.now(timezone.utc).isoformat()
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            created_at=now_iso,
        )
        db.add(msg)
        db.commit()


def get_messages(session_id: str) -> list[dict]:
    with SessionLocal() as db:
        messages = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.id.asc())
            .all()
        )
        return [
            {
                "id": m.id,
                "session_id": m.session_id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ]
