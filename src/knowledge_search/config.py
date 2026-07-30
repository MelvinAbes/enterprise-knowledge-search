from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="EKS_",
        extra="ignore",
        frozen=True,
    )

    app_name: str = Field(default="Enterprise Knowledge Search", min_length=1)
    environment: Environment = "development"
    log_level: LogLevel = "INFO"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    api_prefix: str = Field(default="/api/v1", pattern=r"^/[a-zA-Z0-9/_-]*$")
    database_url: SecretStr = Field(description="PostgreSQL connection URL")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("database URL must use the postgresql+psycopg driver")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
