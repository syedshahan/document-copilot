import asyncio
import json
from collections.abc import AsyncIterator


def stream_event(payload: dict[str, object]) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()


def stream_error(message: str) -> tuple[bytes, bytes]:
    return (
        stream_event({"type": "error", "errorText": message}),
        b"data: [DONE]\n\n",
    )


async def answer_events(
    text_id: str,
    text: str,
    citations: list[dict[str, object]],
    insufficient_evidence: bool = False,
) -> AsyncIterator[bytes]:
    yield stream_event({"type": "text-start", "id": text_id})
    words = text.split(" ")
    for index, word in enumerate(words):
        delta = word if index == 0 else f" {word}"
        yield stream_event({"type": "text-delta", "id": text_id, "delta": delta})
        await asyncio.sleep(0.025)
    yield stream_event({"type": "text-end", "id": text_id})
    for citation in citations:
        yield stream_event({"type": "data-citation", "data": citation})
    if insufficient_evidence:
        yield stream_event(
            {"type": "data-answer-status", "data": {"kind": "insufficient-evidence"}}
        )
    yield stream_event({"type": "finish"})
    yield b"data: [DONE]\n\n"
