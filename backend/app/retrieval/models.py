from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchFilters:
    ticker: str | None = None
    fiscal_year: int | None = None


@dataclass(frozen=True)
class SourcePassage:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    page: int | None
    section: str | None
    metadata: dict[str, Any]
    score: float
    matched_by: set[str] = field(default_factory=set)
    is_neighbor: bool = False
