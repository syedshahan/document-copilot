from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from pydantic_ai.exceptions import AgentRunError, ModelAPIError
from supabase import AsyncClient
from supabase_auth.types import User

from app.auth.dependencies import get_current_user
from app.chat.messages import UIMessage, latest_user_message
from app.chat.orchestrator import run_turn
from app.chat.streaming import answer_events
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

    try:
        turn = await run_turn(client, user.id, body.thread_id, user_message.text())
    except GroundingError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The assistant response failed citation validation",
        ) from exc
    except (AgentRunError, ModelAPIError) as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "The assistant service is unavailable"
        ) from exc
    citation_rows = [
        {
            "chunk_id": citation.chunk_id,
            "excerpt": turn.passages[citation.chunk_id].content,
            "metadata": {
                **turn.passages[citation.chunk_id].metadata,
                "page": turn.passages[citation.chunk_id].page,
                "section": turn.passages[citation.chunk_id].section,
            },
        }
        for citation in turn.answer.citations
    ]

    async def events() -> AsyncIterator[bytes]:
        async for event in answer_events(
            str(uuid4()),
            turn.answer.answer,
            citation_rows,
            turn.answer.insufficient_evidence,
        ):
            yield event
        await append_turn(
            client,
            body.thread_id,
            user_message.model_dump(exclude_none=True),
            user_message.text(),
            turn.answer.answer,
            citation_rows,
            turn.answer.insufficient_evidence,
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
