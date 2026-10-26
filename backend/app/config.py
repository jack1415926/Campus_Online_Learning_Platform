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

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT / Auth
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120  # 2 hours (session timeout)
    refresh_token_expire_days: int = 7

    # Storage backend: "local" 或 "oss"（一键切换）
    storage_backend: str = "local"

    # MinIO / S3 (保留)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "lms"
    s3_region: str = "us-east-1"

    # Aliyun OSS (storage_backend="oss" 时使用)
    oss_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key: str = ""
    oss_secret_key: str = ""
    oss_region: str = ""
    oss_public_domain: str = ""  # 可选：自定义 CDN/公网域名，留空用 bucket 默认域名
    oss_signed_url_expire: int = 3600  # 签名 URL 有效期(秒)

    # CORS
    cors_origins: list[str] = ["http://127.0.0.1:20081", "http://localhost:20081"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
