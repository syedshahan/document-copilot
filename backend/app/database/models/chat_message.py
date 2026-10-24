from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.chat_thread import ChatThread
    from app.database.models.message_citation import MessageCitation


class ChatMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_message_role"),
        UniqueConstraint("thread_id", "position", name="uq_message_thread_position"),
    )

    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    message_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    thread: Mapped["ChatThread"] = relationship(back_populates="messages")
    citations: Mapped[list["MessageCitation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )
