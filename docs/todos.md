# Document Copilot — implementation checklist

Work top to bottom. Each phase unlocks the next. Check items off as you go.

## Where to start: backend, frontend, or both?

**Start with foundation, then backend-led vertical slices.**

| Order | Why |
| ----- | --- |
| 1. Supabase + sample data | Everything persists here; you need a project and a corpus to test against. |
| 2. Backend schema + migrations | Auth, chat, retrieval, and citations all depend on the data model. |
| 3. Thin vertical slices | Wire auth, then a stubbed chat stream, then real RAG — each slice touches frontend + backend together. |
| 4. Frontend in parallel (lightly) | Scaffold the SPA early, but don't build citation UI or chat polish until the backend can return real grounded answers. |

The critical path is **data model → ingestion → retrieval → LLM → citations**. The frontend is mostly a streaming chat shell with auth and citation display — it shouldn't get far ahead of working APIs.

---

## Phase 0 — Prerequisites & foundation

- [x] Install toolchain: Python 3.12+, `uv`, Node 20+, `pnpm` (see [README](../README.md))
- [x] Create Supabase project and collect credentials ([supabase-setup](guides/supabase-setup.md))
- [x] Create Gemini API key (needed from Phase 6 onward)
- [x] Set `USER_AGENT` in `data/download.py` and download sample 10-K corpus:
  ```bash
  uv run data/download.py
  ```
- [x] Confirm `data/downloads/manifest.json` lists AAPL, MSFT, NVDA, AMZN, GOOGL filings (2021–2025)

---

## Phase 1 — Backend scaffold & database

Goal: a running FastAPI service with a migrated Supabase schema.

- [x] Init backend deps and project layout ([backend-setup](guides/backend-setup.md))
- [x] `app/config.py` — settings module, fail fast on missing env vars
- [x] `app/main.py` — FastAPI app, CORS, health check (`GET /health`)
- [x] SQLAlchemy models in `app/database/models/`:
  - [x] `users`
  - [x] `source_documents`
  - [x] `document_chunks` (embedding + generated `tsvector`)
  - [x] `chat_threads`
  - [x] `chat_messages`
  - [x] `message_citations`
- [x] Alembic init + first migration:
  - [x] `create extension if not exists vector`
  - [x] `vector(1536)` embedding column
  - [x] generated `tsvector` column on chunks
  - [x] HNSW index (vector) + GIN index (full-text)
  - [x] RLS policies (users see only their own chats)
- [x] `uv run alembic upgrade head` against Supabase direct connection
- [x] `app/database/supabase.py` — user-scoped and service-role clients
- [x] Verify: `uv run uvicorn app.main:app --reload` → health check returns 200

---

## Phase 2 — Auth (full stack)

Goal: analysts can sign in with email; backend rejects unauthenticated requests.

**Backend**

- [x] `app/auth/dependencies.py` — verify `Authorization: Bearer <supabase_jwt>`, expose `get_current_user`
- [x] Reject missing/expired tokens with `401` before any chat or retrieval work

**Frontend**

