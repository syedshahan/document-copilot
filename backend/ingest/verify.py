import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from supabase import AsyncClient

from app.config import settings
from app.database.supabase import create_service_role_client
from ingest.manifest import load_manifest


@dataclass
class VerificationSummary:
    documents: int = 0
    chunks: int = 0
    failures: int = 0


async def verify_corpus(
    client: AsyncClient, manifest_path: Path, limit: int | None = None
) -> VerificationSummary:
    manifest = load_manifest(manifest_path)
    filings = manifest.filings[:limit] if limit is not None else manifest.filings
    summary = VerificationSummary()

    for filing in filings:
        document_response = await (
            client.table("source_documents")
            .select("id,metadata")
            .eq("accession_number", filing.accession_number)
            .maybe_single()
            .execute()
        )
        document = None if document_response is None else document_response.data
        if not document:
            print(f"FAIL {filing.accession_number}: document is missing")
            summary.failures += 1
            continue

        chunks_response = await (
            client.table("document_chunks")
            .select("chunk_index,content,embedding,search_vector")
            .eq("document_id", document["id"])
            .order("chunk_index")
            .execute()
        )
        chunks = chunks_response.data
        errors = _document_errors(document, chunks)
        if errors:
            print(f"FAIL {filing.accession_number}: {'; '.join(errors)}")
            summary.failures += 1
            continue

        print(f"OK {filing.accession_number}: {len(chunks)} chunks")
        summary.documents += 1
        summary.chunks += len(chunks)
    return summary


def _document_errors(
    document: dict[str, Any], chunks: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    metadata = document.get("metadata") or {}
    expected_count = metadata.get("expected_chunk_count")
    if metadata.get("ingestion_status") != "complete":
        errors.append("status is not complete")
    if expected_count != len(chunks):
        errors.append(f"expected {expected_count} chunks, found {len(chunks)}")
    if [chunk["chunk_index"] for chunk in chunks] != list(range(len(chunks))):
        errors.append("chunk indexes are not contiguous")
    if any(not str(chunk.get("content", "")).strip() for chunk in chunks):
        errors.append("one or more chunks have empty content")
    if any("\ufffd" in str(chunk.get("content", "")) for chunk in chunks):
        errors.append("one or more chunks contain Unicode replacement characters")
    if any(
        _vector_length(chunk.get("embedding")) != settings.gemini_embedding_dimensions
        for chunk in chunks
    ):
        errors.append("one or more embeddings have the wrong dimensions")
    if any(not chunk.get("search_vector") for chunk in chunks):
        errors.append("one or more search vectors are empty")
    return errors


def _vector_length(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        return 0 if not body else body.count(",") + 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the ingested SEC corpus")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("../data/downloads/manifest.json"),
    )
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    summary = await verify_corpus(
        await create_service_role_client(), args.manifest, args.limit
    )
    print(
        f"Summary: documents={summary.documents} chunks={summary.chunks} "
        f"failures={summary.failures}"
    )
    return 1 if summary.failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
