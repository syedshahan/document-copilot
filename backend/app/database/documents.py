from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from supabase import AsyncClient

from ingest.chunking import DocumentChunk
from ingest.manifest import FilingRecord


class DocumentRepository:
    def __init__(self, client: AsyncClient, chunk_batch_size: int = 50) -> None:
        self.client = client
        self.chunk_batch_size = chunk_batch_size

    async def find_by_accession(self, accession_number: str) -> dict[str, Any] | None:
        response = await (
            self.client.table("source_documents")
            .select("id,metadata")
            .eq("accession_number", accession_number)
            .maybe_single()
            .execute()
        )
        return None if response is None else response.data

    async def remove(self, document_id: str) -> None:
        await (
            self.client.table("source_documents")
            .delete()
            .eq("id", document_id)
            .execute()
        )

    async def store(
        self,
        filing: FilingRecord,
        markdown: str,
        chunks: Sequence[DocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> str:
        started_at = datetime.now(UTC).isoformat()
        document_metadata = {
            "cik": filing.cik,
            "report_date": filing.report_date.isoformat(),
            "primary_document": filing.primary_document,
            "ingestion_status": "processing",
            "expected_chunk_count": len(chunks),
            "ingestion_started_at": started_at,
        }
        response = await (
            self.client.table("source_documents")
            .insert(
                {
                    "ticker": filing.ticker,
                    "company_name": filing.company_name,
                    "filing_type": filing.form,
                    "filing_date": filing.filing_date.isoformat(),
                    "fiscal_year": filing.fiscal_year,
                    "accession_number": filing.accession_number,
                    "source_url": str(filing.source_url),
                    "content": markdown,
                    "metadata": document_metadata,
                }
            )
            .execute()
        )
        document_id = response.data[0]["id"]

        try:
            rows = [
                self._chunk_row(document_id, filing, chunk, embedding)
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]
            for start in range(0, len(rows), self.chunk_batch_size):
                await (
                    self.client.table("document_chunks")
                    .insert(rows[start : start + self.chunk_batch_size])
                    .execute()
                )
            document_metadata.update(
                {
                    "ingestion_status": "complete",
                    "chunk_count": len(chunks),
                    "ingestion_completed_at": datetime.now(UTC).isoformat(),
                }
            )
            await (
                self.client.table("source_documents")
                .update({"metadata": document_metadata})
                .eq("id", document_id)
                .execute()
            )
        except BaseException:
            await self.remove(document_id)
            raise
        return document_id

    @staticmethod
    def is_complete(document: dict[str, Any]) -> bool:
        metadata = document.get("metadata") or {}
        return metadata.get("ingestion_status") == "complete"

    @staticmethod
    def _chunk_row(
        document_id: str,
        filing: FilingRecord,
        chunk: DocumentChunk,
        embedding: Sequence[float],
    ) -> dict[str, Any]:
        return {
            "document_id": document_id,
            "chunk_index": chunk.chunk_index,
            "page": chunk.page,
            "section": chunk.section,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "metadata": {
                "ticker": filing.ticker,
                "company_name": filing.company_name,
                "filing_type": filing.form,
                "filing_date": filing.filing_date.isoformat(),
                "fiscal_year": filing.fiscal_year,
                "accession_number": filing.accession_number,
                "page": chunk.page,
                "section": chunk.section,
                "source_start": chunk.start_offset,
                "source_end": chunk.end_offset,
            },
            "embedding": list(embedding),
        }
