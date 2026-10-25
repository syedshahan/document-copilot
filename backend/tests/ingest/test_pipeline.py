import asyncio
import json
from pathlib import Path

from ingest.pipeline import ingest_manifest


class CompleteRepository:
    async def find_by_accession(self, _accession: str) -> dict:
        return {"id": "document-id", "metadata": {"ingestion_status": "complete"}}

    @staticmethod
    def is_complete(_document: dict) -> bool:
        return True


class UnexpectedEmbedder:
    async def embed_chunks(self, *_args) -> list[list[float]]:
        raise AssertionError("A completed document must be skipped before embedding")


class RecordingRepository(CompleteRepository):
    def __init__(self) -> None:
        self.removed: list[str] = []
        self.stored = False

    async def remove(self, document_id: str) -> None:
        self.removed.append(document_id)

    async def store(self, *_args) -> str:
        self.stored = True
        return "new-document-id"


class FakeEmbedder:
    async def embed_chunks(self, chunks, _filing) -> list[list[float]]:
        return [[0.0] * 1536 for _chunk in chunks]


def test_completed_document_is_idempotently_skipped(tmp_path: Path) -> None:
    filing_path = tmp_path / "2024" / "aapl.htm"
    filing_path.parent.mkdir()
    filing_path.write_text(
        "<p>Item 1. Business</p><p>Useful text</p>", encoding="utf-8"
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": "SEC EDGAR",
                "generated_at_utc": "2025-01-01T00:00:00+00:00",
                "form": "10-K",
                "downloaded_count": 1,
                "filings": [
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
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = asyncio.run(
        ingest_manifest(
            manifest_path,
            repository=CompleteRepository(),  # type: ignore[arg-type]
            embedder=UnexpectedEmbedder(),  # type: ignore[arg-type]
        )
    )

    assert summary.skipped == 1
    assert summary.processed == 0
    assert summary.failed == 0


def test_force_replaces_completed_document(tmp_path: Path) -> None:
    filing_path = tmp_path / "2024" / "aapl.htm"
    filing_path.parent.mkdir()
    filing_path.write_text(
        "<p>Item 1. Business</p><p>Useful text</p>", encoding="utf-8"
    )
    manifest_path = tmp_path / "manifest.json"
    data = {
        "source": "SEC EDGAR",
        "generated_at_utc": "2025-01-01T00:00:00+00:00",
        "form": "10-K",
        "downloaded_count": 1,
        "filings": [
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
        ],
    }
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    repository = RecordingRepository()

    summary = asyncio.run(
        ingest_manifest(
            manifest_path,
            repository=repository,  # type: ignore[arg-type]
            embedder=FakeEmbedder(),  # type: ignore[arg-type]
            force=True,
        )
    )

    assert repository.removed == ["document-id"]
    assert repository.stored
    assert summary.processed == 1