- [x] Scaffold Vite + React + TypeScript + Tailwind + shadcn ([frontend-setup](guides/frontend-setup.md))
- [x] `src/lib/env.ts` — validate `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [x] `src/lib/supabase.ts` — browser Supabase client
- [x] `src/lib/http.ts` + `src/lib/api.ts` — fetch wrapper with automatic bearer token
- [x] Sign-in / sign-up pages (email only, no SSO)
- [x] Protected routes — redirect unauthenticated users to login
- [x] Verify: sign up, sign in, token reaches backend on a test authenticated endpoint

---

## Phase 3 — Chat shell (vertical slice, stubbed)

Goal: end-to-end chat UI streaming from FastAPI, no real retrieval yet.

**Backend**

- [x] Chat thread CRUD: list threads, create thread, load message history
- [x] `POST /chat/stream` — accepts AI SDK message format, streams a stubbed assistant reply
- [x] Persist user + assistant messages to `chat_messages` after stream completes
- [x] `403` when user accesses another user's thread

**Frontend**

- [x] React Router: login, chat list, chat thread routes
- [x] AI SDK chat primitives pointed at `POST /chat/stream` with Supabase bearer token
- [x] Thread sidebar (past conversations)
- [x] Basic message list + input + streaming indicator
- [x] Verify: create thread, send message, see streamed response, reload and see history

---

## Phase 4 — Ingestion pipeline

Goal: SEC filings in the corpus are parsed, chunked, embedded, and stored in Supabase.

### Agreed ingestion shape

- [x] Run ingestion as a one-off backend CLI, not an HTTP route:
  `uv run python -m ingest --manifest ../data/downloads/manifest.json`
- [x] Keep the stages separate and small:
  `manifest → extract → normalize → chunk → embed → persist`
- [x] Add only a real HTML-parser dependency if needed (prefer Beautiful Soup with the
  standard-library parser); document why SEC inline-XBRL HTML is not safe to parse with
  string or regex helpers.
- [x] Use the existing settings in `app/config.py` for Gemini and Supabase; never read
  environment variables directly inside ingestion modules.
- [x] Treat `section` plus source character offsets as the dependable citation location.
  Preserve a page number only when the filing contains a reliable page marker; otherwise
  store `page = null` instead of inventing one.

### 1. Input and manifest validation

- [x] Add `backend/ingest/manifest.py` with typed manifest and filing records.
- [x] Validate required fields: ticker, CIK, form, filing/report dates, accession number,
  source URL, and local path.
- [x] Resolve each local path relative to the manifest directory, reject paths outside the
  downloads directory, and fail clearly when a referenced filing is missing.
- [x] Map the five supported tickers to canonical company names and derive fiscal year from
  `report_date`, not from the folder name or filing date.
- [x] Add CLI options for `--manifest`, `--limit`, and `--dry-run` so one filing can be
  inspected without calling Gemini or writing to Supabase.

### 2. SEC HTML extraction and normalization

- [x] Add `backend/ingest/extract.py` to remove scripts, styles, inline-XBRL metadata,
  hidden content, navigation noise, and repeated empty blocks.
- [x] Convert useful headings, paragraphs, lists, and tables into deterministic normalized
  Markdown while preserving financial table rows and cell values.
- [x] Detect SEC section headings such as `Item 1`, `Item 1A`, `Item 7`, and `Item 8`, and
  carry the current section name through the extracted blocks.
- [x] Preserve source offsets and reliable page-break markers in extraction metadata.
- [x] Store the complete normalized Markdown in `source_documents.content` so later
  re-chunking never needs the raw HTML or another SEC download.
- [ ] Add representative HTML fixtures from the local corpus for paragraphs, sections,
  tables, inline-XBRL tags, hidden content, and malformed-but-parseable markup.

### 3. Structure-aware chunking

- [x] Add `backend/ingest/chunking.py` with a pure, deterministic chunking function.
- [x] Split at section/paragraph/table boundaries first; only split inside a block when it
  exceeds the size limit.
- [x] Start with roughly 1,000–1,500 tokens per chunk and 150–200 tokens of overlap, then
  confirm the exact constants against real filings and Gemini's configured model limit.
- [x] Never cut a normal-sized Markdown table row in half; repeat the table header when a
  large table must span multiple chunks.
- [x] Store sequential `chunk_index`, content, token count, optional page, section, source
  start/end offsets, ticker, company, filing type/date, fiscal year, and accession number.
- [x] Reject empty chunks and verify that ordering plus overlap lets neighboring context be
  reconstructed later.

### 4. Gemini document embeddings

- [x] Add `backend/ingest/embeddings.py` using the existing async Google Gen AI SDK.
- [x] Generate retrieval-document embeddings with the configured model and pass
  `output_dimensionality=settings.gemini_embedding_dimensions`.
- [x] Assert every returned vector has exactly 1,536 values before any database write.
- [x] Embed small sequential batches and retry only transient rate-limit or
  service errors with capped exponential backoff; fail loudly on invalid input/config.
- [x] Keep the document embedding format compatible with Phase 5 query embeddings. For
  `gemini-embedding-001`, use `RETRIEVAL_DOCUMENT`; if configured for Embedding 2, use its
  documented `title: ... | text: ...` retrieval format instead.

### 5. Supabase persistence and safe re-runs

- [x] Add `app/database/documents.py` for source-document and chunk persistence; the CLI
  uses the backend-only service-role client.
- [x] Look up documents by unique `accession_number` before doing paid embedding work.
- [x] Skip documents already marked complete; detect and clean up an incomplete prior run
  before retrying it.
- [x] Insert one `source_documents` row and its `document_chunks` in bounded batches, with
  an ingestion-status marker in document metadata so partial runs are never treated as done.
- [x] On a handled write failure, remove that document's partial rows (chunks cascade) and
  report the accession number that failed.
- [x] Let Postgres populate the generated `search_vector`; never send or manually update
  the `tsvector` column from Python.
- [x] Mark a document complete only after every expected chunk is stored, and print a final
  summary of processed, skipped, failed, and total chunk counts.

### 6. Tests and rollout

- [x] Unit-test manifest validation, fiscal-year derivation, HTML cleanup, section detection,
  Markdown table preservation, chunk size/overlap/order, and metadata propagation.
- [x] Unit-test embedding batching, dimension validation, retry boundaries, and idempotency
  with Gemini and Supabase mocked; the fast suite must use no network or live database.
- [ ] Add an optional `@pytest.mark.integration` smoke test for one real embedding and one
  Supabase write/read/delete cycle.
- [x] Run `--dry-run --limit 1`, inspect the normalized Markdown and chunks, and adjust only
  the documented chunk constants if the real filing exposes a problem.
- [x] Ingest one Apple filing, verify document/chunk counts, 1,536-dimensional vectors, and
  populated `search_vector`, then run it again and confirm it is skipped.
- [ ] Run ingestion on the full manifest (25 filings × 5 companies).
- [ ] Verify all 25 documents are complete with contiguous chunk indexes and no empty text
  or embeddings; spot-check an Apple revenue table and its section/source metadata.

---

## Phase 5 — Retrieval

Goal: a user question returns ranked, relevant source passages.

- [x] `retrieval/queries.py` — pgvector semantic search over `document_chunks`
- [x] `retrieval/queries.py` — Postgres full-text search over `search_vector`
- [x] `retrieval/fusion.py` — Reciprocal Rank Fusion in Python
- [x] `retrieval/retriever.py` — query → fused ranked passages + neighbor chunks
- [x] Unit tests: fusion ranking, query assembly (mock DB)
- [ ] Integration test (optional, `@pytest.mark.integration`): real query against ingested corpus
- [x] Live smoke test: an Apple FY2025 net-sales query returned fused Item 7 and Item 8
  passages from the ingested filing
- [ ] Verify: test queries from [client-brief](client-brief.md) return relevant chunks (manual or scripted)

---

## Phase 6 — LLM agent & grounding

Goal: grounded answers with enforced citations — the core product contract.

- [x] `assistant/instructions.md` — product contract (cite everything, refuse to invent, no stock picks)
- [x] PydanticAI agent with typed deps (`DocumentAgentDeps`) and output (`GroundedAnswer`)
- [x] Agent tools: `search_filings`, `read_chunk`, `read_surrounding_chunks`
- [x] `chat/orchestrator.py` — one turn: retrieve → agent → validate → stream → persist
- [x] `grounding/validator.py` — every citation maps to a retrieved passage; fail closed on violation
- [x] `chat/streaming.py` — AI SDK-compatible stream (text deltas + citation metadata parts)
- [x] Persist `message_citations` linked to assistant messages
- [x] Unit tests: citation validation, grounding enforcement, message conversion
- [x] Verify against [client-brief example questions](client-brief.md#example-analyst-questions):
  - [x] Answers cite specific filings and reliable pages or sections
  - [x] Under-specified questions get "not enough evidence" responses
  - [x] Question 10 (generative AI margins) refuses to infer beyond filings

---

## Phase 7 — Trust UI (citations & source passages)

Goal: analysts can verify every claim in one click — this is what makes the product usable.

- [x] Citation chips/links on assistant messages (company, filing type, date, page/section)
- [x] Source passage panel — show underlying excerpt for selected citation
- [x] Empty states (no threads, no corpus match)
- [x] Error states (auth expired, retrieval failure, grounding failure, network/CORS)
- [x] Loading/streaming status during assistant run
- [x] Verify: click a citation → see the exact passage from the filing

---

## Phase 8 — Pilot readiness

Goal: 5 senior analysts can use it for a week and report ≥3 hours saved per analyst per week.

- [x] README "Running locally" section — copy-paste commands for backend + frontend + env vars
- [x] Seed or document how to ingest/update the corpus
- [ ] Smoke-test all 10 example questions from the client brief (blocked until the deferred
  25-filing corpus ingestion; Apple FY2025 behavior is verified)
- [x] Confirm chat history persists across sessions
- [x] Confirm ~40-user scale assumptions (no hardcoded single-user shortcuts)
- [x] Basic structured logging on backend (`structlog`) for debugging failed turns
- [x] Review latency: streaming starts within a few seconds for typical queries

---

## Phase 9 — Deployment (Railway)

- [ ] Railway: backend service (Uvicorn, env vars, `ALLOWED_ORIGINS`)
- [ ] Railway: frontend service (Vite build, `VITE_*` env vars at build time)
- [ ] Supabase: re-enable email confirmation for production if disabled during dev
- [ ] Run `alembic upgrade head` against production Supabase (direct connection)
- [ ] Run ingestion against production database
- [ ] End-to-end test on deployed URLs with a real Driftwood-style email account

---

## Quick reference

| Doc | Purpose |
| --- | ------- |
| [client-brief.md](client-brief.md) | What Driftwood needs and example questions |
| [architecture.md](architecture.md) | System design, data model, streaming contract |
| [guides/supabase-setup.md](guides/supabase-setup.md) | Hosted Postgres + Auth |
| [guides/backend-setup.md](guides/backend-setup.md) | FastAPI + Alembic commands |
| [guides/frontend-setup.md](guides/frontend-setup.md) | Vite + React scaffold commands |
