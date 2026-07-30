from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from knowledge_search.api.app import create_app
from knowledge_search.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    application = create_app(Settings(environment="test"))
    with TestClient(application) as test_client:
        yield test_client
