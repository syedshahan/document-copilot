from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import (
    AuthApiError,
    AuthInvalidJwtError,
    AuthRetryableError,
    AuthUnknownError,
)
from supabase_auth.types import User

from app.database.supabase import create_user_client

_bearer_scheme = HTTPBearer(auto_error=False)


def get_access_token(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> str:
    if credentials is None:
        raise _unauthorized("Missing bearer token")
    return credentials.credentials


async def get_current_user(
    access_token: Annotated[str, Depends(get_access_token)],
) -> User:
    client = await create_user_client(access_token)

    try:
        response = await client.auth.get_user(access_token)
    except AuthInvalidJwtError:
        raise _unauthorized("Invalid or expired bearer token") from None
    except AuthApiError as exc:
        if 400 <= exc.status < 500:
            raise _unauthorized("Invalid or expired bearer token") from None
        raise _auth_service_unavailable() from exc
    except (AuthRetryableError, AuthUnknownError, httpx.RequestError) as exc:
        raise _auth_service_unavailable() from exc

    return response.user


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _auth_service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Authentication service unavailable",
    )
