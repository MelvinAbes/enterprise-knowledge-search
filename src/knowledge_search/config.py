from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ChunkingStrategyName = Literal["fixed_window", "section_aware"]


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
    document_storage_path: Path = Path("data/documents")
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    max_pdf_pages: int = Field(default=200, ge=1)
    chunk_size_tokens: int = Field(default=300, ge=20)
    chunk_overlap_tokens: int = Field(default=50, ge=0)
    chunking_strategy: ChunkingStrategyName = "section_aware"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("database URL must use the postgresql+psycopg driver")
        return value

    @model_validator(mode="after")
    def validate_chunking(self) -> Self:
        if self.chunk_overlap_tokens >= self.chunk_size_tokens:
            raise ValueError("chunk overlap must be smaller than chunk size")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings.model_validate({})
