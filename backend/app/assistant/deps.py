from dataclasses import dataclass, field
from uuid import UUID

from app.retrieval.models import SearchFilters, SourcePassage
from app.retrieval.retriever import DocumentRetriever


@dataclass
class DocumentAgentDeps:
    user_id: UUID
    thread_id: UUID
    retriever: DocumentRetriever
    passages: dict[str, SourcePassage] = field(default_factory=dict)

    def remember(self, passages: list[SourcePassage]) -> list[SourcePassage]:
        self.passages.update((passage.chunk_id, passage) for passage in passages)
        return passages

    async def search(
        self, query: str, ticker: str | None = None, fiscal_year: int | None = None
    ) -> list[SourcePassage]:
        return self.remember(
            await self.retriever.retrieve(
                query, SearchFilters(ticker=ticker, fiscal_year=fiscal_year)
            )
        )
