from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app


def test_auth_me_rejects_missing_bearer_token() -> None:
    with TestClient(app) as client:
        response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_auth_me_returns_authenticated_user() -> None:
    async def override_current_user() -> SimpleNamespace:
        return SimpleNamespace(id="user-id", email="analyst@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    try:
        with TestClient(app) as client:
            response = client.get("/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": "user-id",
        "email": "analyst@example.com",
    }
