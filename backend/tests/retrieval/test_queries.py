import asyncio
from types import SimpleNamespace

from app.retrieval.models import SearchFilters
from app.retrieval.queries import full_text_search, semantic_search


class FakeRPC:
    def __init__(self, data: list[dict]) -> None:
        self.data = data

    async def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self.data)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name: str, params: dict) -> FakeRPC:
        self.calls.append((name, params))
        score_key = "similarity" if name == "match_document_chunks" else "text_rank"
        return FakeRPC(
            [
                {
                    "chunk_id": "chunk-id",
                    "document_id": "document-id",
                    "chunk_index": 7,
                    "content": "Apple net sales",
                    "page": None,
                    "section": "Item 8",
                    "metadata": {"ticker": "AAPL", "fiscal_year": 2025},
                    score_key: 0.9,
                }
            ]
        )


def test_searches_pass_filters_to_database_functions() -> None:
    async def run() -> tuple[list, list, FakeClient]:
        client = FakeClient()
        filters = SearchFilters(ticker="AAPL", fiscal_year=2025)
        semantic = await semantic_search(
            client,  # type: ignore[arg-type]
            [0.1, 0.2],
            filters=filters,
        )
        lexical = await full_text_search(
            client,  # type: ignore[arg-type]
            "net sales",
            filters=filters,
        )
        return semantic, lexical, client

    semantic, lexical, client = asyncio.run(run())

    assert semantic[0].matched_by == {"semantic"}
    assert lexical[0].matched_by == {"full_text"}
    assert all(call[1]["filter_ticker"] == "AAPL" for call in client.calls)
    assert all(call[1]["filter_fiscal_year"] == 2025 for call in client.calls)
