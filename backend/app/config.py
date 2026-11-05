"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Application
    app_name: str = "校园在线学习平台"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = Field(pattern=r"^mysql\+pymysql://")

    # JWT / Auth
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120  # 2 hours (session timeout)
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://127.0.0.1:20081", "http://localhost:20081"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
