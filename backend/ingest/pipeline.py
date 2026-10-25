from dataclasses import dataclass
from pathlib import Path

from app.database.documents import DocumentRepository
from ingest.chunking import DocumentChunk, chunk_document
from ingest.embeddings import GeminiEmbedder
from ingest.extract import ExtractedDocument, extract_filing
from ingest.manifest import FilingRecord, load_manifest, resolve_filing_path


@dataclass
class IngestionSummary:
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    total_chunks: int = 0


async def ingest_manifest(
    manifest_path: Path,
    *,
    repository: DocumentRepository | None,
    embedder: GeminiEmbedder | None,
    limit: int | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> IngestionSummary:
    manifest = load_manifest(manifest_path)
    filings = manifest.filings[:limit] if limit is not None else manifest.filings
    summary = IngestionSummary()

    for filing in filings:
        try:
            extracted, chunks = prepare_filing(manifest_path.parent, filing)
            if dry_run:
                _print_dry_run(filing, chunks)
                summary.processed += 1
                summary.total_chunks += len(chunks)
                continue

            if repository is None or embedder is None:
                raise ValueError(
                    "Repository and embedder are required outside dry-run mode"
                )
            existing = await repository.find_by_accession(filing.accession_number)
            if existing and repository.is_complete(existing) and not force:
                print(f"SKIP {filing.accession_number}: already complete")
                summary.skipped += 1
                continue
            replace_document_id: str | None = None
            if existing:
                reason = "forced refresh" if force else "incomplete document"
                print(f"RETRY {filing.accession_number}: replacing {reason}")
                if force and repository.is_complete(existing):
                    replace_document_id = existing["id"]
                else:
                    await repository.remove(existing["id"])

            print(f"EMBED {filing.accession_number}: {len(chunks)} chunks")
            vectors = await embedder.embed_chunks(chunks, filing)
            if replace_document_id:
                await repository.remove(replace_document_id)
            await repository.store(filing, extracted.markdown, chunks, vectors)
            summary.processed += 1
            summary.total_chunks += len(chunks)
            print(f"DONE {filing.accession_number}")
        # A corpus run should report a bad filing and continue with the remaining files.
        except Exception as exc:  # noqa: BLE001
            summary.failed += 1
            print(f"FAIL {filing.accession_number}: {exc}")

    return summary


def prepare_filing(
    downloads_dir: Path, filing: FilingRecord
) -> tuple[ExtractedDocument, list[DocumentChunk]]:
    path = resolve_filing_path(downloads_dir, filing)
    extracted = extract_filing(path)
    if not extracted.markdown.strip():
        raise ValueError(f"No useful text extracted from {path}")
    chunks = chunk_document(extracted)
    if not chunks:
        raise ValueError(f"No chunks produced from {path}")
    return extracted, chunks


def _print_dry_run(filing: FilingRecord, chunks: list[DocumentChunk]) -> None:
    sections = sorted({chunk.section for chunk in chunks if chunk.section})
    print(
        f"DRY RUN {filing.accession_number}: {filing.company_name}, "
        f"FY{filing.fiscal_year}, {len(chunks)} chunks, sections={sections}"
    )
    samples = chunks[:3]
    samples.extend(chunk for chunk in chunks if chunk.section and chunk not in samples)
    for chunk in samples[:6]:
        preview = " ".join(chunk.content[:160].split())
        print(
            f"  [{chunk.chunk_index}] section={chunk.section!r} page={chunk.page!r} "
            f"chars={len(chunk.content)} estimated_tokens={chunk.token_count}: {preview}"
        )
