from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.chat_message import ChatMessage
    from app.database.models.document_chunk import DocumentChunk


class MessageCitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "message_citations"
    __table_args__ = (
        UniqueConstraint("message_id", "position", name="uq_citation_message_position"),
    )

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="RESTRICT"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    excerpt: Mapped[str] = mapped_column(Text)
    citation_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    message: Mapped["ChatMessage"] = relationship(back_populates="citations")
    chunk: Mapped["DocumentChunk"] = relationship(back_populates="citations")
