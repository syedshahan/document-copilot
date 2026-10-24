from typing import TYPE_CHECKING, Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.message_citation import MessageCitation
    from app.database.models.source_document import SourceDocument


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunk_document_index"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_document_chunks_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(content, ''))", persisted=True),
    )

    document: Mapped["SourceDocument"] = relationship(back_populates="chunks")
    citations: Mapped[list["MessageCitation"]] = relationship(back_populates="chunk")
