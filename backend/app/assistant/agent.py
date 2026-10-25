from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.config import settings

_INSTRUCTIONS = (Path(__file__).with_name("instructions.md")).read_text(
    encoding="utf-8"
)


class DocumentAgent:
    def __init__(self) -> None:
        model = GoogleModel(
            settings.gemini_generation_model,
            provider=GoogleProvider(api_key=settings.gemini_api_key.get_secret_value()),
        )
        self._agent = Agent(
            model,
            deps_type=DocumentAgentDeps,
            output_type=GroundedAnswer,
            instructions=_INSTRUCTIONS,
            retries=2,
        )
        self._register_tools()

    def _register_tools(self) -> None:
        @self._agent.tool
        async def search_filings(
            ctx: RunContext[DocumentAgentDeps],
            query: str,
            ticker: str | None = None,
            fiscal_year: int | None = None,
        ) -> list[dict[str, object]]:
            """Search SEC filings for evidence relevant to the user's question."""
            passages = await ctx.deps.search(query, ticker, fiscal_year)
            return [_tool_passage(passage) for passage in passages]

        @self._agent.tool
        async def read_chunk(
            ctx: RunContext[DocumentAgentDeps], chunk_id: str
        ) -> dict[str, object] | None:
            """Read a complete passage already returned by search_filings."""
            passage = ctx.deps.passages.get(chunk_id)
            return _tool_passage(passage) if passage else None

        @self._agent.tool
        async def read_surrounding_chunks(
            ctx: RunContext[DocumentAgentDeps], chunk_id: str
        ) -> list[dict[str, object]]:
            """Read retrieved context surrounding a passage returned by search_filings."""
            passage = ctx.deps.passages.get(chunk_id)
            if passage is None:
                return []
            return [
                _tool_passage(candidate)
                for candidate in ctx.deps.passages.values()
                if candidate.document_id == passage.document_id
                and abs(candidate.chunk_index - passage.chunk_index) <= 1
            ]

    async def answer(self, question: str, deps: DocumentAgentDeps) -> GroundedAnswer:
        result = await self._agent.run(question, deps=deps)
        return result.output


def _tool_passage(passage: object) -> dict[str, object]:
    from app.retrieval.models import SourcePassage

    assert isinstance(passage, SourcePassage)
    return {
        "chunk_id": passage.chunk_id,
        "content": passage.content,
        "page": passage.page,
        "section": passage.section,
        "metadata": passage.metadata,
    }
