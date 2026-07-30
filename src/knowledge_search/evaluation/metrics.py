import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RelevantLocation:
    filename: str
    section_path: tuple[str, ...]
    page_number: int | None
    relevance: int

    def __post_init__(self) -> None:
        if self.relevance < 1:
            raise ValueError("relevance must be greater than zero")


@dataclass(frozen=True, slots=True)
class RankedLocation:
    filename: str
    section_path: tuple[str, ...]
    page_number: int | None


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float


def evaluate_ranking(
    *,
    ranked: list[RankedLocation],
    relevant: list[RelevantLocation],
    limit: int,
) -> EvaluationMetrics:
    if limit < 1:
        raise ValueError("evaluation limit must be greater than zero")
    relevance_by_location = {
        _key(
            filename=item.filename,
            section_path=item.section_path,
            page_number=item.page_number,
        ): item.relevance
        for item in relevant
    }
    retrieved_keys = [
        _key(
            filename=item.filename,
            section_path=item.section_path,
            page_number=item.page_number,
        )
        for item in ranked[:limit]
    ]
    seen: set[tuple[str, tuple[str, ...], int | None]] = set()
    retrieved_relevances: list[int] = []
    for location in retrieved_keys:
        relevance = relevance_by_location.get(location, 0) if location not in seen else 0
        retrieved_relevances.append(relevance)
        seen.add(location)
    found = len(seen.intersection(relevance_by_location))
    recall = found / len(relevance_by_location) if relevance_by_location else 0.0
    first_relevant = next(
        (rank for rank, relevance in enumerate(retrieved_relevances, start=1) if relevance > 0),
        None,
    )
    reciprocal_rank = 1.0 / first_relevant if first_relevant is not None else 0.0
    dcg = _discounted_gain(retrieved_relevances)
    ideal = sorted(relevance_by_location.values(), reverse=True)[:limit]
    ideal_dcg = _discounted_gain(ideal)
    ndcg = dcg / ideal_dcg if ideal_dcg else 0.0
    return EvaluationMetrics(
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
        ndcg_at_k=ndcg,
    )


def _discounted_gain(relevances: list[int]) -> float:
    gain = 0.0
    for rank, relevance in enumerate(relevances, start=1):
        gain += (float(2**relevance) - 1.0) / math.log2(rank + 1)
    return gain


def _key(
    *,
    filename: str,
    section_path: tuple[str, ...],
    page_number: int | None,
) -> tuple[str, tuple[str, ...], int | None]:
    return filename, section_path, page_number
