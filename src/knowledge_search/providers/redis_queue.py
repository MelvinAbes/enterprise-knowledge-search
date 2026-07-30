from uuid import UUID

from pydantic import SecretStr
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue, Retry
from rq.serializers import JSONSerializer

from knowledge_search.ingestion.errors import QueueDispatchError

WORKER_FUNCTION = "knowledge_search.worker.jobs.process_ingestion_job"


class RedisIngestionQueue:
    def __init__(self, *, redis_url: SecretStr | str, queue_name: str) -> None:
        raw_url = redis_url.get_secret_value() if isinstance(redis_url, SecretStr) else redis_url
        self._redis: Redis = Redis.from_url(raw_url)
        self._queue = Queue(
            name=queue_name,
            connection=self._redis,
            serializer=JSONSerializer,
        )

    def enqueue(self, job_id: UUID) -> None:
        try:
            self._queue.enqueue(
                WORKER_FUNCTION,
                str(job_id),
                job_id=f"ingestion-{job_id}",
                retry=Retry(max=3, interval=[10, 30, 60]),
                result_ttl=3_600,
                failure_ttl=86_400,
            )
        except RedisError as error:
            raise QueueDispatchError("Redis did not accept the ingestion job.") from error

    def is_ready(self) -> bool:
        try:
            return bool(self._redis.ping())
        except RedisError:
            return False
