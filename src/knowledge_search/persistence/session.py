from collections.abc import Iterator
from contextlib import contextmanager

from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker


class PostgresSessionFactory:
    def __init__(self, database_url: SecretStr | str) -> None:
        raw_url = (
            database_url.get_secret_value() if isinstance(database_url, SecretStr) else database_url
        )
        if not raw_url.startswith("postgresql+psycopg://"):
            raise ValueError("PostgreSQL session factory requires the postgresql+psycopg driver")
        self._engine = create_engine(
            raw_url,
            pool_pre_ping=True,
            connect_args={"application_name": "enterprise-knowledge-search"},
        )
        self._sessions = sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            class_=Session,
        )

    @property
    def engine(self) -> Engine:
        return self._engine

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self._sessions.begin() as session:
            yield session

    def is_ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True

    def dispose(self) -> None:
        self._engine.dispose()
