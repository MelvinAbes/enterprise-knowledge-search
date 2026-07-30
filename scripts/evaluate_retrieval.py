import argparse
import json
from dataclasses import asdict
from pathlib import Path
from statistics import fmean
from typing import Any

import httpx

from knowledge_search.evaluation import (
    RankedLocation,
    RelevantLocation,
    evaluate_ranking,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUERIES = PROJECT_ROOT / "samples" / "evaluation" / "queries.jsonl"


def main() -> None:
    arguments = _arguments()
    evaluations: list[dict[str, Any]] = []
    with httpx.Client(base_url=arguments.api_url, timeout=30) as client:
        for case in _load_cases(arguments.queries):
            response = client.get(
                "/api/v1/search",
                params={
                    "q": case["query"],
                    "mode": arguments.mode,
                    "limit": arguments.limit,
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            metrics = evaluate_ranking(
                ranked=[_ranked_location(item) for item in payload["items"]],
                relevant=[_relevant_location(item) for item in case["relevant"]],
                limit=arguments.limit,
            )
            evaluations.append(
                {
                    "id": case["id"],
                    **asdict(metrics),
                }
            )

    summary = {
        "mode": arguments.mode,
        "limit": arguments.limit,
        "queries": len(evaluations),
        "mean_recall_at_k": fmean(item["recall_at_k"] for item in evaluations),
        "mean_reciprocal_rank": fmean(item["reciprocal_rank"] for item in evaluations),
        "mean_ndcg_at_k": fmean(item["ndcg_at_k"] for item in evaluations),
        "per_query": evaluations,
    }
    print(json.dumps(summary, indent=2))


def _load_cases(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _ranked_location(item: dict[str, Any]) -> RankedLocation:
    citation = item["citation"]
    return RankedLocation(
        filename=str(citation["original_filename"]),
        section_path=tuple(citation["section_path"]),
        page_number=citation["page_number"],
    )


def _relevant_location(item: dict[str, Any]) -> RelevantLocation:
    return RelevantLocation(
        filename=str(item["filename"]),
        section_path=tuple(item["section_path"]),
        page_number=item.get("page_number"),
        relevance=int(item["relevance"]),
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality.")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running API.",
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=DEFAULT_QUERIES,
        help="JSON Lines evaluation cases.",
    )
    parser.add_argument(
        "--mode",
        choices=("keyword", "vector", "hybrid"),
        default="hybrid",
    )
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


if __name__ == "__main__":
    main()
