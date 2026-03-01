"""SearchResult entity - represents a retrieved chunk with relevance score."""

from typing import Any

from pydantic import BaseModel, Field

from memory.entities.chunk import Chunk
from memory.entities.document import Document


class SearchResult(BaseModel):
    """A retrieved chunk with relevance score.

    Returned by the retrieval system, combining chunk content with similarity score.
    """

    chunk: Chunk
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    document: Document | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
