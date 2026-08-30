from pydantic import BaseModel


class QueryRequest(BaseModel):
    text: str
    prompt_style: str = "zero-shot"
    session_id: str
    use_rag: bool = True


class SessionCreate(BaseModel):
    session_id: str | None = None
    title: str | None = None


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: str


class MessageOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: str
