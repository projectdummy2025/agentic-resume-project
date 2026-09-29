import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from ..core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_current_time() -> str:
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    auth_provider = Column(String, default="email", nullable=False)
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(String, nullable=True)
    created_at = Column(String, default=get_current_time, nullable=False)

    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, default=1)
    title = Column(String, nullable=True)
    created_at = Column(String, default=get_current_time, nullable=False)

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(String, default=get_current_time, nullable=False)

    session = relationship("SessionModel", back_populates="messages")


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, default=1)
    category = Column(String, nullable=False)
    fact = Column(Text, nullable=False)
    created_at = Column(String, default=get_current_time, nullable=False)
    updated_at = Column(String, default=get_current_time, nullable=False)

    user = relationship("User", back_populates="memories")
