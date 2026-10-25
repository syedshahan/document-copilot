import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from supabase_auth.errors import AuthApiError, AuthRetryableError

from app.auth import dependencies


def test_get_access_token_requires_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        dependencies.get_access_token(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_get_access_token_returns_bearer_value() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    assert dependencies.get_access_token(credentials) == "token"


def test_get_current_user_returns_verified_supabase_user(monkeypatch) -> None:
    expected_user = object()
    get_user = AsyncMock(return_value=SimpleNamespace(user=expected_user))
    client = SimpleNamespace(auth=SimpleNamespace(get_user=get_user))
    create_client = AsyncMock(return_value=client)
    monkeypatch.setattr(dependencies, "create_user_client", create_client)

    user = asyncio.run(dependencies.get_current_user("token"))

    assert user is expected_user
    create_client.assert_awaited_once_with("token")
    get_user.assert_awaited_once_with("token")


@pytest.mark.parametrize(
    "error",
    [
        AuthApiError("invalid token", 401, None),
        AuthApiError("malformed token", 400, None),
    ],
)
def test_get_current_user_rejects_invalid_tokens(monkeypatch, error) -> None:
    client = SimpleNamespace(
        auth=SimpleNamespace(get_user=AsyncMock(side_effect=error))
    )
    monkeypatch.setattr(
        dependencies, "create_user_client", AsyncMock(return_value=client)
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependencies.get_current_user("bad-token"))

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def test_get_current_user_reports_auth_service_failure(monkeypatch) -> None:
    client = SimpleNamespace(
        auth=SimpleNamespace(
            get_user=AsyncMock(side_effect=AuthRetryableError("unavailable", 503))
        )
    )
    monkeypatch.setattr(
        dependencies, "create_user_client", AsyncMock(return_value=client)
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(dependencies.get_current_user("token"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Authentication service unavailable"
