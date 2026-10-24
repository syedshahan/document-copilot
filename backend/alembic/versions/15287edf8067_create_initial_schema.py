"""create initial schema

Revision ID: 15287edf8067
Revises:
Create Date: 2026-10-24 20:18:11.751545

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "15287edf8067"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.execute(
        """
        CREATE FUNCTION public.handle_new_auth_user()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER SET search_path = ''
        AS $$
        BEGIN
            INSERT INTO public.users (id, email)
            VALUES (NEW.id, NEW.email)
            ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER document_copilot_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user()
        """
    )
    op.execute(
        """
        INSERT INTO public.users (id, email)
        SELECT id, email FROM auth.users WHERE email IS NOT NULL
        ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email
        """
    )
    op.create_table(
        "source_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=10), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("filing_type", sa.String(length=20), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("accession_number", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("accession_number"),
    )
    op.create_index("ix_source_documents_ticker", "source_documents", ["ticker"])
    op.create_index(
        "ix_source_documents_filing_type", "source_documents", ["filing_type"]
    )
    op.create_index(
        "ix_source_documents_filing_date", "source_documents", ["filing_date"]
    )
    op.create_index(
        "ix_source_documents_fiscal_year", "source_documents", ["fiscal_year"]
    )

    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(dim=1536), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(content, ''))", persisted=True
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["source_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_chunk_document_index"
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id", "document_chunks", ["document_id"]
    )
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.create_table(
        "chat_threads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_threads_user_id", "chat_threads", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "message_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')", name="ck_chat_message_role"
        ),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["chat_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_id", "position", name="uq_message_thread_position"
        ),
    )
    op.create_index("ix_chat_messages_thread_id", "chat_messages", ["thread_id"])

    op.create_table(
        "message_citations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["chat_messages.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id", "position", name="uq_citation_message_position"
        ),
    )
    op.create_index(
        "ix_message_citations_message_id", "message_citations", ["message_id"]
    )
    op.create_index(
        "ix_message_citations_chunk_id", "message_citations", ["chunk_id"]
    )

    for table in (
        "users",
        "source_documents",
        "document_chunks",
        "chat_threads",
        "chat_messages",
        "message_citations",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        "CREATE POLICY users_select_own ON users FOR SELECT TO authenticated "
        "USING (id = auth.uid())"
    )
    op.execute(
        "CREATE POLICY source_documents_read ON source_documents FOR SELECT "
        "TO authenticated USING (true)"
    )
    op.execute(
        "CREATE POLICY document_chunks_read ON document_chunks FOR SELECT "
        "TO authenticated USING (true)"
    )
    op.execute(
        "CREATE POLICY chat_threads_owner ON chat_threads FOR ALL TO authenticated "
        "USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())"
    )
    op.execute(
        "CREATE POLICY chat_messages_owner ON chat_messages FOR ALL TO authenticated "
        "USING (EXISTS (SELECT 1 FROM chat_threads "
        "WHERE chat_threads.id = chat_messages.thread_id "
        "AND chat_threads.user_id = auth.uid())) "
        "WITH CHECK (EXISTS (SELECT 1 FROM chat_threads "
        "WHERE chat_threads.id = chat_messages.thread_id "
        "AND chat_threads.user_id = auth.uid()))"
    )
    op.execute(
        "CREATE POLICY message_citations_owner ON message_citations FOR SELECT "
        "TO authenticated USING (EXISTS (SELECT 1 FROM chat_messages "
        "JOIN chat_threads ON chat_threads.id = chat_messages.thread_id "
        "WHERE chat_messages.id = message_citations.message_id "
        "AND chat_threads.user_id = auth.uid()))"
    )

    op.execute("GRANT SELECT ON users TO authenticated")
    op.execute("GRANT SELECT ON source_documents, document_chunks TO authenticated")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON chat_threads TO authenticated")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON chat_messages TO authenticated")
    op.execute("GRANT SELECT ON message_citations TO authenticated")


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS document_copilot_auth_user_created ON auth.users"
    )
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_auth_user()")
    op.drop_table("message_citations")
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")
    op.drop_table("document_chunks")
    op.drop_table("source_documents")
    op.drop_table("users")
