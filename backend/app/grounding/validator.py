from app.assistant.outputs import GroundedAnswer
from app.retrieval.models import SourcePassage


class GroundingError(ValueError):
    pass


def validate_grounded_answer(
    answer: GroundedAnswer, retrieved: dict[str, SourcePassage]
) -> GroundedAnswer:
    if answer.insufficient_evidence:
        if answer.citations:
            raise GroundingError(
                "An insufficient-evidence answer cannot contain citations"
            )
        return answer
    if not answer.citations:
        raise GroundingError("A grounded answer must contain at least one citation")

    seen: set[str] = set()
    for citation in answer.citations:
        if citation.chunk_id not in retrieved:
            raise GroundingError(f"Citation {citation.chunk_id} was not retrieved")
        if citation.chunk_id in seen:
            raise GroundingError(f"Citation {citation.chunk_id} is duplicated")
        seen.add(citation.chunk_id)
    return answer
