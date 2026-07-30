import time
from typing import Any

import httpx

API_URL = "http://127.0.0.1:8000"
DOCUMENT = b"""# Smoke Test Operations

## Escalation

The smoke-test service escalation window is exactly forty-seven minutes.
"""


def main() -> None:
    with httpx.Client(base_url=API_URL, timeout=30) as client:
        _expect_ok(client.get("/health/live"))
        _expect_ok(client.get("/health/ready"))
        _expect_ok(client.get("/"))
        _expect_ok(client.get("/docs"))
        _expect_ok(client.get("/metrics"))

        upload = client.post(
            "/api/v1/documents",
            files={"document": ("smoke-operations.md", DOCUMENT, "text/markdown")},
        )
        if upload.status_code == 409:
            document_id = str(upload.json()["extensions"]["existing_document_id"])
            document = client.get(f"/api/v1/documents/{document_id}")
            document.raise_for_status()
            if document.json()["status"] == "failed":
                deletion = client.delete(f"/api/v1/documents/{document_id}")
                deletion.raise_for_status()
                upload = client.post(
                    "/api/v1/documents",
                    files={
                        "document": (
                            "smoke-operations.md",
                            DOCUMENT,
                            "text/markdown",
                        )
                    },
                )
                upload.raise_for_status()
                replacement_payload: dict[str, Any] = upload.json()
                document_id = str(replacement_payload["document"]["id"])
                _wait_for_job(
                    client,
                    str(replacement_payload["ingestion_job"]["id"]),
                )
            elif document.json()["status"] != "ready":
                _wait_for_document(client, document_id)
        else:
            upload.raise_for_status()
            upload_payload: dict[str, Any] = upload.json()
            document_id = str(upload_payload["document"]["id"])
            _wait_for_job(client, str(upload_payload["ingestion_job"]["id"]))

        search = client.get(
            "/api/v1/search",
            params={
                "q": "What is the smoke-test service escalation window?",
                "mode": "hybrid",
                "limit": 5,
            },
        )
        search.raise_for_status()
        filenames = {item["citation"]["original_filename"] for item in search.json()["items"]}
        if "smoke-operations.md" not in filenames:
            raise AssertionError("smoke document was not returned by hybrid search")

        deletion = client.delete(f"/api/v1/documents/{document_id}")
        if deletion.status_code not in {204, 404}:
            deletion.raise_for_status()
        print("Compose smoke test passed.")


def _wait_for_job(client: httpx.Client, job_id: str) -> None:
    for _ in range(180):
        response = client.get(f"/api/v1/ingestion-jobs/{job_id}")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        if payload["status"] == "succeeded":
            return
        if payload["status"] == "failed":
            raise AssertionError(f"ingestion failed: {payload['failure_code']}")
        time.sleep(1)
    raise TimeoutError("ingestion did not complete during smoke test")


def _wait_for_document(client: httpx.Client, document_id: str) -> None:
    for _ in range(180):
        response = client.get(f"/api/v1/documents/{document_id}")
        response.raise_for_status()
        status = response.json()["status"]
        if status == "ready":
            return
        if status == "failed":
            raise AssertionError("existing smoke document failed ingestion")
        time.sleep(1)
    raise TimeoutError("existing smoke document did not become ready")


def _expect_ok(response: httpx.Response) -> None:
    response.raise_for_status()


if __name__ == "__main__":
    main()
