from redis import Redis
from rq import Queue, Worker
from rq.serializers import JSONSerializer

from knowledge_search.config import get_settings
from knowledge_search.observability import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    connection: Redis = Redis.from_url(settings.redis_url.get_secret_value())
    queue = Queue(
        settings.ingestion_queue_name,
        connection=connection,
        serializer=JSONSerializer,
    )
    worker = Worker(
        [queue],
        connection=connection,
        serializer=JSONSerializer,
    )
    worker.work(
        logging_level=settings.log_level,
        with_scheduler=True,
    )


if __name__ == "__main__":
    main()
