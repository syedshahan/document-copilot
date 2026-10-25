from typing import Any, Literal

from pydantic import BaseModel


class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class DataPart(BaseModel):
    type: Literal["data-citation", "data-answer-status", "data-run-status"]
    data: dict[str, Any]


class UIMessage(BaseModel):
    id: str | None = None
    role: Literal["system", "user", "assistant"]
    parts: list[TextPart | DataPart]

    def text(self) -> str:
        return "".join(
            part.text for part in self.parts if isinstance(part, TextPart)
        ).strip()


def latest_user_message(messages: list[UIMessage]) -> UIMessage:
    for message in reversed(messages):
        if message.role == "user" and message.text():
            return message
    raise ValueError("A non-empty user message is required")
