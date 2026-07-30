from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from knowledge_search.api.app import create_app
from knowledge_search.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    application = create_app(
        Settings(
            environment="test",
            database_url=SecretStr(
                "postgresql+psycopg://knowledge_search:test@127.0.0.1:5432/knowledge_search"
            ),
        )
    )
    with TestClient(application) as test_client:
        yield test_client
