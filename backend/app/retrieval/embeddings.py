import asyncio
import re

from google import genai
from google.genai import errors, types

from app.config import settings

_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRY_DELAY_RE = re.compile(r"retry in ([0-9.]+)s", re.IGNORECASE)


class QueryEmbeddingError(RuntimeError):
    pass


class QueryEmbedder:
    def __init__(self, max_attempts: int = 4) -> None:
        self.model = settings.gemini_embedding_model
        self.dimensions = settings.gemini_embedding_dimensions
        self.max_attempts = max_attempts
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

    async def embed(self, query: str) -> list[float]:
        text = query.strip()
        if not text:
            raise ValueError("Query cannot be empty")
        if self.model == "gemini-embedding-001":
            contents = text
            config = types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=self.dimensions,
            )
        else:
            contents = f"task: search result | query: {text}"
            config = types.EmbedContentConfig(output_dimensionality=self.dimensions)

        for attempt in range(self.max_attempts):
            try:
                response = await self._client.aio.models.embed_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                vector = list(response.embeddings[0].values or [])
                if len(vector) != self.dimensions:
                    raise QueryEmbeddingError(
                        f"Expected {self.dimensions} values, got {len(vector)}"
                    )
                return vector
            except errors.APIError as exc:
                if (
                    exc.code not in _TRANSIENT_STATUS_CODES
                    or attempt + 1 == self.max_attempts
                ):
                    raise QueryEmbeddingError(
                        f"Gemini query embedding failed with status {exc.code}"
                    ) from exc
                await asyncio.sleep(_retry_delay(exc, attempt))
        raise AssertionError("Retry loop must return or raise")


def _retry_delay(error: errors.APIError, attempt: int) -> float:
    if match := _RETRY_DELAY_RE.search(str(error)):
        return min(float(match.group(1)) + 1, 65)
    return min(2**attempt, 8)
