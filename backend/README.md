# Document Copilot backend

FastAPI service for authentication, document retrieval, and grounded chat.

## Local development

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```powershell
cd backend
uv sync
Copy-Item .env.example .env
```

Fill in every value in `.env`, then start the API:

```powershell
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` to check the service or `/docs` for the interactive API documentation.

## Common commands

```powershell
uv run ruff check .               # lint
uv run pytest                     # test
uv run alembic upgrade head       # apply database migrations
```

Add packages with `uv add <package>` and development-only tools with `uv add --dev <package>`.
