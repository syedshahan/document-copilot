# Pilot readiness notes

## Current corpus boundary

The current live database contains one Apple fiscal-2025 10-K. Questions about other
companies or years must return insufficient evidence until the deferred corpus ingestion is
completed. The ten client-brief questions cannot be meaningfully certified against this
one-document corpus.

## Chat durability and isolation

- Threads and messages are stored in Supabase rather than process memory, so they survive
  browser refreshes and backend restarts.
- Every thread request verifies ownership before reading, changing, deleting, retrieving, or
  generating an answer.
- Chat rows are tied to the authenticated Supabase user. Database RLS adds a second read
  boundary for user-visible chat data.
- Retrieval reads the shared curated filing corpus; it never reads another user's chats.

## Approximately 40 users

The API is stateless and can run multiple Railway replicas. Supabase holds durable state and
Gemini handles model inference, so there is no in-process single-user state. Async database,
embedding, and model calls avoid blocking one request behind another.

The practical constraints for a 40-user pilot are external quotas and same-thread write
contention:

- Set Gemini quotas for expected concurrent questions and watch rate-limit logs.
- The UI allows one in-flight turn per browser conversation. Analysts should not submit to
  the same thread simultaneously from multiple tabs because message positions are unique.
- Supabase connection and API limits should be monitored during the pilot; no dedicated
  connection is held per logged-in user.
- Add more backend replicas only after measuring real latency and rate limits. Forty users
  do not justify speculative queues or caching yet.

## Logging and latency

The backend writes JSON logs for every HTTP request and chat turn. Logs include a request ID,
route, response status, request duration, thread ID, citation count, grounding/model failures,
and total turn duration. They intentionally exclude prompts, answers, access tokens, and API
keys.

The chat endpoint opens its SSE response with a `searching` status before retrieval and Gemini
finish. This gives immediate UI feedback even when the complete grounded answer takes longer.
Successful turns are persisted before answer delivery so a client disconnect does not lose a
completed result.

For the pilot, measure p50 and p95 total turn duration from `chat_turn_completed` events and
track `chat_turn_model_failed`. The first-stream target is a few seconds; total answer latency
depends primarily on Gemini availability and query-embedding quota.
