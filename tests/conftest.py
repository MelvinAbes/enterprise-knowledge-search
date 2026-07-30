from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from knowledge_search.api.app import create_app
from knowledge_search.api.services import ReadinessService
from knowledge_search.config import Settings


class ReadyProbe:
    def is_ready(self) -> bool:
        return True


@pytest.fixture
def client() -> Iterator[TestClient]:
    readiness = ReadinessService(
        database=ReadyProbe(),
        queue=ReadyProbe(),
        vector_index=ReadyProbe(),
    )
    application = create_app(
        Settings(
            environment="test",
            database_url=SecretStr(
                "postgresql+psycopg://knowledge_search:test@127.0.0.1:5432/knowledge_search"
            ),
            redis_url=SecretStr("redis://127.0.0.1:6379/0"),
        ),
        readiness_service=readiness,
    )
    with TestClient(application) as test_client:
        yield test_client
