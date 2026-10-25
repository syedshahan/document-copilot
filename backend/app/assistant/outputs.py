from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: str


class GroundedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[Citation] = Field(default_factory=list)
    insufficient_evidence: bool = False
