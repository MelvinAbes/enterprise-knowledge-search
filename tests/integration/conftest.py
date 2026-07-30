from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from testcontainers.community.postgres import PostgresContainer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
POSTGRES_IMAGE = "postgres:17-alpine"
DOMAIN_TABLES = {"chunks", "corpus_revision", "documents", "ingestion_jobs"}


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def migrated_database_url(postgres_url: str) -> Iterator[str]:
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", postgres_url.replace("%", "%%"))
    command.upgrade(alembic_config, "head")

    yield postgres_url

    command.downgrade(alembic_config, "base")
    engine = create_engine(postgres_url)
    try:
        assert DOMAIN_TABLES.isdisjoint(inspect(engine).get_table_names())
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_database(migrated_database_url: str) -> Iterator[None]:
    engine = create_engine(migrated_database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE documents CASCADE"))
            connection.execute(text("UPDATE corpus_revision SET revision = 0 WHERE id = 1"))
        yield
    finally:
        engine.dispose()
