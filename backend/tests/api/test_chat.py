from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import chat
from app.assistant.outputs import Citation, GroundedAnswer
from app.auth.dependencies import get_current_user
from app.chat.orchestrator import CompletedTurn
from app.grounding.validator import GroundingError
from app.main import app
from app.retrieval.models import SourcePassage


def _set_dependencies() -> None:
    async def current_user() -> SimpleNamespace:
        return SimpleNamespace(id=uuid4(), email="analyst@example.com")

    async def chat_client() -> SimpleNamespace:
        return SimpleNamespace()

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[chat.get_chat_client] = chat_client


def test_message_history_rejects_another_users_thread(monkeypatch) -> None:
    async def forbidden(*_args) -> None:
        raise HTTPException(403, "You do not have access to this chat thread")

    monkeypatch.setattr(chat, "get_owned_thread", forbidden)
    _set_dependencies()
    try:
        with TestClient(app) as client:
            response = client.get(f"/chat/threads/{uuid4()}/messages")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_stream_returns_ai_sdk_events_and_persists_turn(monkeypatch) -> None:
    monkeypatch.setattr(chat, "get_owned_thread", AsyncMock(return_value={}))
    append_turn = AsyncMock()
    monkeypatch.setattr(chat, "append_turn", append_turn)
    passage = SourcePassage(
        chunk_id="chunk-1",
        document_id="document-1",
        chunk_index=1,
        content="Net sales were $100 million.",
        page=10,
        section="Item 7",
        metadata={"ticker": "AAPL"},
        score=1,
    )
    monkeypatch.setattr(
        chat,
        "run_turn",
        AsyncMock(
            return_value=CompletedTurn(
                answer=GroundedAnswer(
                    answer="Net sales were $100 million.",
                    citations=[Citation(chunk_id="chunk-1")],
                ),
                passages={"chunk-1": passage},
            )
        ),
    )
    thread_id = uuid4()
    _set_dependencies()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat/stream",
                json={
                    "threadId": str(thread_id),
                    "messages": [
                        {
                            "id": "message-1",
                            "role": "user",
                            "parts": [{"type": "text", "text": "Hello"}],
                        }
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"
    assert '"type":"text-start"' in response.text
    assert '"type":"text-delta"' in response.text
    assert '"type":"data-citation"' in response.text
    assert response.text.endswith("data: [DONE]\n\n")
    append_turn.assert_awaited_once()


def test_stream_accepts_prior_assistant_citation_parts(monkeypatch) -> None:
    monkeypatch.setattr(chat, "get_owned_thread", AsyncMock(return_value={}))
    monkeypatch.setattr(chat, "append_turn", AsyncMock())
    monkeypatch.setattr(
        chat,
        "run_turn",
        AsyncMock(
            return_value=CompletedTurn(
                answer=GroundedAnswer(
                    answer="Not enough evidence.", insufficient_evidence=True
                ),
                passages={},
            )
        ),
    )
    _set_dependencies()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat/stream",
                json={
                    "threadId": str(uuid4()),
                    "messages": [
                        {
                            "role": "assistant",
                            "parts": [
                                {"type": "text", "text": "Earlier answer"},
                                {
                                    "type": "data-citation",
                                    "data": {"chunk_id": "chunk-1"},
                                },
                            ],
                        },
                        {
                            "role": "user",
                            "parts": [{"type": "text", "text": "Follow-up question"}],
                        },
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert '"type":"data-answer-status"' in response.text


def test_stream_returns_502_when_grounding_validation_fails(monkeypatch) -> None:
    monkeypatch.setattr(chat, "get_owned_thread", AsyncMock(return_value={}))
    monkeypatch.setattr(
        chat,
        "run_turn",
        AsyncMock(side_effect=GroundingError("Citation was not retrieved")),
    )
    _set_dependencies()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat/stream",
                json={
                    "threadId": str(uuid4()),
                    "messages": [
                        {
                            "role": "user",
                            "parts": [{"type": "text", "text": "Hello"}],
                        }
                    ],
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "The assistant response failed citation validation"
    )
