from app.database.documents import DocumentRepository
from ingest.chunking import DocumentChunk
from ingest.manifest import FilingRecord


def test_completion_marker_and_chunk_metadata() -> None:
    filing = FilingRecord.model_validate(
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
    chunk = DocumentChunk(0, "Revenue", 2, None, "Item 7", 10, 17)

    row = DocumentRepository._chunk_row("document-id", filing, chunk, [0.1, 0.2])

    assert DocumentRepository.is_complete(
        {"metadata": {"ingestion_status": "complete"}}
    )
    assert not DocumentRepository.is_complete(
        {"metadata": {"ingestion_status": "processing"}}
    )
    assert row["metadata"]["fiscal_year"] == 2024
    assert row["metadata"]["source_start"] == 10
    assert "search_vector" not in row
