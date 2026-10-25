import asyncio

from app.retrieval.models import SearchFilters, SourcePassage
from app.retrieval.retriever import DocumentRetriever


def passage(
    chunk_id: str, index: int, method: str, neighbor: bool = False
) -> SourcePassage:
    return SourcePassage(
        chunk_id=chunk_id,
        document_id="document-id",
        chunk_index=index,
        content=chunk_id,
        page=None,
        section="Item 7",
        metadata={"ticker": "AAPL"},
        score=0.8,
        matched_by={method},
        is_neighbor=neighbor,
    )


class FakeEmbedder:
    async def embed(self, query: str) -> list[float]:
        assert query == "Apple revenue"
        return [0.1, 0.2]


def test_retriever_fuses_results_and_adds_unique_neighbors(monkeypatch) -> None:
    async def semantic(*_args, **_kwargs) -> list[SourcePassage]:
        return [passage("match", 5, "semantic")]

    async def lexical(*_args, **_kwargs) -> list[SourcePassage]:
        return [passage("match", 5, "full_text"), passage("text-only", 9, "full_text")]

    async def neighbors(_client, _document_id, index, **_kwargs) -> list[SourcePassage]:
        return [
            passage(f"neighbor-{index}", index - 1, "", neighbor=True),
            passage("match", 5, "", neighbor=True),
        ]

    async def sources(_client, document_ids) -> dict[str, dict[str, object]]:
        assert document_ids == {"document-id"}
        return {
            "document-id": {
                "source_url": "https://www.sec.gov/Archives/example.htm",
                "company_name": "Apple Inc.",
            }
        }

    monkeypatch.setattr("app.retrieval.retriever.semantic_search", semantic)
    monkeypatch.setattr("app.retrieval.retriever.full_text_search", lexical)
    monkeypatch.setattr("app.retrieval.retriever.neighboring_chunks", neighbors)
    monkeypatch.setattr("app.retrieval.retriever.document_sources", sources)
    retriever = DocumentRetriever(
        object(),  # type: ignore[arg-type]
        FakeEmbedder(),  # type: ignore[arg-type]
        result_limit=2,
    )

    results = asyncio.run(
        retriever.retrieve("Apple revenue", SearchFilters(ticker="AAPL"))
    )

    assert results[0].chunk_id == "match"
    assert results[0].matched_by == {"semantic", "full_text"}
    assert [result.chunk_id for result in results].count("match") == 1
    assert any(result.is_neighbor for result in results)
    assert results[0].metadata["source_url"] == (
        "https://www.sec.gov/Archives/example.htm"
    )
