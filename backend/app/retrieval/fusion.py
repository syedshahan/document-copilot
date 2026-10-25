from dataclasses import replace

from app.retrieval.models import SourcePassage


def reciprocal_rank_fusion(
    ranked_lists: list[list[SourcePassage]], *, k: int = 60
) -> list[SourcePassage]:
    if k < 0:
        raise ValueError("k must be non-negative")

    passages: dict[str, SourcePassage] = {}
    scores: dict[str, float] = {}
    methods: dict[str, set[str]] = {}
    for ranked in ranked_lists:
        for rank, passage in enumerate(ranked, start=1):
            passages.setdefault(passage.chunk_id, passage)
            scores[passage.chunk_id] = scores.get(passage.chunk_id, 0) + 1 / (k + rank)
            methods.setdefault(passage.chunk_id, set()).update(passage.matched_by)

    ordered_ids = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
    return [
        replace(
            passages[chunk_id],
            score=scores[chunk_id],
            matched_by=methods[chunk_id],
        )
        for chunk_id in ordered_ids
    ]
