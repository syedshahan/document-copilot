from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.chat_message import ChatMessage
    from app.database.models.user import User


class ChatThread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_threads"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="chat_threads")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ChatMessage.position",
    )
