from typing import Any

from supabase import AsyncClient

from app.retrieval.models import SearchFilters, SourcePassage


async def semantic_search(
    client: AsyncClient,
    query_embedding: list[float],
    *,
    limit: int = 20,
    filters: SearchFilters | None = None,
) -> list[SourcePassage]:
    filters = filters or SearchFilters()
    response = await client.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": limit,
            "filter_ticker": filters.ticker,
            "filter_fiscal_year": filters.fiscal_year,
        },
    ).execute()
    return [_passage(row, "semantic", "similarity") for row in response.data]


async def full_text_search(
    client: AsyncClient,
    query: str,
    *,
    limit: int = 20,
    filters: SearchFilters | None = None,
) -> list[SourcePassage]:
    filters = filters or SearchFilters()
    response = await client.rpc(
        "search_document_chunks",
        {
            "query_text": query,
            "match_count": limit,
            "filter_ticker": filters.ticker,
            "filter_fiscal_year": filters.fiscal_year,
        },
    ).execute()
    return [_passage(row, "full_text", "text_rank") for row in response.data]


async def neighboring_chunks(
    client: AsyncClient,
    document_id: str,
    chunk_index: int,
    *,
    distance: int = 1,
) -> list[SourcePassage]:
    response = await (
        client.table("document_chunks")
        .select("id,document_id,chunk_index,content,page,section,metadata")
        .eq("document_id", document_id)
        .gte("chunk_index", max(0, chunk_index - distance))
        .lte("chunk_index", chunk_index + distance)
        .order("chunk_index")
        .execute()
    )
    return [
        SourcePassage(
            chunk_id=row["id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            page=row.get("page"),
            section=row.get("section"),
            metadata=row.get("metadata") or {},
            score=0,
            is_neighbor=True,
        )
        for row in response.data
    ]


async def document_sources(
    client: AsyncClient, document_ids: set[str]
) -> dict[str, dict[str, Any]]:
    if not document_ids:
        return {}
    response = await (
        client.table("source_documents")
        .select(
            "id,source_url,ticker,company_name,filing_type,filing_date,"
            "fiscal_year,accession_number"
        )
        .in_("id", sorted(document_ids))
        .execute()
    )
    return {row["id"]: row for row in response.data}


def _passage(row: dict[str, Any], method: str, score_key: str) -> SourcePassage:
    return SourcePassage(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        chunk_index=row["chunk_index"],
        content=row["content"],
        page=row.get("page"),
        section=row.get("section"),
        metadata=row.get("metadata") or {},
        score=float(row[score_key]),
        matched_by={method},
    )
