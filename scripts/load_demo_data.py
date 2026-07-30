import argparse
import time
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = PROJECT_ROOT / "samples" / "documents"
MEDIA_TYPES = {
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


def main() -> None:
    arguments = _arguments()
    with httpx.Client(base_url=arguments.api_url, timeout=30) as client:
        for path in sorted(DOCUMENTS.iterdir()):
            media_type = MEDIA_TYPES.get(path.suffix.lower())
            if media_type is None:
                continue
            with path.open("rb") as source:
                response = client.post(
                    "/api/v1/documents",
                    files={"document": (path.name, source, media_type)},
                )
            if response.status_code == 409:
                print(f"Already present: {path.name}")
                continue
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            job_id = str(payload["ingestion_job"]["id"])
            _wait_for_job(client, job_id=job_id, filename=path.name)


def _wait_for_job(client: httpx.Client, *, job_id: str, filename: str) -> None:
    for _ in range(180):
        response = client.get(f"/api/v1/ingestion-jobs/{job_id}")
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        status = str(payload["status"])
        if status == "succeeded":
            print(f"Indexed: {filename}")
            return
        if status == "failed":
            raise RuntimeError(f"Indexing failed for {filename}: {payload.get('failure_code')}")
        time.sleep(1)
    raise TimeoutError(f"Indexing did not finish for {filename}")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load the demonstration corpus.")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running API.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
