from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import AsyncClient
from supabase_auth.types import User

from app.auth.dependencies import get_current_user
from app.database.supabase import create_service_role_client

router = APIRouter(prefix="/documents", tags=["documents"])


async def get_document_client() -> AsyncClient:
    return await create_service_role_client()


DocumentClient = Annotated[AsyncClient, Depends(get_document_client)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/{document_id}/location/{chunk_id}")
async def document_location(
    document_id: UUID,
    chunk_id: UUID,
    client: DocumentClient,
    _user: CurrentUser,
) -> dict[str, Any]:
    document_response = await (
        client.table("source_documents")
        .select(
            "id,ticker,company_name,filing_type,filing_date,fiscal_year,"
            "accession_number,source_url,content"
        )
        .eq("id", str(document_id))
        .maybe_single()
        .execute()
    )
    chunk_response = await (
        client.table("document_chunks")
        .select("id,document_id,content,page,section,metadata")
        .eq("id", str(chunk_id))
        .eq("document_id", str(document_id))
        .maybe_single()
        .execute()
    )
    if (
        document_response is None
        or document_response.data is None
        or chunk_response is None
        or chunk_response.data is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cited passage not found")

    document = document_response.data
    chunk = chunk_response.data
    start = document["content"].find(chunk["content"])
    if start < 0:
        source_start = (chunk.get("metadata") or {}).get("source_start")
        if isinstance(source_start, int) and 0 <= source_start < len(
            document["content"]
        ):
            start = source_start
    return {
        **document,
        "chunk_id": chunk["id"],
        "chunk_content": chunk["content"],
        "page": chunk.get("page"),
        "section": chunk.get("section"),
        "highlight_start": start if start >= 0 else None,
        "highlight_end": (
            min(start + len(chunk["content"]), len(document["content"]))
            if start >= 0
            else None
        ),
    }
