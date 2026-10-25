import argparse
import asyncio
import sys
from pathlib import Path

from app.database.documents import DocumentRepository
from app.database.supabase import create_service_role_client
from ingest.embeddings import GeminiEmbedder
from ingest.pipeline import ingest_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest SEC filings into Supabase")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("../data/downloads/manifest.json"),
        help="Path to the SEC download manifest",
    )
    parser.add_argument("--limit", type=_positive_int)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk locally without Gemini or Supabase calls",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace completed documents (for parser or embedding-model changes)",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    repository = None
    embedder = None
    if not args.dry_run:
        repository = DocumentRepository(await create_service_role_client())
        embedder = GeminiEmbedder()

    summary = await ingest_manifest(
        args.manifest,
        repository=repository,
        embedder=embedder,
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
    )
    print(
        "Summary: "
        f"processed={summary.processed} skipped={summary.skipped} "
        f"failed={summary.failed} chunks={summary.total_chunks}"
    )
    return 1 if summary.failed else 0


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(asyncio.run(main()))
