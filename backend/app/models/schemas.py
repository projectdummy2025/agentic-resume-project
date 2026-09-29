from pydantic import BaseModel, EmailStr


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


class MemoryCreateRequest(BaseModel):
    category: str = "profile"
    fact: str


class MemoryOut(BaseModel):
    id: str
    user_id: str
    category: str
    fact: str
    created_at: str
    updated_at: str


class UserRegister(BaseModel):
    name: str | None = None
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class VerifyOTP(BaseModel):
    email: EmailStr
    otp_code: str


class UserOut(BaseModel):
    id: int
    name: str | None = None
    email: str
    is_verified: bool
    auth_provider: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
