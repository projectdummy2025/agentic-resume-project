import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def get_db_path() -> str:
    env_path = os.getenv("SESSION_DB")
    if env_path:
        return env_path
    # Fallback to local workspace data directory if SESSION_DB is not set
    workspace_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    return os.path.abspath(os.path.join(workspace_dir, "sessions.db"))


db_file_path = get_db_path()
os.makedirs(os.path.dirname(db_file_path), exist_ok=True)

DATABASE_URL = f"sqlite:///{db_file_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 20.0},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
