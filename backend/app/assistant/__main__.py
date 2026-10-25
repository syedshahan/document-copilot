import argparse
import asyncio
import sys
from uuid import uuid4

from app.chat.orchestrator import run_turn
from app.database.supabase import create_service_role_client


async def _main(question: str) -> None:
    client = await create_service_role_client()
    turn = await run_turn(client, uuid4(), uuid4(), question)
    print(turn.answer.model_dump_json(indent=2))
    print(f"retrieved_passages={len(turn.passages)}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Run one grounded document question")
    parser.add_argument("question")
    args = parser.parse_args()
    asyncio.run(_main(args.question))
