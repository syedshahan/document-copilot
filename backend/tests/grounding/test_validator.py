import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import GroundingError, validate_grounded_answer
from app.retrieval.models import SourcePassage


def passage(chunk_id: str = "chunk-1") -> SourcePassage:
    return SourcePassage(
        chunk_id=chunk_id,
        document_id="document-1",
        chunk_index=2,
        content="Net sales increased to $100 million in fiscal 2025.",
        page=None,
        section="Item 7",
        metadata={"ticker": "AAPL"},
        score=1,
    )


def test_accepts_exact_excerpt_from_retrieved_chunk() -> None:
    answer = GroundedAnswer(
        answer="Net sales increased.",
        citations=[Citation(chunk_id="chunk-1")],
    )

    assert validate_grounded_answer(answer, {"chunk-1": passage()}) is answer


def test_rejects_citation_to_chunk_that_was_not_retrieved() -> None:
    answer = GroundedAnswer(
        answer="Unsupported answer.",
        citations=[Citation(chunk_id="invented")],
    )

    with pytest.raises(GroundingError, match="was not retrieved"):
        validate_grounded_answer(answer, {"chunk-1": passage()})


def test_allows_explicit_insufficient_evidence_without_citations() -> None:
    answer = GroundedAnswer(
        answer="The available corpus does not contain enough evidence.",
        insufficient_evidence=True,
    )

    assert validate_grounded_answer(answer, {}) is answer
