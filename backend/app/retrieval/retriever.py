import asyncio
from dataclasses import replace

from supabase import AsyncClient

from app.retrieval.embeddings import QueryEmbedder
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.models import SearchFilters, SourcePassage
from app.retrieval.queries import (
    document_sources,
    full_text_search,
    neighboring_chunks,
    semantic_search,
)


class DocumentRetriever:
    def __init__(
        self,
        client: AsyncClient,
        embedder: QueryEmbedder,
        *,
        candidate_limit: int = 20,
        result_limit: int = 8,
        neighbor_distance: int = 1,
    ) -> None:
        self.client = client
        self.embedder = embedder
        self.candidate_limit = candidate_limit
        self.result_limit = result_limit
        self.neighbor_distance = neighbor_distance

    async def retrieve(
        self, query: str, filters: SearchFilters | None = None
    ) -> list[SourcePassage]:
        filters = filters or SearchFilters()
        query_embedding = await self.embedder.embed(query)
        semantic, lexical = await asyncio.gather(
            semantic_search(
                self.client,
                query_embedding,
                limit=self.candidate_limit,
                filters=filters,
            ),
            full_text_search(
                self.client,
                query,
                limit=self.candidate_limit,
                filters=filters,
            ),
        )
        selected = reciprocal_rank_fusion([semantic, lexical])[: self.result_limit]
        if self.neighbor_distance == 0:
            return await self._with_sources(selected)

        neighborhoods = await asyncio.gather(
            *(
                neighboring_chunks(
                    self.client,
                    passage.document_id,
                    passage.chunk_index,
                    distance=self.neighbor_distance,
                )
                for passage in selected
            )
        )
        selected_by_id = {passage.chunk_id: passage for passage in selected}
        neighbors_by_id = {
            passage.chunk_id: passage
            for neighborhood in neighborhoods
            for passage in neighborhood
            if passage.chunk_id not in selected_by_id
        }
        return await self._with_sources([*selected, *neighbors_by_id.values()])

    async def _with_sources(self, passages: list[SourcePassage]) -> list[SourcePassage]:
        sources = await document_sources(
            self.client, {passage.document_id for passage in passages}
        )
        return [
            replace(
                passage,
                metadata={**passage.metadata, **sources.get(passage.document_id, {})},
            )
            for passage in passages
        ]
