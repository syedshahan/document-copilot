from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from supabase_auth.types import User

from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class CurrentUserResponse(BaseModel):
    id: str
    email: str | None


@router.get("/me")
async def read_current_user(
    user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, email=user.email)
