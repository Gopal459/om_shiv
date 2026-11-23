import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(extra="ignore", env_file=".env")

    PROJECT_NAME: str = "Omshiv CRM Backend"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/omshiv_crm",
    )
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "omshiv-crm-insecure-dev-secret-key-32b"
    )
    SQL_ECHO: bool = False


settings = Settings()
