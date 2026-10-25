from collections.abc import AsyncIterator
from time import perf_counter
from typing import Annotated, Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from pydantic_ai.exceptions import AgentRunError, ModelAPIError
from supabase import AsyncClient
from supabase_auth.types import User

from app.auth.dependencies import get_current_user
from app.chat.messages import UIMessage, latest_user_message
from app.chat.orchestrator import run_turn
from app.chat.streaming import answer_events, stream_error, stream_event
from app.database.chats import (
    append_turn,
    create_thread,
    delete_thread,
    get_owned_thread,
    list_messages,
    list_threads,
    update_thread,
)
from app.database.supabase import create_service_role_client
from app.grounding.validator import GroundingError

router = APIRouter(prefix="/chat", tags=["chat"])
logger = structlog.get_logger()


class ThreadCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def title_must_contain_text(cls, value: str) -> str:
        if not (title := value.strip()):
            raise ValueError("Title cannot be empty")
        return title


class ThreadUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def title_must_contain_text(cls, value: str) -> str:
        if not (title := value.strip()):
            raise ValueError("Title cannot be empty")
        return title


class StreamRequest(BaseModel):
    thread_id: UUID = Field(alias="threadId")
    messages: list[UIMessage]


async def get_chat_client() -> AsyncClient:
    return await create_service_role_client()


ChatClient = Annotated[AsyncClient, Depends(get_chat_client)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/threads")
async def threads(client: ChatClient, user: CurrentUser) -> list[dict[str, Any]]:
    return await list_threads(client, user.id)


@router.post("/threads", status_code=status.HTTP_201_CREATED)
async def new_thread(
    body: ThreadCreate, client: ChatClient, user: CurrentUser
) -> dict[str, Any]:
    return await create_thread(client, user.id, body.title)


@router.patch("/threads/{thread_id}")
async def rename_thread(
    thread_id: UUID, body: ThreadUpdate, client: ChatClient, user: CurrentUser
) -> dict[str, Any]:
    await get_owned_thread(client, thread_id, user.id)
    return await update_thread(client, thread_id, body.title)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_thread(
    thread_id: UUID, client: ChatClient, user: CurrentUser
) -> Response:
    await get_owned_thread(client, thread_id, user.id)
    await delete_thread(client, thread_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/threads/{thread_id}/messages")
async def messages(
    thread_id: UUID, client: ChatClient, user: CurrentUser
) -> list[dict[str, Any]]:
    await get_owned_thread(client, thread_id, user.id)
    return await list_messages(client, thread_id)


@router.post("/stream")
async def stream_chat(
    body: StreamRequest, client: ChatClient, user: CurrentUser
) -> StreamingResponse:
    await get_owned_thread(client, body.thread_id, user.id)
    try:
        user_message = latest_user_message(body.messages)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    async def events() -> AsyncIterator[bytes]:
        started = perf_counter()
        yield stream_event({"type": "data-run-status", "data": {"stage": "searching"}})
        logger.info(
            "chat_turn_started",
            user_id=str(user.id),
            thread_id=str(body.thread_id),
        )
        try:
            turn = await run_turn(
                client,
                user.id,
                body.thread_id,
                user_message.text(),
                conversation_context=_recent_context(body.messages),
            )
        except GroundingError:
            logger.warning(
                "chat_turn_grounding_failed",
                thread_id=str(body.thread_id),
                exc_info=True,
            )
            fallback = (
                "I could not verify an answer to this question against the retrieved "
                "filing passages. Please rephrase it with the company, filing period, "
                "and metric you want checked."
            )
            await append_turn(
                client,
                body.thread_id,
                user_message.model_dump(exclude_none=True),
                user_message.text(),
                fallback,
                [],
                True,
            )
            yield stream_event(
                {"type": "data-run-status", "data": {"stage": "answering"}}
            )
            async for event in answer_events(
                str(uuid4()), fallback, [], insufficient_evidence=True
            ):
                yield event
            return
        except (AgentRunError, ModelAPIError):
            logger.warning(
                "chat_turn_model_failed", thread_id=str(body.thread_id), exc_info=True
            )
            for event in stream_error(
                "The assistant service is unavailable. Please retry in a moment."
            ):
                yield event
            return

        citation_rows = [
            {
                "chunk_id": citation.chunk_id,
                "excerpt": turn.passages[citation.chunk_id].content,
                "metadata": {
                    **turn.passages[citation.chunk_id].metadata,
                    "document_id": turn.passages[citation.chunk_id].document_id,
                    "page": turn.passages[citation.chunk_id].page,
                    "section": turn.passages[citation.chunk_id].section,
                },
            }
            for citation in turn.answer.citations
        ]
        await append_turn(
            client,
            body.thread_id,
            user_message.model_dump(exclude_none=True),
            user_message.text(),
            turn.answer.answer,
            citation_rows,
            turn.answer.insufficient_evidence,
        )
        yield stream_event({"type": "data-run-status", "data": {"stage": "answering"}})
        async for event in answer_events(
            str(uuid4()),
            turn.answer.answer,
            citation_rows,
            turn.answer.insufficient_evidence,
        ):
            yield event
        logger.info(
            "chat_turn_completed",
            thread_id=str(body.thread_id),
            citation_count=len(citation_rows),
            insufficient_evidence=turn.answer.insufficient_evidence,
            duration_ms=round((perf_counter() - started) * 1000, 1),
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _recent_context(messages: list[UIMessage], limit: int = 6) -> str:
    prior = messages[:-1]
    lines = [
        f"{message.role}: {text}"
        for message in prior[-limit:]
        if (text := message.text())
    ]
    return "\n".join(lines)
