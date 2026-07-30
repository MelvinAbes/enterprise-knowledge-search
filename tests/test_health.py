from uuid import UUID

from fastapi.testclient import TestClient


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["X-Request-ID"])


def test_readiness(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {
            "database": True,
            "queue": True,
            "vector_index": True,
        },
    }


def test_valid_request_id_is_returned_and_metrics_use_route_template(
    client: TestClient,
) -> None:
    request_id = "c5fd80ba-0df8-49a6-92d7-a540a8b51ca7"

    response = client.get("/health/live", headers={"X-Request-ID": request_id})
    metrics = client.get("/metrics")

    assert response.headers["X-Request-ID"] == request_id
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    assert (
        'eks_http_requests_total{method="GET",route="/health/live",status="200"} 1.0'
        in metrics.text
    )
