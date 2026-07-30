import pytest
from pydantic import ValidationError

from knowledge_search.config import Settings


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"environment": "staging"})


def test_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"port": 70_000})
