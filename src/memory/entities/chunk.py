"""Chunk entity - represents a segment of a document."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Chunk(BaseModel):
    """A segment of a document suitable for embedding.

    Documents are split into chunks to enable semantic search at a granular level.
    Each chunk maintains a reference to its parent document.
    """

    id: UUID = Field(default_factory=uuid4)
    repository_id: UUID = Field(..., description="Repository this chunk belongs to")
    document_id: UUID = Field(..., description="Parent document ID")
    content: str = Field(..., description="Text content of this chunk")
    chunk_index: int = Field(..., ge=0, description="Position in the document")
    start_char: int = Field(..., ge=0, description="Start character offset in document")
    end_char: int = Field(..., gt=0, description="End character offset in document")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Chunk content cannot be empty")
        return v

    @field_validator("end_char")
    @classmethod
    def end_after_start(cls, v: int, info: Any) -> int:
        if "start_char" in info.data and v <= info.data["start_char"]:
            raise ValueError("end_char must be greater than start_char")
        return v
