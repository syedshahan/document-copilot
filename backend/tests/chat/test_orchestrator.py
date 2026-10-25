import asyncio
from uuid import uuid4

import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.orchestrator import run_turn
from app.grounding.validator import GroundingError
from app.retrieval.models import SourcePassage


class FakeAgent:
    def __init__(self, answer: GroundedAnswer) -> None:
        self.answer_value = answer

    async def answer(self, question, deps) -> GroundedAnswer:
        assert question == "What were sales?"
        deps.remember(
            [
                SourcePassage(
                    chunk_id="chunk-1",
                    document_id="document-1",
                    chunk_index=1,
                    content="Net sales were $100 million.",
                    page=10,
                    section="Item 7",
                    metadata={"ticker": "AAPL"},
                    score=1,
                )
            ]
        )
        return self.answer_value


def test_run_turn_returns_validated_passages() -> None:
    answer = GroundedAnswer(
        answer="Net sales were $100 million [chunk-1].",
        citations=[Citation(chunk_id="chunk-1")],
    )

    turn = asyncio.run(
        run_turn(
            object(),  # type: ignore[arg-type]
            uuid4(),
            uuid4(),
            "What were sales?",
            agent=FakeAgent(answer),  # type: ignore[arg-type]
        )
    )

    assert turn.answer.answer == "Net sales were $100 million [1]."
    assert turn.answer.citations == answer.citations
    assert turn.passages["chunk-1"].page == 10


def test_run_turn_fails_closed_on_bad_citation() -> None:
    answer = GroundedAnswer(
        answer="Invented.",
        citations=[Citation(chunk_id="missing")],
    )

    with pytest.raises(GroundingError):
        asyncio.run(
            run_turn(
                object(),  # type: ignore[arg-type]
                uuid4(),
                uuid4(),
                "What were sales?",
                agent=FakeAgent(answer),  # type: ignore[arg-type]
            )
        )


def test_run_turn_rejects_under_specified_question_without_calling_agent() -> None:
    class UnexpectedAgent:
        async def answer(self, question, deps):
            raise AssertionError("Agent should not run for an under-specified question")

    turn = asyncio.run(
        run_turn(
            object(),  # type: ignore[arg-type]
            uuid4(),
            uuid4(),
            "Did it improve?",
            agent=UnexpectedAgent(),  # type: ignore[arg-type]
        )
    )

    assert turn.answer.insufficient_evidence is True
    assert turn.answer.citations == []
    assert "does not identify" in turn.answer.answer
