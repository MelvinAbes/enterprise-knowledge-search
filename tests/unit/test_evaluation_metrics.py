import pytest

from knowledge_search.evaluation import (
    RankedLocation,
    RelevantLocation,
    evaluate_ranking,
)


def test_evaluation_metrics_use_graded_relevance_and_cutoff() -> None:
    relevant = [
        RelevantLocation(
            filename="operations.md",
            section_path=("Backups",),
            page_number=None,
            relevance=3,
        ),
        RelevantLocation(
            filename="recovery.md",
            section_path=("Restore",),
            page_number=None,
            relevance=1,
        ),
    ]
    ranked = [
        RankedLocation(
            filename="unrelated.md",
            section_path=("Overview",),
            page_number=None,
        ),
        RankedLocation(
            filename="operations.md",
            section_path=("Backups",),
            page_number=None,
        ),
        RankedLocation(
            filename="recovery.md",
            section_path=("Restore",),
            page_number=None,
        ),
    ]

    metrics = evaluate_ranking(ranked=ranked, relevant=relevant, limit=2)

    assert metrics.recall_at_k == 0.5
    assert metrics.reciprocal_rank == 0.5
    assert metrics.ndcg_at_k == pytest.approx(0.5787641110)


def test_duplicate_ranked_locations_do_not_inflate_recall() -> None:
    relevant = [
        RelevantLocation(
            filename="operations.md",
            section_path=("Backups",),
            page_number=None,
            relevance=3,
        )
    ]
    duplicate = RankedLocation(
        filename="operations.md",
        section_path=("Backups",),
        page_number=None,
    )

    metrics = evaluate_ranking(
        ranked=[duplicate, duplicate],
        relevant=relevant,
        limit=2,
    )

    assert metrics.recall_at_k == 1.0
    assert metrics.ndcg_at_k == 1.0
