from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "APIFlow"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://apiflow:apiflow@localhost:5432/apiflow"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    reset_token_expire_minutes: int = 30
    invite_token_expire_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""
    resend_api_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    cookie_secure: bool = False
    session_secret: str = "change-me-session"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
