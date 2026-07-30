import pytest
from pydantic import ValidationError

from knowledge_search.config import Settings

VALID_DATABASE_URL = "postgresql+psycopg://knowledge_search:test@localhost/knowledge_search"
VALID_REDIS_URL = "redis://localhost:6379/0"


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "environment": "staging",
                "database_url": VALID_DATABASE_URL,
                "redis_url": VALID_REDIS_URL,
            }
        )


def test_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "port": 70_000,
                "database_url": VALID_DATABASE_URL,
                "redis_url": VALID_REDIS_URL,
            }
        )


def test_settings_reject_non_psycopg_database_driver() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "database_url": "postgresql://localhost/knowledge_search",
                "redis_url": VALID_REDIS_URL,
            }
        )


def test_settings_reject_chunk_overlap_equal_to_size() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "database_url": VALID_DATABASE_URL,
                "redis_url": VALID_REDIS_URL,
                "chunk_size_tokens": 100,
                "chunk_overlap_tokens": 100,
            }
        )
