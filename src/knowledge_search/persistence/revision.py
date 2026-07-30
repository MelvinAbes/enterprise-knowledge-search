from knowledge_search.persistence.repositories import (
    SqlAlchemyCorpusRevisionRepository,
)
from knowledge_search.persistence.session import PostgresSessionFactory


class PostgresCorpusRevisionProvider:
    def __init__(self, sessions: PostgresSessionFactory) -> None:
        self._sessions = sessions

    def current(self) -> int:
        with self._sessions.transaction() as session:
            return SqlAlchemyCorpusRevisionRepository(session).current()
