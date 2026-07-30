from uuid import UUID

import pytest
from redis import Redis
from rq import Queue
from rq.serializers import JSONSerializer

from knowledge_search.providers.redis_queue import (
    WORKER_FUNCTION,
    RedisIngestionQueue,
)

pytestmark = pytest.mark.integration


def test_redis_queue_serializes_ingestion_job_reference(redis_url: str) -> None:
    job_id = UUID("cf70d7fb-e342-45c2-8c6c-a227f98f7f69")
    adapter = RedisIngestionQueue(
        redis_url=redis_url,
        queue_name="document-ingestion-test",
    )

    adapter.enqueue(job_id)

    connection: Redis = Redis.from_url(redis_url)
    queue = Queue(
        name="document-ingestion-test",
        connection=connection,
        serializer=JSONSerializer,
    )
    queued_job = queue.fetch_job(f"ingestion-{job_id}")

    assert adapter.is_ready()
    assert queue.job_ids == [f"ingestion-{job_id}"]
    assert queued_job is not None
    assert queued_job.func_name == WORKER_FUNCTION
    assert queued_job.args == [str(job_id)]
    assert queued_job.retries_left == 3
