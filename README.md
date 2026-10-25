# Document Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English and get sourced, citable answers.

## The client

**Driftwood Capital** — independent investment research firm. Their analysts spend half their week reading 10-Ks and 10-Qs before they can produce any original analysis. Document Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| Hosting            | Railway                                              |
| LLM + embeddings   | Gemini                                               |

## Repo layout

```text
document-copilot/
├── AGENTS.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + download script (payloads gitignored)
├── docs/
│   └── client-brief.md # the client one-pager
├── backend/            # FastAPI service
└── frontend/           # React SPA (Vite)
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need accounts/keys for external services once the app is wired up. Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create a Gemini API key when the LLM layer is wired up.

## Running locally

1. Copy the environment templates and fill in every value:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

2. Install dependencies and apply database migrations:

```powershell
cd backend
uv sync
uv run alembic upgrade head
cd ../frontend
pnpm install
cd ..
```

3. Start the backend from the repository root in one terminal:

```powershell
cd backend
uv run uvicorn app.main:app --reload
```

4. Start the frontend in another terminal:

```powershell
cd frontend
pnpm dev
```

Open `http://localhost:5173`. The API health check is available at
`http://localhost:8000/health`.

Required backend settings are documented in `backend/.env.example`. The frontend needs
the backend URL plus the public Supabase URL and anon key from `frontend/.env.example`.
Never place the Supabase service-role key or database URL in the frontend environment.

Detailed setup guides:

- [Supabase](docs/guides/supabase-setup.md) — account, hosted project (dashboard or CLI)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)

## Sample SEC data

Use the standalone downloader to fetch a small local 10-K sample from SEC EDGAR.
Edit the params at the top of `data/download.py`, especially `USER_AGENT`, then run:

```bash
uv run data/download.py
```

By default this downloads the latest 5 10-K filings for AAPL, MSFT, NVDA, AMZN, and GOOGL into year folders under `data/downloads/` and writes a `manifest.json`.
Downloaded files are gitignored; the `data/` folder itself stays in git for the script and notes.

### Ingesting and updating the corpus

The ingestion command is intentionally a backend-only CLI, not an HTTP endpoint:

```powershell
cd backend
uv run python -m ingest --manifest ../data/downloads/manifest.json --dry-run --limit 1
uv run python -m ingest --manifest ../data/downloads/manifest.json --limit 1
uv run python -m ingest.verify --manifest ../data/downloads/manifest.json --limit 1
```

Remove `--limit 1` only when the Gemini embedding quota is ready for the complete corpus.
Completed accession numbers are skipped on safe reruns. Use `--force` only when deliberately
replacing a completed document; the prior version remains available until replacement
embeddings are ready.

After adding new filings, regenerate `data/downloads/manifest.json`, run a dry run, ingest,
then run the verifier. Do not change the configured embedding model or dimensionality after
vectors have been stored without planning a complete re-embedding and schema migration.
