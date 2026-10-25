import asyncio
import re
from collections.abc import Sequence

from google import genai
from google.genai import errors, types

from app.config import settings
from ingest.chunking import DocumentChunk
from ingest.manifest import FilingRecord

_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRY_DELAY_RE = re.compile(
    r"(?:retry in |retryDelay[^0-9]+)([0-9.]+)s", re.IGNORECASE
)


class EmbeddingError(RuntimeError):
    pass


class GeminiEmbedder:
    def __init__(
        self,
        *,
        model: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 20,
        max_attempts: int = 4,
    ) -> None:
        self.model = model or settings.gemini_embedding_model
        self.dimensions = dimensions or settings.gemini_embedding_dimensions
        self.batch_size = batch_size
        self.max_attempts = max_attempts
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())

    async def embed_chunks(
        self, chunks: Sequence[DocumentChunk], filing: FilingRecord
    ) -> list[list[float]]:
        if self.model == "gemini-embedding-001":
            vectors: list[list[float]] = []
            for start in range(0, len(chunks), 50):
                batch = chunks[start : start + 50]
                title = _embedding_title(filing, batch[0])
                vectors.extend(
                    await self._request(
                        [chunk.content for chunk in batch],
                        types.EmbedContentConfig(
                            task_type="RETRIEVAL_DOCUMENT",
                            title=title,
                            output_dimensionality=self.dimensions,
                        ),
                    )
                )
        else:
            vectors = []
            for start in range(0, len(chunks), self.batch_size):
                batch = chunks[start : start + self.batch_size]
                contents = [
                    types.Content(
                        parts=[
                            types.Part(
                                text=(
                                    f"title: {_embedding_title(filing, chunk)} | "
                                    f"text: {chunk.content}"
                                )
                            )
                        ]
                    )
                    for chunk in batch
                ]
                vectors.extend(
                    await self._request(
                        contents,
                        types.EmbedContentConfig(output_dimensionality=self.dimensions),
                    )
                )

        if len(vectors) != len(chunks):
            raise EmbeddingError(
                f"Gemini returned {len(vectors)} embeddings for {len(chunks)} chunks"
            )
        for vector in vectors:
            if len(vector) != self.dimensions:
                raise EmbeddingError(
                    f"Expected {self.dimensions} embedding values, got {len(vector)}"
                )
        return vectors

    async def _request(
        self,
        contents: str | list[str] | list[types.Content],
        config: types.EmbedContentConfig,
    ) -> list[list[float]]:
        for attempt in range(self.max_attempts):
            try:
                response = await self._client.aio.models.embed_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                return [
                    list(embedding.values or []) for embedding in response.embeddings
                ]
            except errors.APIError as exc:
                if (
                    exc.code not in _TRANSIENT_STATUS_CODES
                    or attempt + 1 == self.max_attempts
                ):
                    raise EmbeddingError(
                        f"Gemini embedding request failed with status {exc.code}: {exc}"
                    ) from exc
                delay = _retry_delay(exc, attempt)
                print(f"WAIT Gemini status {exc.code}: retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
        raise AssertionError("Retry loop must return or raise")


def _embedding_title(filing: FilingRecord, chunk: DocumentChunk) -> str:
    section = f", {chunk.section}" if chunk.section else ""
    return (
        f"{filing.company_name} ({filing.ticker}) {filing.form} "
        f"fiscal {filing.fiscal_year}{section}"
    )


def _retry_delay(error: errors.APIError, attempt: int) -> float:
    if match := _RETRY_DELAY_RE.search(str(error)):
        return min(float(match.group(1)) + 1, 65)
    return min(2**attempt, 8)
