import pytest

from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.models import SourcePassage


def passage(chunk_id: str, method: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=chunk_id,
        document_id="document-id",
        chunk_index=0,
        content=chunk_id,
        page=None,
        section=None,
        metadata={},
        score=0,
        matched_by={method},
    )


def test_rrf_rewards_chunks_found_by_both_methods() -> None:
    semantic = [passage("semantic-only", "semantic"), passage("both", "semantic")]
    lexical = [passage("both", "full_text"), passage("lexical-only", "full_text")]

    results = reciprocal_rank_fusion([semantic, lexical], k=60)

    assert results[0].chunk_id == "both"
    assert results[0].matched_by == {"semantic", "full_text"}
    assert results[0].score == pytest.approx(1 / 62 + 1 / 61)


def test_rrf_rejects_negative_k() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        reciprocal_rank_fusion([], k=-1)
