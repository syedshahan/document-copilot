import asyncio
from types import SimpleNamespace

import pytest
from google.genai.errors import APIError

from ingest.chunking import DocumentChunk
from ingest.embeddings import EmbeddingError, GeminiEmbedder, _retry_delay
from ingest.manifest import FilingRecord


def _filing() -> FilingRecord:
    return FilingRecord.model_validate(
        {
            "ticker": "AAPL",
            "cik": "0000320193",
            "form": "10-K",
            "filing_date": "2024-11-01",
            "report_date": "2024-09-28",
            "accession_number": "0000320193-24-000123",
            "primary_document": "aapl.htm",
            "source_url": "https://www.sec.gov/aapl.htm",
            "local_path": "2024/aapl.htm",
        }
    )


def test_embedding_dimension_is_validated() -> None:
    embedder = GeminiEmbedder(model="gemini-embedding-2", dimensions=3)

    async def request(*_args, **_kwargs):
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 2.0])])

    embedder._client = SimpleNamespace(  # type: ignore[assignment]
        aio=SimpleNamespace(models=SimpleNamespace(embed_content=request))
    )
    chunk = DocumentChunk(0, "Revenue", 2, None, "Item 7", 0, 7)

    with pytest.raises(EmbeddingError, match="Expected 3 embedding values"):
        asyncio.run(embedder.embed_chunks([chunk], _filing()))


def test_retry_delay_honors_gemini_retry_hint() -> None:
    error = APIError(
        429,
        {"error": {"message": "Please retry in 57.5s."}},
    )

    assert _retry_delay(error, attempt=0) == 58.5
