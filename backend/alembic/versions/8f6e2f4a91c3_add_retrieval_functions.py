"""add retrieval functions

Revision ID: 8f6e2f4a91c3
Revises: 15287edf8067
Create Date: 2026-10-25 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "8f6e2f4a91c3"
down_revision: str | Sequence[str] | None = "15287edf8067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION public.match_document_chunks(
            query_embedding vector(1536),
            match_count integer DEFAULT 20,
            filter_ticker text DEFAULT NULL,
            filter_fiscal_year integer DEFAULT NULL
        )
        RETURNS TABLE (
            chunk_id uuid,
            document_id uuid,
            chunk_index integer,
            content text,
            page integer,
            section varchar,
            metadata jsonb,
            similarity double precision
        )
        LANGUAGE sql
        STABLE
        SECURITY INVOKER
        SET search_path = ''
        AS $$
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.page,
                dc.section,
                dc.metadata,
                1 - (dc.embedding OPERATOR(public.<=>) query_embedding) AS similarity
            FROM public.document_chunks AS dc
            WHERE
                (filter_ticker IS NULL OR dc.metadata->>'ticker' = filter_ticker)
                AND (
                    filter_fiscal_year IS NULL
                    OR (dc.metadata->>'fiscal_year')::integer = filter_fiscal_year
                )
            ORDER BY dc.embedding OPERATOR(public.<=>) query_embedding
            LIMIT LEAST(GREATEST(match_count, 1), 100)
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION public.search_document_chunks(
            query_text text,
            match_count integer DEFAULT 20,
            filter_ticker text DEFAULT NULL,
            filter_fiscal_year integer DEFAULT NULL
        )
        RETURNS TABLE (
            chunk_id uuid,
            document_id uuid,
            chunk_index integer,
            content text,
            page integer,
            section varchar,
            metadata jsonb,
            text_rank real
        )
        LANGUAGE sql
        STABLE
        SECURITY INVOKER
        SET search_path = ''
        AS $$
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.page,
                dc.section,
                dc.metadata,
                ts_rank_cd(
                    dc.search_vector,
                    websearch_to_tsquery('english', query_text)
                ) AS text_rank
            FROM public.document_chunks AS dc
            WHERE
                length(trim(query_text)) > 0
                AND dc.search_vector @@ websearch_to_tsquery('english', query_text)
                AND (filter_ticker IS NULL OR dc.metadata->>'ticker' = filter_ticker)
                AND (
                    filter_fiscal_year IS NULL
                    OR (dc.metadata->>'fiscal_year')::integer = filter_fiscal_year
                )
            ORDER BY text_rank DESC, dc.chunk_index
            LIMIT LEAST(GREATEST(match_count, 1), 100)
        $$
        """
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.match_document_chunks"
        "(public.vector, integer, text, integer) TO authenticated, service_role"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.search_document_chunks"
        "(text, integer, text, integer) TO authenticated, service_role"
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION IF EXISTS public.search_document_chunks"
        "(text, integer, text, integer)"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS public.match_document_chunks"
        "(public.vector, integer, text, integer)"
    )
