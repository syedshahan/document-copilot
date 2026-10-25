import argparse
import asyncio
import sys

from app.database.supabase import create_service_role_client
from app.retrieval.embeddings import QueryEmbedder
from app.retrieval.models import SearchFilters
from app.retrieval.retriever import DocumentRetriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the ingested SEC corpus")
    parser.add_argument("query")
    parser.add_argument("--ticker")
    parser.add_argument("--year", type=int)
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    retriever = DocumentRetriever(
        await create_service_role_client(),
        QueryEmbedder(),
        result_limit=args.limit,
    )
    passages = await retriever.retrieve(
        args.query,
        SearchFilters(
            ticker=args.ticker.upper() if args.ticker else None,
            fiscal_year=args.year,
        ),
    )
    for passage in passages:
        kind = (
            "neighbor" if passage.is_neighbor else "+".join(sorted(passage.matched_by))
        )
        preview = " ".join(passage.content[:240].split())
        print(
            f"{kind:18} score={passage.score:.6f} "
            f"{passage.metadata.get('ticker')} FY{passage.metadata.get('fiscal_year')} "
            f"chunk={passage.chunk_index} section={passage.section!r}\n  {preview}"
        )


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    asyncio.run(main())
