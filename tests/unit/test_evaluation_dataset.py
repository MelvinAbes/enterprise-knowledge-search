import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = PROJECT_ROOT / "samples" / "documents"
QUERIES = PROJECT_ROOT / "samples" / "evaluation" / "queries.jsonl"


def test_evaluation_cases_reference_existing_original_documents() -> None:
    cases: list[dict[str, Any]] = [
        json.loads(line)
        for line in QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(cases) == 8
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(str(case["query"]).strip() for case in cases)
    for case in cases:
        for judgment in case["relevant"]:
            assert (DOCUMENTS / str(judgment["filename"])).is_file()
            assert int(judgment["relevance"]) >= 1


def test_generated_device_handbook_has_stable_searchable_pages() -> None:
    reader = PdfReader(DOCUMENTS / "device-maintenance-handbook.pdf")

    assert len(reader.pages) == 2
    assert "Wednesday at 22:00 UTC" in (reader.pages[0].extract_text() or "")
    assert "rollback" in (reader.pages[1].extract_text() or "").lower()
