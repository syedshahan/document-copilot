from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.document_chunk import DocumentChunk


class SourceDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "source_documents"

    ticker: Mapped[str] = mapped_column(String(10), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    filing_type: Mapped[str] = mapped_column(String(20), index=True)
    filing_date: Mapped[date] = mapped_column(Date, index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, index=True)
    accession_number: Mapped[str] = mapped_column(String(32), unique=True)
    source_url: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    document_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
