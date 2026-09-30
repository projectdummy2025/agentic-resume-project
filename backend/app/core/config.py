from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI

# Root project path for .env file resolution
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core & LLM Settings
    DEFAULT_USER_ID: int = 1
    LLM_PROVIDER: str = "openai_compat"
    OPENAI_COMPATIBLE_API_KEY: str = ""
    OPENAI_COMPATIBLE_BASE_URL: str = ""
    OPENAI_COMPATIBLE_MODEL: str = ""

    # JWT Authentication Config
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 4320

    # SMTP Configuration
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    @property
    def effective_smtp_from_email(self) -> str:
        return self.SMTP_FROM_EMAIL or self.SMTP_USER or "noreply@luwesin.local"


settings = Settings()

# Export settings fields for backward compatibility
DEFAULT_USER_ID = settings.DEFAULT_USER_ID
LLM_PROVIDER = settings.LLM_PROVIDER
OPENAI_COMPATIBLE_API_KEY = settings.OPENAI_COMPATIBLE_API_KEY
OPENAI_COMPATIBLE_BASE_URL = settings.OPENAI_COMPATIBLE_BASE_URL
OPENAI_COMPATIBLE_MODEL = settings.OPENAI_COMPATIBLE_MODEL

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASSWORD = settings.SMTP_PASSWORD
SMTP_FROM_EMAIL = settings.effective_smtp_from_email

GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI = settings.GOOGLE_REDIRECT_URI


def get_openai_client() -> OpenAI:
    api_key = settings.OPENAI_COMPATIBLE_API_KEY.strip() if settings.OPENAI_COMPATIBLE_API_KEY else "dummy_api_key"
    return OpenAI(
        api_key=api_key,
        base_url=settings.OPENAI_COMPATIBLE_BASE_URL,
    )


def extract_user_id(request) -> int:
    user_header = request.headers.get("x-user-id", "")
    clean_user = user_header.strip()
    if clean_user.isdigit():
        return int(clean_user)
    return settings.DEFAULT_USER_ID

