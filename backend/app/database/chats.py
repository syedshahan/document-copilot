from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import AsyncClient


async def list_threads(client: AsyncClient, user_id: UUID) -> list[dict[str, Any]]:
    response = await (
        client.table("chat_threads")
        .select("id,title,created_at,updated_at")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data


async def create_thread(
    client: AsyncClient, user_id: UUID, title: str
) -> dict[str, Any]:
    response = await (
        client.table("chat_threads")
        .insert({"user_id": str(user_id), "title": title})
        .execute()
    )
    return response.data[0]


async def get_owned_thread(
    client: AsyncClient, thread_id: UUID, user_id: UUID
) -> dict[str, Any]:
    response = await (
        client.table("chat_threads")
        .select("id,user_id,title,created_at,updated_at")
        .eq("id", str(thread_id))
        .maybe_single()
        .execute()
    )
    if response is None or response.data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat thread not found")
    if response.data["user_id"] != str(user_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You do not have access to this chat thread"
        )
    return response.data


async def update_thread(
    client: AsyncClient, thread_id: UUID, title: str
) -> dict[str, Any]:
    response = await (
        client.table("chat_threads")
        .update({"title": title, "updated_at": datetime.now(UTC).isoformat()})
        .eq("id", str(thread_id))
        .execute()
    )
    return response.data[0]


async def delete_thread(client: AsyncClient, thread_id: UUID) -> None:
    await client.table("chat_threads").delete().eq("id", str(thread_id)).execute()


async def list_messages(client: AsyncClient, thread_id: UUID) -> list[dict[str, Any]]:
    response = await (
        client.table("chat_messages")
        .select("id,role,content,message_data,position,created_at")
        .eq("thread_id", str(thread_id))
        .order("position")
        .execute()
    )
    return response.data


async def append_turn(
    client: AsyncClient,
    thread_id: UUID,
    user_message: dict[str, Any],
    user_text: str,
    assistant_text: str,
    citations: list[dict[str, Any]] | None = None,
    insufficient_evidence: bool = False,
) -> None:
    latest = await (
        client.table("chat_messages")
        .select("position")
        .eq("thread_id", str(thread_id))
        .order("position", desc=True)
        .limit(1)
        .execute()
    )
    next_position = latest.data[0]["position"] + 1 if latest.data else 0
    inserted = await (
        client.table("chat_messages")
        .insert(
            [
                {
                    "thread_id": str(thread_id),
                    "position": next_position,
                    "role": "user",
                    "content": user_text,
                    "message_data": user_message,
                },
                {
                    "thread_id": str(thread_id),
                    "position": next_position + 1,
                    "role": "assistant",
                    "content": assistant_text,
                    "message_data": {
                        "role": "assistant",
                        "parts": [
                            {"type": "text", "text": assistant_text},
                            *[
                                {"type": "data-citation", "data": citation}
                                for citation in citations or []
                            ],
                            *(
                                [
                                    {
                                        "type": "data-answer-status",
                                        "data": {"kind": "insufficient-evidence"},
                                    }
                                ]
                                if insufficient_evidence
                                else []
                            ),
                        ],
                    },
                },
            ]
        )
        .execute()
    )
    assistant_message_id = inserted.data[1]["id"]
    if citations:
        await (
            client.table("message_citations")
            .insert(
                [
                    {
                        "message_id": assistant_message_id,
                        "chunk_id": citation["chunk_id"],
                        "position": position,
                        "excerpt": citation["excerpt"],
                        "metadata": citation["metadata"],
                    }
                    for position, citation in enumerate(citations)
                ]
            )
            .execute()
        )
    await (
        client.table("chat_threads")
        .update({"updated_at": datetime.now(UTC).isoformat()})
        .eq("id", str(thread_id))
        .execute()
    )
