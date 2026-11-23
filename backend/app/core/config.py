import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore", env_file=".env")

    PROJECT_NAME: str = "Omshiv CRM Backend"
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./omshiv_dev.db",
    )
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "omshiv-crm-insecure-dev-secret-key-32b"
    )
    SQL_ECHO: bool = False

    # Auth & Security
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    OTP_EXPIRE_SECONDS: int = 300  # 5 minutes
    OTP_MAX_ATTEMPTS: int = 3

    # Notification Gateways
    DOUBLETICK_API_KEY: str = os.environ.get("DOUBLETICK_API_KEY", "")
    DOUBLETICK_API_URL: str = os.environ.get(
        "DOUBLETICK_API_URL", "https://api.doubletick.io/v1"
    )
    FAST2SMS_API_KEY: str = os.environ.get("FAST2SMS_API_KEY", "")
    MSG91_AUTH_KEY: str = os.environ.get("MSG91_AUTH_KEY", "")


settings = Settings()
