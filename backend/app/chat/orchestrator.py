from dataclasses import dataclass
from uuid import UUID

from supabase import AsyncClient

from app.assistant.agent import DocumentAgent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, GroundedAnswer
from app.grounding.validator import validate_grounded_answer
from app.retrieval.embeddings import QueryEmbedder
from app.retrieval.models import SourcePassage
from app.retrieval.retriever import DocumentRetriever


@dataclass(frozen=True)
class CompletedTurn:
    answer: GroundedAnswer
    passages: dict[str, SourcePassage]


async def run_turn(
    client: AsyncClient,
    user_id: UUID,
    thread_id: UUID,
    question: str,
    *,
    agent: DocumentAgent | None = None,
) -> CompletedTurn:
    if _is_under_specified(question):
        return CompletedTurn(
            answer=GroundedAnswer(
                answer=(
                    "The question does not identify a company, filing period, or metric. "
                    "Please provide those details so I can search the corpus without "
                    "guessing."
                ),
                insufficient_evidence=True,
            ),
            passages={},
        )
    deps = DocumentAgentDeps(
        user_id=user_id,
        thread_id=thread_id,
        retriever=DocumentRetriever(client, QueryEmbedder()),
    )
    answer = await (agent or DocumentAgent()).answer(question, deps)
    validate_grounded_answer(answer, deps.passages)
    answer = answer.model_copy(
        update={
            "answer": _number_citation_markers(answer.answer, answer.citations),
        }
    )
    return CompletedTurn(answer=answer, passages=deps.passages)


def _is_under_specified(question: str) -> bool:
    words = question.casefold().split()
    vague_references = {"it", "this", "that", "they", "them", "those", "these"}
    return len(words) <= 5 and any(
        word.strip(".,?!:;") in vague_references for word in words
    )


def _number_citation_markers(answer: str, citations: list[Citation]) -> str:
    for number, citation in enumerate(citations, start=1):
        answer = answer.replace(citation.chunk_id, str(number))
    return answer
