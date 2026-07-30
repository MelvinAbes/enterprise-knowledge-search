from collections import defaultdict
from uuid import UUID

from knowledge_search.retrieval.models import FusedCandidate, RetrievalCandidate


def reciprocal_rank_fusion(
    *,
    keyword: list[RetrievalCandidate],
    vector: list[RetrievalCandidate],
    rrf_k: int,
) -> list[FusedCandidate]:
    if rrf_k < 1:
        raise ValueError("rrf_k must be greater than zero")

    scores: defaultdict[UUID, float] = defaultdict(float)
    keyword_ranks = {candidate.chunk_id: candidate.rank for candidate in keyword}
    vector_ranks = {candidate.chunk_id: candidate.rank for candidate in vector}
    for candidate in keyword:
        scores[candidate.chunk_id] += 1.0 / (rrf_k + candidate.rank)
    for candidate in vector:
        scores[candidate.chunk_id] += 1.0 / (rrf_k + candidate.rank)

    return sorted(
        (
            FusedCandidate(
                chunk_id=chunk_id,
                score=score,
                keyword_rank=keyword_ranks.get(chunk_id),
                vector_rank=vector_ranks.get(chunk_id),
            )
            for chunk_id, score in scores.items()
        ),
        key=lambda candidate: (-candidate.score, str(candidate.chunk_id)),
    )
