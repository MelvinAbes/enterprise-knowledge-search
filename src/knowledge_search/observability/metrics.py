from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_LATEST


class RequestMetrics:
    def __init__(self) -> None:
        self._registry = CollectorRegistry()
        self._requests = Counter(
            "eks_http_requests_total",
            "HTTP requests completed by the API.",
            labelnames=("method", "route", "status"),
            registry=self._registry,
        )
        self._duration = Histogram(
            "eks_http_request_duration_seconds",
            "API request duration in seconds.",
            labelnames=("method", "route"),
            registry=self._registry,
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
        )

    def observe(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        self._requests.labels(
            method=method,
            route=route,
            status=str(status_code),
        ).inc()
        self._duration.labels(method=method, route=route).observe(duration_seconds)

    def render(self) -> tuple[bytes, str]:
        return generate_latest(self._registry), CONTENT_TYPE_LATEST
