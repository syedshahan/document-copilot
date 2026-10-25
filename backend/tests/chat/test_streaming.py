import asyncio
import json

from app.chat.streaming import answer_events, stream_event


def test_stream_event_uses_sse_data_format() -> None:
    event = stream_event({"type": "text-delta", "id": "text-1", "delta": "Hello"})

    assert event == (b'data: {"type":"text-delta","id":"text-1","delta":"Hello"}\n\n')


def test_answer_stream_has_ordered_ai_sdk_events_and_citations() -> None:
    answer = "Apple revenue increased."
    citation = {"chunk_id": "chunk-1", "excerpt": "revenue increased"}

    async def collect() -> list[bytes]:
        return [event async for event in answer_events("text-1", answer, [citation])]

    events = asyncio.run(collect())
    payloads = [
        json.loads(event.removeprefix(b"data: ").strip()) for event in events[:-1]
    ]

    assert payloads[0] == {"type": "text-start", "id": "text-1"}
    assert payloads[-3] == {"type": "text-end", "id": "text-1"}
    assert payloads[-2] == {"type": "data-citation", "data": citation}
    assert payloads[-1] == {"type": "finish"}
    assert (
        "".join(
            payload["delta"] for payload in payloads if payload["type"] == "text-delta"
        )
        == answer
    )
    assert events[-1] == b"data: [DONE]\n\n"


def test_insufficient_answer_streams_structured_status() -> None:
    async def collect() -> list[bytes]:
        return [
            event
            async for event in answer_events(
                "text-1", "Not enough evidence.", [], insufficient_evidence=True
            )
        ]

    events = asyncio.run(collect())

    assert any(b'"type":"data-answer-status"' in event for event in events)
